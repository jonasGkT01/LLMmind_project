import argparse
from pathlib import Path
import pandas as pd
from similarity_lib import compute_nearest_neighbours

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--k", type=int, required=True)
    args = parser.parse_args()
    df = pd.read_parquet(args.input)
    if df.shape[0] != df.shape[1]:
        raise ValueError(f"Expected a square similarity matrix, got {df.shape}.")
    if list(df.index) != list(df.columns):
        df.index = df.columns
    nn = compute_nearest_neighbours(df, args.k)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    nn.to_parquet(output_path, engine="pyarrow", index=False)

if __name__ == "__main__":
    main()
