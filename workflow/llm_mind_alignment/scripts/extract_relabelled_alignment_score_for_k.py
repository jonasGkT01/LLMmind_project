import argparse
from pathlib import Path

import pandas as pd

def main():
    parser = argparse.ArgumentParser(
        description="Slice one number_of_neighbours' rows out of the combined relabelled-common-neighbours "
                     "file (see relabel_llm_similarity_and_compute_relabelled_llm_alignment_score.py), "
                     "reproducing the per-k file shape every other consumer already expects."
    )
    parser.add_argument("--relabelled_common_neighbours", required=True)
    parser.add_argument("--number_of_neighbours", type=int, required=True)
    parser.add_argument("--relabelled_alignment_score", required=True)
    args = parser.parse_args()

    combined_df = pd.read_parquet(args.relabelled_common_neighbours, engine="pyarrow")
    sliced_df = combined_df[combined_df["number_of_neighbours"] == args.number_of_neighbours].drop(columns=["number_of_neighbours"])

    if sliced_df.empty:
        raise ValueError(f"{args.relabelled_common_neighbours} has no rows for number_of_neighbours={args.number_of_neighbours}")

    output_path = Path(args.relabelled_alignment_score)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sliced_df.to_parquet(output_path, engine="pyarrow", compression="snappy", index=True)

if __name__ == "__main__":
    main()
