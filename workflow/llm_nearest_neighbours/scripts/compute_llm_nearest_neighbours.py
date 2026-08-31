import argparse
from pathlib import Path

import pandas as pd

from libraries.compute_nearest_neighbours import create_nearest_neighbours_dataframe

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--number_of_neighbours", type=int, required=True)
    parser.add_argument("--similarity_dataframe", required=True)
    parser.add_argument("--nearest_neighbours", required=True)
    args = parser.parse_args()

    similarity_df = pd.read_parquet(args.similarity_dataframe)

    if similarity_df.shape[0] != similarity_df.shape[1]:
        raise ValueError(f"Expected a square similarity matrix, got {similarity_df.shape}")

    if list(similarity_df.index) != list(similarity_df.columns):
        raise ValueError("Expected similarity_df index and columns to match exactly")

    nearest_neighbours_df = create_nearest_neighbours_dataframe(similarity_df=similarity_df, number_of_neighbours = args.number_of_neighbours,)

    output_path = Path(args.nearest_neighbours)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    nearest_neighbours_df.to_parquet(output_path, engine="pyarrow", index=True)

if __name__ == "__main__":
    main()