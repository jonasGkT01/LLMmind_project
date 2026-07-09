#!/usr/bin/env python3
import argparse
from pathlib import Path

import pandas as pd

def read_nearest_neighbours(path):
    df = pd.read_parquet(path, engine="pyarrow")

    required_columns = {"concept", "neighbour"}
    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"{path} is missing required columns: {sorted(missing_columns)}"
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

    nn_df_1 = read_nearest_neighbours(args.llm_nearest_neighbours_1)
    nn_df_2 = read_nearest_neighbours(args.llm_nearest_neighbours_2)

    nn_dict_1 = {
        concept: set(group["neighbour"])
        for concept, group in nn_df_1.groupby("concept")
    }

    nn_dict_2 = {
        concept: set(group["neighbour"])
        for concept, group in nn_df_2.groupby("concept")
    }

    concepts = sorted(set(nn_dict_1) & set(nn_dict_2))

    if len(concepts) == 0:
        raise ValueError(
            "No shared concepts found between the two nearest-neighbour files"
        )

    rows = []

    for concept in concepts:
        neighbours_1 = nn_dict_1[concept]
        neighbours_2 = nn_dict_2[concept]

        common_neighbours = len(neighbours_1 & neighbours_2)

        rows.append(
            {
                "concept": concept,
                "common_neighbours": common_neighbours,
                "alignment_score": common_neighbours / args.number_of_neighbours,
                "alignment_score_percentage": (
                    common_neighbours / args.number_of_neighbours * 100
                ),
            }
        )

    alignment_score_df = pd.DataFrame(rows)

    output_path = Path(args.alignment_score)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    alignment_score_df.to_parquet(output_path, engine="pyarrow", index=False)

if __name__ == "__main__":
    main()