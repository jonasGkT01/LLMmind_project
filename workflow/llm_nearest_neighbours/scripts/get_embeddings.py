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
        Embed a potentially long stimulus by splitting it into overlapping token chunks.

        Returns:
            final_embedding: tensor of shape [hidden_dim]
            n_tokens: number of original tokens before adding special tokens
            n_chunks: number of chunks used
    """
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
        raise ValueError("Empty stimulus after tokenization.")

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
            f"overlap is too large after accounting for special tokens. "
            f"chunk_token_length={chunk_token_length}, overlap={overlap}"
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

        chunk_embeddings.append(pooled.squeeze(0).detach().cpu())
        chunk_lengths.append(len(chunk_ids))

        del input_ids_tensor, attention_mask, llm_output, pooled

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    if not chunk_embeddings:
        raise ValueError("No chunks were produced for stimulus.")

    chunks = torch.stack(chunk_embeddings, dim=0).float()
    weights = torch.tensor(chunk_lengths, dtype=torch.float32).unsqueeze(1)

    final_embedding = (chunks * weights).sum(dim=0) / weights.sum()

    return final_embedding, n_tokens, len(chunk_embeddings)

def main():
    parser = argparse.ArgumentParser(description="Embed stimuli with chunking")
    parser.add_argument(
        "--stimuli_table",
        required=True,
        help="TSV file containing columns: task and stimulus"
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to the output file where embeddings will be saved"
    )
    parser.add_argument(
        "--model_path",
        required=True,
        help="Path to the language model"
    )
    parser.add_argument(
        "--quantization_method",
        choices=["4bit", "8bit"],
        default=None,
        help="Quantization method"
    )
    parser.add_argument(
        "--excluded_stimuli",
        nargs="*",
        default=[],
        help="List of stimuli to exclude from embedding"
    )
    parser.add_argument(
        "--chunk_max_length",
        type=int,
        default=None,
        help="Maximum model input length per chunk. Default: inferred, usually 2048."
    )
    parser.add_argument(
        "--chunk_overlap",
        type=int,
        default=256,
        help="Number of overlapping stimulus tokens between adjacent chunks."
    )
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
            f"--chunk_overlap must be smaller than chunk max length. "
            f"Got overlap={args.chunk_overlap}, max_length={max_length}."
        )

    print(
        f"Using chunk_max_length={max_length}, chunk_overlap={args.chunk_overlap}",
        flush=True,
    )

    stimuli_table = pd.read_csv(args.stimuli_table, sep="\t")

    required_columns = {"task", "stimulus"}
    missing_columns = required_columns - set(stimuli_table.columns)

    if missing_columns:
        raise ValueError(
            f"Stimuli table {args.stimuli_table} is missing columns "
            f"{sorted(missing_columns)}. "
            f"Available columns: {list(stimuli_table.columns)}"
        )

    stimuli_table["task"] = stimuli_table["task"].astype(str)
    stimuli_table["stimulus"] = stimuli_table["stimulus"].astype(str)

    if args.excluded_stimuli:
        stimuli_table = stimuli_table[
            ~stimuli_table["task"].isin(args.excluded_stimuli)
        ]

    if stimuli_table.empty:
        raise ValueError(
            f"No stimuli remaining after exclusions in {args.stimuli_table}"
        )

    items = stimuli_table[
        ["task", "stimulus"]
    ].to_dict(orient="records")

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

#            print(
#                f"{item['task']}: n_tokens={n_tokens}, n_chunks={n_chunks}",
#                flush=True,
#            )

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

    df = df.set_index("task")
    df.index.name = "task"

    metadata_cols = [
        "n_tokens",
        "n_chunks",
        "chunk_max_length",
        "chunk_overlap",
    ]

    embedding_cols = [
        c for c in df.columns
        if isinstance(c, int)
    ]

    unexpected_cols = [
        c for c in df.columns
        if c not in metadata_cols and c not in embedding_cols
    ]

    if unexpected_cols:
        raise ValueError(
            f"Unexpected non-embedding columns found: {unexpected_cols}"
        )

    df = df[metadata_cols + embedding_cols]

    df.to_parquet(args.output, engine="pyarrow", index=True)

if __name__ == "__main__":
    main()