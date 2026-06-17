import argparse
from pathlib import Path

import pandas as pd
import torch
from PIL import Image
from transformers import AutoModel, AutoProcessor, AutoTokenizer, BitsAndBytesConfig

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

def get_safe_max_length(
    tokenizer,
    model,
    user_max_length: int | None = None,
) -> int:
    """
        Determine a safe context length for the model.

        Some tokenizers expose very large placeholder values, so these values
        are not trusted when they exceed 100,000 tokens.
    """
    if user_max_length is not None:
        return int(user_max_length)

    candidates = []

    if tokenizer is not None:
        tokenizer_max = getattr(tokenizer, "model_max_length", None)

        if isinstance(tokenizer_max, int) and tokenizer_max < 100_000:
            candidates.append(tokenizer_max)

    config_max = getattr(model.config, "max_position_embeddings", None)

    if isinstance(config_max, int) and config_max < 100_000:
        candidates.append(config_max)

    text_config = getattr(model.config, "text_config", None)

    if text_config is not None:
        text_config_max = getattr(
            text_config,
            "max_position_embeddings",
            None,
        )

        if (
            isinstance(text_config_max, int)
            and text_config_max < 100_000
        ):
            candidates.append(text_config_max)

    if candidates:
        return int(min(candidates))

    return 2048

def load_excluded_stimuli(path):
    if path is None:
        return set()

    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"Excluded-stimuli file does not exist: {path}"
        )

    excluded = set()

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            stimulus = line.strip()

            if stimulus:
                excluded.add(stimulus)

    return excluded

def get_input_type_and_files(stimuli_dir):
    stimuli_dir = Path(stimuli_dir)

    if not stimuli_dir.exists():
        raise FileNotFoundError(
            f"Stimuli directory does not exist: {stimuli_dir}"
        )

    if not stimuli_dir.is_dir():
        raise NotADirectoryError(
            f"Stimuli path is not a directory: {stimuli_dir}"
        )

    text_files = sorted(
        path
        for path in stimuli_dir.iterdir()
        if path.is_file()
        and path.suffix.lower() == ".txt"
    )

    image_files = sorted(
        path
        for path in stimuli_dir.iterdir()
        if path.is_file()
        and path.suffix.lower() in {".jpg", ".jpeg", ".png"}
    )

    if text_files and image_files:
        raise ValueError(
            f"Stimuli directory contains both text and image files: "
            f"{stimuli_dir}. Each execution must process only one input type."
        )

    if text_files:
        return "language", text_files

    if image_files:
        return "visual", image_files

    raise ValueError(
        f"No supported input files found in {stimuli_dir}. "
        "Expected .txt, .jpg, .jpeg, or .png files."
    )

def model_input_device(model):
    try:
        return model.get_input_embeddings().weight.device
    except Exception:
        return next(model.parameters()).device

def move_inputs_to_device(inputs, device):
    moved = {}

    for key, value in inputs.items():
        if isinstance(value, torch.Tensor):
            moved[key] = value.to(device)
        else:
            moved[key] = value

    return moved

def extract_embedding_from_output(
    output,
    attention_mask: torch.Tensor | None = None,
    input_type: str | None = None,
) -> torch.Tensor:
    if input_type == "visual":
        image_embeds = getattr(output, "image_embeds", None)

        if isinstance(image_embeds, torch.Tensor):
            return image_embeds.squeeze(0)

        vision_model_output = getattr(
            output,
            "vision_model_output",
            None,
        )

        if vision_model_output is not None:
            pooler_output = getattr(
                vision_model_output,
                "pooler_output",
                None,
            )

            if isinstance(pooler_output, torch.Tensor):
                return pooler_output.squeeze(0)

            last_hidden_state = getattr(
                vision_model_output,
                "last_hidden_state",
                None,
            )

            if isinstance(last_hidden_state, torch.Tensor):
                return last_hidden_state.mean(dim=1).squeeze(0)

    if input_type == "language":
        text_embeds = getattr(output, "text_embeds", None)

        if isinstance(text_embeds, torch.Tensor):
            return text_embeds.squeeze(0)

        text_model_output = getattr(
            output,
            "text_model_output",
            None,
        )

        if text_model_output is not None:
            pooler_output = getattr(
                text_model_output,
                "pooler_output",
                None,
            )

            if isinstance(pooler_output, torch.Tensor):
                return pooler_output.squeeze(0)

            last_hidden_state = getattr(
                text_model_output,
                "last_hidden_state",
                None,
            )

            if isinstance(last_hidden_state, torch.Tensor):
                pooled = mean_pool_last_hidden(
                    last_hidden_state,
                    attention_mask,
                )

                return pooled.squeeze(0)

    pooler_output = getattr(output, "pooler_output", None)

    if isinstance(pooler_output, torch.Tensor):
        return pooler_output.squeeze(0)

    last_hidden_state = getattr(output, "last_hidden_state", None)

    if isinstance(last_hidden_state, torch.Tensor):
        pooled = mean_pool_last_hidden(
            last_hidden_state,
            attention_mask,
        )

        return pooled.squeeze(0)

    if isinstance(output, tuple):
        for value in output:
            if not isinstance(value, torch.Tensor):
                continue

            if value.ndim == 3:
                pooled = mean_pool_last_hidden(
                    value,
                    attention_mask,
                )

                return pooled.squeeze(0)

            if value.ndim == 2:
                return value.squeeze(0)

    raise ValueError(
        "Could not extract an embedding from the model output. "
        "This model may require a model-specific embedding procedure."
    )

def embed_long_text(
    text: str,
    tokenizer,
    model,
    device: torch.device,
    max_length: int = 2048,
    overlap: int = 256,
) -> tuple[torch.Tensor, int, int]:
    """
        Embed a potentially long text by splitting it into overlapping token chunks.

        Returns:
            final_embedding: tensor of shape [hidden_dim]
            n_tokens: number of original tokens before adding special tokens
            n_chunks: number of chunks used
    """
    if tokenizer is None:
        raise ValueError(
            "A tokenizer is required for language embedding."
        )

    if overlap < 0:
        raise ValueError("overlap must be >= 0")

    if overlap >= max_length:
        raise ValueError("overlap must be smaller than max_length")

    input_ids = tokenizer.encode(
        text,
        add_special_tokens=False,
    )

    n_tokens = len(input_ids)

    if n_tokens == 0:
        raise ValueError("Empty text after tokenization.")

    bos_token_id = getattr(tokenizer, "bos_token_id", None)
    eos_token_id = getattr(tokenizer, "eos_token_id", None)

    add_bos_token = bool(
        getattr(tokenizer, "add_bos_token", bos_token_id is not None)
    )

    add_eos_token = bool(
        getattr(tokenizer, "add_eos_token", False)
    )

    special_tokens_count = 0

    if add_bos_token and bos_token_id is not None:
        special_tokens_count += 1

    if add_eos_token and eos_token_id is not None:
        special_tokens_count += 1

    chunk_token_length = max_length - special_tokens_count

    if chunk_token_length <= 0:
        raise ValueError(
            f"max_length={max_length} is too small after accounting "
            f"for {special_tokens_count} special tokens."
        )

    step = chunk_token_length - overlap

    if step <= 0:
        raise ValueError(
            "overlap is too large after accounting for special tokens. "
            f"chunk_token_length={chunk_token_length}, overlap={overlap}"
        )

    chunk_embeddings = []
    chunk_lengths = []

    for start in range(0, n_tokens, step):
        chunk_ids = input_ids[start:start + chunk_token_length]

        if not chunk_ids:
            continue

        model_input_ids = []

        if add_bos_token and bos_token_id is not None:
            model_input_ids.append(bos_token_id)

        model_input_ids.extend(chunk_ids)

        if add_eos_token and eos_token_id is not None:
            model_input_ids.append(eos_token_id)

        if len(model_input_ids) > max_length:
            raise RuntimeError(
                f"Chunk length {len(model_input_ids)} exceeds "
                f"max_length={max_length}."
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

        model_inputs = {
            "input_ids": input_ids_tensor,
            "attention_mask": attention_mask,
            "output_hidden_states": False,
            "return_dict": True,
        }

        with torch.inference_mode():
            try:
                model_output = model(
                    **model_inputs,
                    use_cache=False,
                )
            except TypeError:
                model_output = model(
                    **model_inputs,
                )

        embedding = extract_embedding_from_output(
            output=model_output,
            attention_mask=attention_mask,
            input_type="language",
        )

        chunk_embeddings.append(
            embedding.detach().cpu().float()
        )
        chunk_lengths.append(len(chunk_ids))

        del input_ids_tensor
        del attention_mask
        del model_output
        del embedding

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    if not chunk_embeddings:
        raise ValueError("No chunks were produced for text.")

    chunks = torch.stack(
        chunk_embeddings,
        dim=0,
    ).float()

    weights = torch.tensor(
        chunk_lengths,
        dtype=torch.float32,
    ).unsqueeze(1)

    final_embedding = (
        (chunks * weights).sum(dim=0)
        / weights.sum()
    )

    return final_embedding, n_tokens, len(chunk_embeddings)

def embed_visual_input(
    image_path,
    processor,
    model,
    device,
) -> torch.Tensor:
    if processor is None:
        raise ValueError(
            "An AutoProcessor-compatible processor is required "
            "for visual embedding."
        )

    with Image.open(image_path) as image:
        image = image.convert("RGB")

        inputs = processor(
            images=image,
            return_tensors="pt",
        )

    inputs = move_inputs_to_device(inputs, device)

    with torch.inference_mode():
        if hasattr(model, "get_image_features"):
            embedding = model.get_image_features(**inputs)
            embedding = embedding.squeeze(0)
        else:
            model_output = model(
                **inputs,
                return_dict=True,
            )

            embedding = extract_embedding_from_output(
                output=model_output,
                input_type="visual",
            )

            del model_output

    embedding = embedding.detach().cpu().float()

    del inputs

    return embedding

def embed_multimodal_input(
    text,
    image_path,
    processor,
    model,
    device,
    tokenizer,
    max_length,
    input_type,
) -> tuple[torch.Tensor, int | None]:
    if processor is None:
        raise ValueError(
            "An AutoProcessor-compatible processor is required "
            "for multimodal embedding."
        )

    processor_kwargs = {
        "return_tensors": "pt",
    }

    image = None

    if input_type == "language":
        if text is None:
            raise ValueError(
                "A text input is required when input_type is language."
            )

        processor_kwargs["text"] = text
        processor_kwargs["truncation"] = True
        processor_kwargs["max_length"] = max_length

    elif input_type == "visual":
        if image_path is None:
            raise ValueError(
                "An image input is required when input_type is visual."
            )

        image = Image.open(image_path).convert("RGB")
        processor_kwargs["images"] = image

    else:
        raise ValueError(
            f"Unsupported input type for multimodal model: {input_type}"
        )

    try:
        inputs = processor(**processor_kwargs)
    finally:
        if image is not None:
            image.close()

    inputs = move_inputs_to_device(inputs, device)

    n_tokens = None

    if input_type == "language" and tokenizer is not None:
        n_tokens = len(
            tokenizer.encode(
                text,
                add_special_tokens=False,
            )
        )

    with torch.inference_mode():
        if (
            input_type == "language"
            and hasattr(model, "get_text_features")
        ):
            embedding = model.get_text_features(**inputs)
            embedding = embedding.squeeze(0)

        elif (
            input_type == "visual"
            and hasattr(model, "get_image_features")
        ):
            embedding = model.get_image_features(**inputs)
            embedding = embedding.squeeze(0)

        else:
            model_output = model(
                **inputs,
                return_dict=True,
            )

            attention_mask = inputs.get("attention_mask")

            embedding = extract_embedding_from_output(
                output=model_output,
                attention_mask=attention_mask,
                input_type=input_type,
            )

            del model_output

    embedding = embedding.detach().cpu().float()

    del inputs

    return embedding, n_tokens

def read_text_file(path):
    with Path(path).open("r", encoding="utf-8") as f:
        return f.read()

def main():
    parser = argparse.ArgumentParser(
        description="Embed language, visual, or multimodal stimuli"
    )
    parser.add_argument(
        "--stimuli_dir",
        required=True,
        help=(
            "Path to a directory containing either text files or image files. "
            "Each execution must process only one input type."
        ),
    )
    parser.add_argument(
        "--output",
        required=True,
        help=(
            "Path to the output Parquet file containing one embedding "
            "per stimulus."
        ),
    )
    parser.add_argument(
        "--modality",
        required=True,
        choices=["language", "visual", "multimodal"],
        help="Modality in which the model is expected to operate.",
    )
    parser.add_argument(
        "--model_path",
        required=True,
        help="Path or Hugging Face identifier of the model.",
    )
    parser.add_argument(
        "--quantization_method",
        choices=["4bit", "8bit"],
        default=None,
        help="Optional model quantization method.",
    )
    parser.add_argument(
        "--excluded_stimuli",
        default=None,
        help=(
            "Path to a text file containing one stimulus ID per line. "
            "Files whose stem matches one of these IDs are excluded."
        ),
    )
    parser.add_argument(
        "--chunk_max_length",
        type=int,
        default=None,
        help=(
            "Maximum language-model input length per chunk. "
            "Default: inferred, usually 2048."
        ),
    )
    parser.add_argument(
        "--chunk_overlap",
        type=int,
        default=256,
        help=(
            "Number of overlapping text tokens between adjacent chunks. "
            "Used for language-only models."
        ),
    )
    args = parser.parse_args()

    input_type, input_files = get_input_type_and_files(
        args.stimuli_dir
    )

    if args.modality == "language" and input_type != "language":
        raise ValueError(
            "A language-only model cannot process visual inputs."
        )

    if args.modality == "visual" and input_type != "visual":
        raise ValueError(
            "A visual-only model cannot process language inputs."
        )

    excluded_stimuli = load_excluded_stimuli(
        args.excluded_stimuli
    )

    print(
        f"Loaded {len(excluded_stimuli)} excluded stimuli",
        flush=True,
    )

    items = []

    for filepath in input_files:
        concept = filepath.stem

        if concept in excluded_stimuli:
            print(
                f"Skipping excluded stimulus: {concept}",
                flush=True,
            )
            continue

        items.append(
            {
                "concept": concept,
                "filepath": filepath,
            }
        )

    if not items:
        raise ValueError(
            f"No valid {input_type} stimuli remained after exclusions."
        )

    tokenizer = None
    processor = None

    if args.modality == "language":
        tokenizer = AutoTokenizer.from_pretrained(
            args.model_path,
            trust_remote_code=True,
        )

        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

    else:
        processor = AutoProcessor.from_pretrained(
            args.model_path,
            trust_remote_code=True,
        )

        tokenizer = getattr(processor, "tokenizer", None)

        if tokenizer is not None and tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

    quantization_config = None

    if args.quantization_method == "4bit":
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True
        )

    elif args.quantization_method == "8bit":
        quantization_config = BitsAndBytesConfig(
            load_in_8bit=True
        )

    if quantization_config is not None:
        model = AutoModel.from_pretrained(
            args.model_path,
            quantization_config=quantization_config,
            device_map="auto",
            trust_remote_code=True,
        )

    else:
        device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )

        model = AutoModel.from_pretrained(
            args.model_path,
            trust_remote_code=True,
        ).to(device)

    model.eval()

    device = model_input_device(model)

    max_length = get_safe_max_length(
        tokenizer=tokenizer,
        model=model,
        user_max_length=args.chunk_max_length,
    )

    if input_type == "language":
        if args.chunk_overlap >= max_length:
            raise ValueError(
                "--chunk_overlap must be smaller than the chunk maximum "
                f"length. Got overlap={args.chunk_overlap}, "
                f"max_length={max_length}."
            )

        print(
            f"Using chunk_max_length={max_length}, "
            f"chunk_overlap={args.chunk_overlap}",
            flush=True,
        )

    concepts = []
    embeddings = []
    embedding_dimension = None

    for item in items:
        concept = item["concept"]
        filepath = item["filepath"]

        if args.modality == "language":
            text = read_text_file(filepath)

            embedding, n_tokens, n_chunks = embed_long_text(
                text=text,
                tokenizer=tokenizer,
                model=model,
                device=device,
                max_length=max_length,
                overlap=args.chunk_overlap,
            )

        elif args.modality == "visual":
            embedding = embed_visual_input(
                image_path=filepath,
                processor=processor,
                model=model,
                device=device,
            )

            n_tokens = None
            n_chunks = None

        else:
            if input_type == "language":
                text = read_text_file(filepath)
                image_path = None
            else:
                text = None
                image_path = filepath

            embedding, n_tokens = embed_multimodal_input(
                text=text,
                image_path=image_path,
                processor=processor,
                model=model,
                device=device,
                tokenizer=tokenizer,
                max_length=max_length,
                input_type=input_type,
            )

            n_chunks = 1

        embedding = embedding.reshape(-1).float()

        if embedding_dimension is None:
            embedding_dimension = embedding.numel()

        elif embedding.numel() != embedding_dimension:
            raise ValueError(
                f"Inconsistent embedding dimension for {concept}: "
                f"expected {embedding_dimension}, "
                f"got {embedding.numel()}."
            )

        if not torch.isfinite(embedding).all():
            raise ValueError(
                f"Embedding for {concept} contains NaN or infinite values."
            )

        print(
            f"{concept}: model_modality={args.modality}, "
            f"input_type={input_type}, "
            f"n_tokens={n_tokens}, n_chunks={n_chunks}, "
            f"embedding_dimension={embedding.numel()}",
            flush=True,
        )

        concepts.append(concept)
        embeddings.append(
            embedding.detach().cpu().numpy().astype("float32")
        )

        del embedding

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    if len(concepts) != len(set(concepts)):
        duplicated_concepts = sorted(
            {
                concept
                for concept in concepts
                if concepts.count(concept) > 1
            }
        )

        raise ValueError(
            f"Duplicate concept names found: {duplicated_concepts}"
        )

    embeddings_df = pd.DataFrame(
        embeddings,
        index=pd.Index(
            concepts,
            name="concept",
        ),
        columns=[
            i
            for i in range(embedding_dimension)
        ],
        dtype="float32",
    )
    
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    embeddings_df.to_parquet(
        output_path,
        engine="pyarrow",
        index=False,
    )
    
    print(
        f"Wrote {len(embeddings_df)} embeddings with {embedding_dimension} dimensions to {output_path}",
        flush=True,
    )

if __name__ == "__main__":
    main()