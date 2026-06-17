import argparse
from pathlib import Path

import numpy as np
import pandas as pd

def compute_nearest_neighbours_from_array(
    X: np.ndarray,
    concepts: np.ndarray,
    neighbours: np.ndarray,
    number_of_neighbours: int,
) -> pd.DataFrame:
    if X.shape[1] - 1 < number_of_neighbours:
        raise ValueError(
            f"Requested {number_of_neighbours} neighbours, "
            f"but only {X.shape[1] - 1} candidates are available."
        )

    idx_part = np.argpartition(X, -number_of_neighbours, axis=1)[:, -number_of_neighbours:]
    scores_part = np.take_along_axis(X, idx_part, axis=1)

    order = np.argsort(scores_part, axis=1)[:, ::-1]
    idx_topk = np.take_along_axis(idx_part, order, axis=1)
    scores_topk = np.take_along_axis(X, idx_topk, axis=1)

    return pd.DataFrame(
        {
            "concept": np.repeat(concepts, number_of_neighbours),
            "neighbour": neighbours[idx_topk.reshape(-1)],
            "similarity": scores_topk.reshape(-1),
        }
    )

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--number_of_neighbours", type=int, required=True)
    parser.add_argument("--similarity_dataframe", required=True)
    parser.add_argument("--nearest_neighbours", required=True)
    args = parser.parse_args()

    similarity_df = pd.read_parquet(args.similarity_dataframe)

    if similarity_df.shape[0] != similarity_df.shape[1]:
        raise ValueError(f"Expected a square similarity matrix, got {similarity_df.shape}.")

    if list(similarity_df.index) != list(similarity_df.columns):
        raise ValueError("Expected similarity_df index and columns to match exactly.")

    X = similarity_df.to_numpy(copy=True)
    np.fill_diagonal(X, -np.inf)

    nearest_neighbours_df = compute_nearest_neighbours_from_array(
        X=X,
        concepts=similarity_df.index.to_numpy(),
        neighbours=similarity_df.columns.to_numpy(),
        number_of_neighbours=args.number_of_neighbours,
    )

    output_path = Path(args.nearest_neighbours)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    nearest_neighbours_df.to_parquet(output_path, engine="pyarrow", index=False)

if __name__ == "__main__":
    main()