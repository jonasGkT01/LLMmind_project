import os
import re
import argparse

import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModel, BitsAndBytesConfig

def mean_pool_last_hidden(
    last_hidden_state: torch.Tensor,
    attention_mask: torch.Tensor,
) -> torch.Tensor:
    mask = attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()
    summed = (last_hidden_state * mask).sum(dim=1)
    counts = mask.sum(dim=1).clamp(min=1e-9)
    return summed / counts

def get_safe_max_length(tokenizer, model, user_max_length: int | None = None) -> int:
    """
        Determine a safe context length for the model.

        For OpenLLaMA/BLOOM-like models, 2048 is a safe default.
        Some tokenizers expose huge placeholder values, so we avoid blindly trusting
        tokenizer.model_max_length.
    """
    if user_max_length is not None:
        return int(user_max_length)

    candidates = []

    tokenizer_max = getattr(tokenizer, "model_max_length", None)
    if isinstance(tokenizer_max, int) and tokenizer_max < 100_000:
        candidates.append(tokenizer_max)

    config_max = getattr(model.config, "max_position_embeddings", None)
    if isinstance(config_max, int) and config_max < 100_000:
        candidates.append(config_max)

    if candidates:
        return int(min(candidates))

    return 2048

def embed_long_text(
    text: str,
    tokenizer,
    model,
    device: torch.device,
    max_length: int = 2048,
    overlap: int = 256,
) -> tuple[torch.Tensor, int, int]:
    """
        Embed a potentially long transcript by splitting it into overlapping token chunks.

        Returns:
            final_embedding: tensor of shape [hidden_dim]
            n_tokens: number of original tokens before adding special tokens
            n_chunks: number of chunks used
    """
    if overlap < 0:
        raise ValueError("overlap must be >= 0")

    if overlap >= max_length:
        raise ValueError("overlap must be smaller than max_length")

    # Tokenize without special tokens. This may print a length warning in some
    # tokenizer versions, but these IDs are NOT passed to the model all at once.
    input_ids = tokenizer.encode(
        text,
        add_special_tokens=False,
    )

    n_tokens = len(input_ids)

    if n_tokens == 0:
        raise ValueError("Empty transcript after tokenization.")

    # Manually add only BOS when available. This avoids tokenizer helper methods
    # that are absent in your LlamaTokenizer wrapper.
    bos_token_id = getattr(tokenizer, "bos_token_id", None)

    n_manual_special = 1 if bos_token_id is not None else 0
    chunk_token_length = max_length - n_manual_special

    if chunk_token_length <= 0:
        raise ValueError(
            f"max_length={max_length} is too small after accounting for BOS."
        )

    step = chunk_token_length - overlap

    if step <= 0:
        raise ValueError(
            f"overlap is too large after accounting for special tokens. chunk_token_length={chunk_token_length}, overlap={overlap}"
        )

    chunk_embeddings = []
    chunk_lengths = []

    for start in range(0, n_tokens, step):
        chunk_ids = input_ids[start:start + chunk_token_length]

        if not chunk_ids:
            continue

        if bos_token_id is not None:
            model_input_ids = [bos_token_id] + chunk_ids
        else:
            model_input_ids = chunk_ids

        if len(model_input_ids) > max_length:
            raise RuntimeError(
                f"Chunk length {len(model_input_ids)} exceeds max_length={max_length}."
            )

        input_ids_tensor = torch.tensor(
            [model_input_ids],
            dtype=torch.long,
            device=device,
        )

        attention_mask = torch.ones_like(input_ids_tensor, device=device)

        with torch.inference_mode():
            llm_output = model(
                input_ids=input_ids_tensor,
                attention_mask=attention_mask,
                output_hidden_states=False,
                return_dict=True,
                use_cache=False,
            )

        pooled = mean_pool_last_hidden(
            llm_output.last_hidden_state,
            attention_mask,
        )

        # Weight by original transcript tokens, excluding the manually added BOS.
        chunk_embeddings.append(pooled.squeeze(0).detach().cpu())
        chunk_lengths.append(len(chunk_ids))

        del input_ids_tensor, attention_mask, llm_output, pooled

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    if not chunk_embeddings:
        raise ValueError("No chunks were produced for transcript.")

    chunks = torch.stack(chunk_embeddings, dim=0).float()
    weights = torch.tensor(chunk_lengths, dtype=torch.float32).unsqueeze(1)

    final_embedding = (chunks * weights).sum(dim=0) / weights.sum()

    return final_embedding, n_tokens, len(chunk_embeddings)

def main():
    parser = argparse.ArgumentParser(description="Embed transcripts with chunking")
    parser.add_argument(
        "--stimuli_dir",
        required=True,
        help="Path to the input directory containing txt files to embed")
    parser.add_argument(
        "--output",
        required=True,
        help="Path to the output file where embeddings will be saved")
    parser.add_argument(
        "--model_path",
        required=True,
        help="Path to the language model")
    parser.add_argument(
        "--quantization_method",
        choices=["4bit", "8bit"],
        default=None,
        help="Quantization method")
    parser.add_argument(
        "--excluded_stimuli",
        nargs="*",
        default=[],
        help="List of stimuli to exclude from embedding")
    parser.add_argument(
        "--chunk_max_length",
        type=int,
        default=None,
        help="Maximum model input length per chunk. Default: inferred, usually 2048.")
    parser.add_argument(
        "--chunk_overlap",
        type=int,
        default=256,
        help="Number of overlapping transcript tokens between adjacent chunks.")
    args = parser.parse_args()

    tokenizer = AutoTokenizer.from_pretrained(args.model_path)

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    quantization_config = None
    if args.quantization_method == "4bit":
        quantization_config = BitsAndBytesConfig(load_in_4bit=True)
    elif args.quantization_method == "8bit":
        quantization_config = BitsAndBytesConfig(load_in_8bit=True)

    if quantization_config is not None:
        model = AutoModel.from_pretrained(
            args.model_path,
            quantization_config=quantization_config,
            device_map="auto",
        )
        device = next(model.parameters()).device
    else:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = AutoModel.from_pretrained(args.model_path).to(device)

    model.eval()

    # For quantized models with device_map="auto", this is usually the correct input device.
    device = next(model.parameters()).device

    max_length = get_safe_max_length(
        tokenizer=tokenizer,
        model=model,
        user_max_length=args.chunk_max_length,
    )

    if args.chunk_overlap >= max_length:
        raise ValueError(
            f"--chunk_overlap must be smaller than chunk max length. Got overlap={args.chunk_overlap}, max_length={max_length}."
        )

    print(
        f"Using chunk_max_length={max_length}, chunk_overlap={args.chunk_overlap}",
        flush=True,
    )

    # Load txt files and keep both task name and stimulus text.
    items = []
    pattern = re.compile(r"^(.+)_transcript\.txt$")

    for filename in sorted(os.listdir(args.stimuli_dir)):
        match = pattern.match(filename)
        if not match:
            continue

        task = match.group(1)

        if task in args.excluded_stimuli:
            continue

        filepath = os.path.join(args.stimuli_dir, filename)

        with open(filepath, "r", encoding="utf-8") as f:
            stimulus = f.read()

        items.append(
            {
                "task": task,
                "stimulus": stimulus,
            }
        )

    if not items:
        raise ValueError(
            f"No input files found in {args.stimuli_dir}. Expected files matching '*_transcript.txt'."
        )

    records = []

    with torch.no_grad():
        for item in items:
            embedding, n_tokens, n_chunks = embed_long_text(
                text=item["stimulus"],
                tokenizer=tokenizer,
                model=model,
                device=device,
                max_length=max_length,
                overlap=args.chunk_overlap,
            )

            print(
                f"{item['task']}: n_tokens={n_tokens}, n_chunks={n_chunks}",
                flush=True,
            )

            records.append(
                {
                    "task": item["task"],
                    "n_tokens": n_tokens,
                    "n_chunks": n_chunks,
                    "chunk_max_length": max_length,
                    "chunk_overlap": args.chunk_overlap,
                    **{
                        i: value
                        for i, value in enumerate(
                            embedding.numpy().astype("float32")
                        )
                    },
                }
            )

            del embedding

            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    df = pd.DataFrame(records)

    # Use task name as the dataframe index.
    df = df.set_index("task")
    df.index.name = "task"

    metadata_cols = [
        "n_tokens",
        "n_chunks",
        "chunk_max_length",
        "chunk_overlap",
    ]

    # Your embedding columns are integer-labelled dimensions: 0, 1, 2, ..., hidden_size-1.
    embedding_cols = [
        c for c in df.columns
        if isinstance(c, int)
    ]

    unexpected_cols = [
        c for c in df.columns
        if c not in metadata_cols and c not in embedding_cols
    ]

    if unexpected_cols:
        raise ValueError(f"Unexpected non-embedding columns found: {unexpected_cols}")

    df = df[metadata_cols + embedding_cols]

    df.to_parquet(args.output, engine="pyarrow", index=True)
    
#    # print the alignment score dataframe
#    with pd.option_context("display.max_rows", None, "display.max_columns", None):
#        print(df)

if __name__ == "__main__":
    main()