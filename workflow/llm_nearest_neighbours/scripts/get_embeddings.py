import argparse
import gc
import os
from pathlib import Path

import pandas as pd
import torch
from PIL import Image
from transformers import AutoModel, AutoProcessor, AutoTokenizer, BitsAndBytesConfig

IMAGE_EXTENSIONS = {".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}

TEXT_EXTENSIONS = {".txt"}

def mean_pool_last_hidden(
    last_hidden_state: torch.Tensor,
    attention_mask: torch.Tensor | None = None,
) -> torch.Tensor:
    if attention_mask is None:
        return last_hidden_state.mean(dim=1)

    mask = attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()
    summed = (last_hidden_state * mask).sum(dim=1)
    counts = mask.sum(dim=1).clamp(min=1e-9)

    return summed / counts

def pool_hidden_state(
    hidden_state: torch.Tensor,
    pool: str,
    attention_mask: torch.Tensor | None = None,
) -> torch.Tensor:
    if hidden_state.ndim == 2:
        return hidden_state

    if hidden_state.ndim != 3:
        raise ValueError(
            f"Expected a 2D or 3D hidden-state tensor, got shape {tuple(hidden_state.shape)}"
        )

    if pool == "avg":
        return mean_pool_last_hidden(
            last_hidden_state=hidden_state,
            attention_mask=attention_mask,
        )

    if pool == "cls":
        return hidden_state[:, 0, :]

    if pool == "last":
        if attention_mask is None:
            return hidden_state[:, -1, :]

        last_indices = attention_mask.long().sum(dim=1) - 1

        batch_indices = torch.arange(
            hidden_state.size(0),
            device=hidden_state.device,
        )

        return hidden_state[
            batch_indices,
            last_indices,
            :,
        ]

    raise ValueError(f"Unknown pooling method: {pool}")

def get_safe_max_length(
    tokenizer,
    model,
    user_max_length: int | None = None,
) -> int:
    """
        Determine a safe context length for the model.

        Some tokenizers expose very large placeholder values, so these values are not trusted when they exceed 100,000 tokens.
    """
    if user_max_length is not None:
        return int(user_max_length)

    candidates = []

    tokenizer_max = getattr(
        tokenizer,
        "model_max_length",
        None,
    )

    if isinstance(tokenizer_max, int) and tokenizer_max < 100_000:
        candidates.append(tokenizer_max)

    config_max = getattr(
        model.config,
        "max_position_embeddings",
        None,
    )

    if isinstance(config_max, int) and config_max < 100_000:
        candidates.append(config_max)

    text_config = getattr(
        model.config,
        "text_config",
        None,
    )

    if text_config is not None:
        text_config_max = getattr(
            text_config,
            "max_position_embeddings",
            None,
        )

        if isinstance(text_config_max, int) and text_config_max < 100_000:
            candidates.append(text_config_max)

    if candidates:
        return int(min(candidates))

    return 2048

def get_model_device(model) -> torch.device:
    return next(model.parameters()).device

def move_inputs_to_device(
    inputs,
    device: torch.device,
) -> dict:
    return {
        key: value.to(device) if torch.is_tensor(value) else value
        for key, value in inputs.items()
    }

def extract_embedding_from_output(
    output,
    pool: str,
    attention_mask: torch.Tensor | None = None,
) -> torch.Tensor:
    last_hidden_state = getattr(
        output,
        "last_hidden_state",
        None,
    )

    if torch.is_tensor(last_hidden_state):
        return pool_hidden_state(
            hidden_state=last_hidden_state,
            pool=pool,
            attention_mask=attention_mask,
        )

    hidden_states = getattr(
        output,
        "hidden_states",
        None,
    )

    if hidden_states is not None and len(hidden_states) > 0:
        return pool_hidden_state(
            hidden_state=hidden_states[-1],
            pool=pool,
            attention_mask=attention_mask,
        )

    pooler_output = getattr(
        output,
        "pooler_output",
        None,
    )

    if torch.is_tensor(pooler_output):
        return pooler_output

    image_embeds = getattr(
        output,
        "image_embeds",
        None,
    )

    if torch.is_tensor(image_embeds):
        if image_embeds.ndim == 1:
            image_embeds = image_embeds.unsqueeze(0)

        return image_embeds

    text_embeds = getattr(
        output,
        "text_embeds",
        None,
    )

    if torch.is_tensor(text_embeds):
        if text_embeds.ndim == 1:
            text_embeds = text_embeds.unsqueeze(0)

        return text_embeds

    vision_model_output = getattr(
        output,
        "vision_model_output",
        None,
    )

    if vision_model_output is not None:
        return extract_embedding_from_output(
            output=vision_model_output,
            pool=pool,
            attention_mask=None,
        )

    text_model_output = getattr(
        output,
        "text_model_output",
        None,
    )

    if text_model_output is not None:
        return extract_embedding_from_output(
            output=text_model_output,
            pool=pool,
            attention_mask=attention_mask,
        )

    raise ValueError(
        f"Could not extract embeddings from model output of type {type(output).__name__}"
    )

def load_excluded_stimuli(
    excluded_stimuli_path: str,
) -> set[str]:
    with open(
        excluded_stimuli_path,
        "r",
        encoding="utf-8",
    ) as input_file:
        return {
            line.strip()
            for line in input_file
            if line.strip()
        }

def load_stimuli(
    stimuli_dir: str,
    excluded_stimuli: set[str],
) -> tuple[list[dict], str]:
    files = [
        path
        for path in sorted(Path(stimuli_dir).iterdir())
        if path.is_file()
        and path.stem not in excluded_stimuli
    ]

    text_files = [
        path
        for path in files
        if path.suffix.lower() in TEXT_EXTENSIONS
    ]

    image_files = [
        path
        for path in files
        if path.suffix.lower() in IMAGE_EXTENSIONS
    ]

    if text_files and image_files:
        raise ValueError(
            f"Both text and image stimuli were found in {stimuli_dir}. Each execution must receive only one type of stimulus"
        )

    if text_files:
        items = []

        for path in text_files:
            with open(
                path,
                "r",
                encoding="utf-8",
            ) as input_file:
                text = input_file.read()

            items.append(
                {
                    "stimulus": path.stem,
                    "text": text,
                }
            )

        return items, "text"

    if image_files:
        return [
            {
                "stimulus": path.stem,
                "image_path": str(path),
            }
            for path in image_files
        ], "image"

    raise ValueError(
        f"No supported stimulus files found in {stimuli_dir}"
    )

def embed_long_text(
    text: str,
    tokenizer,
    model,
    device: torch.device,
    max_length: int,
    overlap: int,
    pool: str,
) -> tuple[torch.Tensor, int, int]:
    """
        Embed a potentially long textual stimulus by splitting it into overlapping token chunks.

        The final representation is the weighted mean of the chunk representations.
    """
    if overlap < 0:
        raise ValueError("Overlap must be >= 0")

    if overlap >= max_length:
        raise ValueError("Overlap must be smaller than max_length")

    input_ids = tokenizer.encode(
        text,
        add_special_tokens=False,
    )

    n_tokens = len(input_ids)

    if n_tokens == 0:
        raise ValueError("Empty stimulus after tokenization")

    bos_token_id = getattr(
        tokenizer,
        "bos_token_id",
        None,
    )

    n_manual_special_tokens = (
        1
        if bos_token_id is not None
        else 0
    )

    chunk_token_length = (
        max_length
        - n_manual_special_tokens
    )

    if chunk_token_length <= 0:
        raise ValueError(
            f"max_length={max_length} is too small after accounting for BOS"
        )

    step = chunk_token_length - overlap

    if step <= 0:
        raise ValueError(
            f"Overlap is too large after accounting for special tokens. Chunk_token_length={chunk_token_length}, overlap={overlap}"
        )

    chunk_embeddings = []
    chunk_lengths = []

    for start in range(
        0,
        n_tokens,
        step,
    ):
        chunk_ids = input_ids[
            start:start + chunk_token_length
        ]

        if not chunk_ids:
            continue

        if bos_token_id is not None:
            model_input_ids = [
                bos_token_id,
                *chunk_ids,
            ]

        else:
            model_input_ids = chunk_ids

        if len(model_input_ids) > max_length:
            raise RuntimeError(
                f"Chunk length {len(model_input_ids)} exceeds max_length={max_length}"
            )

        input_ids_tensor = torch.tensor(
            [model_input_ids],
            dtype=torch.long,
            device=device,
        )

        attention_mask = torch.ones_like(
            input_ids_tensor,
            device=device,
        )

        with torch.inference_mode():
            model_output = model(
                input_ids=input_ids_tensor,
                attention_mask=attention_mask,
                output_hidden_states=True,
                return_dict=True,
                use_cache=False,
            )

        pooled = extract_embedding_from_output(
            output=model_output,
            pool=pool,
            attention_mask=attention_mask,
        )

        chunk_embeddings.append(
            pooled
            .squeeze(0)
            .detach()
            .cpu()
            .float()
        )

        chunk_lengths.append(
            len(chunk_ids)
        )

        del input_ids_tensor
        del attention_mask
        del model_output
        del pooled

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    if not chunk_embeddings:
        raise ValueError(
            "No chunks were produced for stimulus"
        )

    chunks = torch.stack(
        chunk_embeddings,
        dim=0,
    )

    weights = torch.tensor(
        chunk_lengths,
        dtype=torch.float32,
    ).unsqueeze(1)

    final_embedding = (
        chunks * weights
    ).sum(dim=0) / weights.sum()

    return (
        final_embedding,
        n_tokens,
        len(chunk_embeddings),
    )

def embed_image(
    image_path: str,
    processor,
    model,
    device: torch.device,
    pool: str,
) -> torch.Tensor:
    with Image.open(image_path) as image:
        image = image.convert("RGB")

        inputs = processor(
            images=image,
            return_tensors="pt",
        )

    inputs = move_inputs_to_device(
        inputs=inputs,
        device=device,
    )

    with torch.inference_mode():
        model_output = model(
            **inputs,
            output_hidden_states=True,
            return_dict=True,
        )

    embedding = extract_embedding_from_output(
        output=model_output,
        pool=pool,
        attention_mask=None,
    )

    embedding = (
        embedding
        .squeeze(0)
        .detach()
        .cpu()
        .float()
    )

    del inputs
    del model_output

    return embedding

def load_model(
    model_path: str,
    quantization_method: str | None,
    trust_remote_code: bool,
):
    quantization_config = None

    if quantization_method == "4bit":
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
        )

    elif quantization_method == "8bit":
        quantization_config = BitsAndBytesConfig(
            load_in_8bit=True,
        )

    if quantization_config is not None:
        model = AutoModel.from_pretrained(
            model_path,
            quantization_config=quantization_config,
            device_map="auto",
            trust_remote_code=trust_remote_code,
        )

    else:
        device = torch.device(
            "cuda"
            if torch.cuda.is_available()
            else "cpu"
        )

        model = AutoModel.from_pretrained(
            model_path,
            trust_remote_code=trust_remote_code,
        ).to(device)

    model.eval()

    return model

def main():
    parser = argparse.ArgumentParser(
        description="Extract language or vision embeddings"
    )
    parser.add_argument(
        "--stimuli_dir",
        required=True,
        help="Directory containing the input stimuli")
    parser.add_argument(
        "--output",
        required=True,
        help="Output Parquet file")
    parser.add_argument(
        "--model_path",
        required=True,
        help="Path or Hugging Face identifier of the model")
    parser.add_argument(
        "--modality",
        required=True,
        choices=["language", "vision", "multimodal"],
        help="Modality supported by the model")
    parser.add_argument(
        "--quantization_method",
        choices=["4bit", "8bit"],
        default=None,
        help="Optional model quantization method")
    parser.add_argument(
        "--excluded_stimuli",
        required=True,
        help="File containing one excluded stimulus name per line")
    parser.add_argument(
        "--pool",
        choices=["avg", "cls", "last"],
        default=None,
        help="Pooling method")
    parser.add_argument(
        "--chunk_max_length",
        type=int,
        default=None,
        help="Maximum model input length per textual chunk")
    parser.add_argument(
        "--chunk_overlap",
        type=int,
        default=256,
        help="Number of overlapping tokens between textual chunks")
    parser.add_argument(
        "--trust_remote_code",
        action="store_true",
        help="Allow custom Hugging Face model code")
    args = parser.parse_args()

    excluded_stimuli = load_excluded_stimuli(
        excluded_stimuli_path=args.excluded_stimuli,
    )

    items, input_type = load_stimuli(
        stimuli_dir=args.stimuli_dir,
        excluded_stimuli=excluded_stimuli,
    )

    if args.modality == "language" and input_type != "text":
        raise ValueError(
            "A language model requires textual stimuli"
        )

    if args.modality == "vision" and input_type != "image":
        raise ValueError(
            "A vision model requires visual stimuli"
        )

    if args.pool is None:
        if input_type == "image":
            pool = "cls"

        else:
            pool = "avg"

    else:
        pool = args.pool

    model = load_model(
        model_path=args.model_path,
        quantization_method=args.quantization_method,
        trust_remote_code=args.trust_remote_code,
    )

    device = get_model_device(model)

    tokenizer = None
    processor = None
    max_length = 0

    if input_type == "text":
        tokenizer = AutoTokenizer.from_pretrained(
            args.model_path,
            trust_remote_code=args.trust_remote_code,
        )

        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        max_length = get_safe_max_length(
            tokenizer=tokenizer,
            model=model,
            user_max_length=args.chunk_max_length,
        )

        if args.chunk_overlap >= max_length:
            raise ValueError(
                f"--chunk_overlap must be smaller than chunk max length. Got overlap={args.chunk_overlap}, max_length={max_length}"
            )

    else:
        processor = AutoProcessor.from_pretrained(
            args.model_path,
            trust_remote_code=args.trust_remote_code,
        )

    print(f"model_modality={args.modality}, input_type={input_type}, pool={pool}, number_of_stimuli={len(items)}")

    if input_type == "text":
        print(f"chunk_max_length={max_length}, chunk_overlap={args.chunk_overlap}")

    records = []

    for item in items:
        if input_type == "text":
            embedding, n_tokens, n_chunks = embed_long_text(
                text=item["text"],
                tokenizer=tokenizer,
                model=model,
                device=device,
                max_length=max_length,
                overlap=args.chunk_overlap,
                pool=pool,
            )

        else:
            embedding = embed_image(
                image_path=item["image_path"],
                processor=processor,
                model=model,
                device=device,
                pool=pool,
            )

            n_tokens = 0
            n_chunks = 1

        print(f"{item['stimulus']}: embedding_dim={embedding.numel()}, n_tokens={n_tokens}, n_chunks={n_chunks}")

        records.append(
            {
                "stimulus": item["stimulus"],
                "n_tokens": n_tokens,
                "n_chunks": n_chunks,
                "chunk_max_length": (
                    max_length
                    if input_type == "text"
                    else 0
                ),
                "chunk_overlap": (
                    args.chunk_overlap
                    if input_type == "text"
                    else 0
                ),
                **{
                    dimension: value
                    for dimension, value in enumerate(
                        embedding.numpy().astype("float32")
                    )
                },
            }
        )

        del embedding

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    dataframe = pd.DataFrame(records)

    dataframe = dataframe.set_index(
        "stimulus"
    )

    dataframe.index.name = "stimulus"

    metadata_columns = [
        "n_tokens",
        "n_chunks",
        "chunk_max_length",
        "chunk_overlap",
    ]

    embedding_columns = [
        column
        for column in dataframe.columns
        if isinstance(column, int)
    ]

    unexpected_columns = [
        column
        for column in dataframe.columns
        if column not in metadata_columns
        and column not in embedding_columns
    ]

    if unexpected_columns:
        raise ValueError(
            f"Unexpected non-embedding columns found: {unexpected_columns}"
        )

    dataframe = dataframe[
        metadata_columns
        + embedding_columns
    ]

    output_directory = os.path.dirname(
        args.output
    )

    if output_directory:
        os.makedirs(
            output_directory,
            exist_ok=True,
        )

    dataframe.to_parquet(
        args.output,
        engine="pyarrow",
        index=True,
    )

    del model
    del tokenizer
    del processor

    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()

    gc.collect()

if __name__ == "__main__":
    main()