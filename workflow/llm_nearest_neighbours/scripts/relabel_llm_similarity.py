import argparse
from pathlib import Path
import pandas as pd
from similarity_lib import relabel_wide_similarity

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--seed", type=int, required=True)
    args = parser.parse_args()
    df = pd.read_parquet(args.input)
    if df.shape[0] != df.shape[1]:
        raise ValueError(f"Expected a square similarity matrix, but got shape {df.shape}.")
    if list(df.index) != list(df.columns):
        df.index = df.columns
    relabelled = relabel_wide_similarity(df=df, seed=args.seed)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    relabelled.to_parquet(output_path, engine="pyarrow", index=True)

if __name__ == "__main__":
    main()
