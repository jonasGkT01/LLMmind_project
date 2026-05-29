import argparse
from pathlib import Path
import pandas as pd
from similarity_lib import relabel_wide_similarity, compute_nearest_neighbours

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--n_random", type=int, required=True)
    parser.add_argument("--seed_start", type=int, default=0)
    parser.add_argument("--k", type=int, required=True)
    args = parser.parse_args()

    

    df = pd.read_parquet(args.input)
    if df.shape[0] != df.shape[1]:
        raise ValueError(f"Expected a square matrix, got {df.shape}.")

    if list(df.index) != list(df.columns):
        df.index = df.columns

    all_nns = {}
    for i in range(args.n_random):
        relabelled = relabel_wide_similarity(df, seed=args.seed_start + i)
        nn = compute_nearest_neighbours(relabelled, args.k)
        all_nns[f"shuffle_{i}"] = nn

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    big_df = pd.concat(all_nns, names=["shuffle_id", "row"])
    big_df.to_parquet(output_path, engine="pyarrow")

if __name__ == "__main__":
    main()
