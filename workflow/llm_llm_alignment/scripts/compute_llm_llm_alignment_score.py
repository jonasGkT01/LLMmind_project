#!/usr/bin/env python3
import argparse
from pathlib import Path

import pandas as pd

from libraries.compute_alignment import compute_alignment_scores
from libraries.validate_data import validate_required_columns

def read_nearest_neighbours(path):
    df = pd.read_parquet(path, engine = "pyarrow",)

    validate_required_columns(
        df = df,
        required_columns = {"concept", "neighbour",},
        source = str(path),
    )

    return df

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--number_of_neighbours", type=int, required=True)
    parser.add_argument("--llm_nearest_neighbours_1", type=str, required=True)
    parser.add_argument("--llm_nearest_neighbours_2", type=str, required=True)
    parser.add_argument("--alignment_score", type=str, required=True)
    args = parser.parse_args()

    if args.number_of_neighbours <= 0:
        raise ValueError("--number_of_neighbours must be a positive integer")

    llm_nearest_neighbours_1_df = read_nearest_neighbours(args.llm_nearest_neighbours_1)
    llm_nearest_neighbours_2_df = read_nearest_neighbours(args.llm_nearest_neighbours_2)

    alignment_score_df = compute_alignment_scores(
        nearest_neighbours_df_1 = llm_nearest_neighbours_1_df,
        nearest_neighbours_df_2 = llm_nearest_neighbours_2_df,
        number_of_neighbours = args.number_of_neighbours,
    )
    
    if alignment_score_df.empty:
        raise ValueError("No shared concepts found between the two nearest-neighbour files")

    output_path = Path(args.alignment_score)
    output_path.parent.mkdir(parents = True, exist_ok = True)

    alignment_score_df.to_parquet(output_path, engine = "pyarrow", index = True)

if __name__ == "__main__":
    main()