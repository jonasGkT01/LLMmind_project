import argparse
from pathlib import Path

import numpy as np
import pandas as pd

def compute_relabelled_nearest_neighbours_numpy(
    similarity_df: pd.DataFrame,
    number_of_relabellings: int,
    number_of_neighbours: int,
    random_seed: int,
) -> pd.DataFrame:
    if similarity_df.shape[0] != similarity_df.shape[1]:
        raise ValueError(f"Expected a square matrix, got {similarity_df.shape}.")

    if list(similarity_df.index) != list(similarity_df.columns):
        raise ValueError("Expected index and columns to match exactly.")

    X = similarity_df.to_numpy(copy=True)
    concepts = similarity_df.index.to_numpy()
    neighbours = similarity_df.columns.to_numpy()

    n = X.shape[0]
    k = number_of_neighbours

    if n < k + 1:
        raise ValueError(
            f"Requested {k} neighbours, but only {n} concepts are available."
        )

    rows = []

    for shuffle_i in range(number_of_relabellings):
        rng = np.random.default_rng(random_seed + shuffle_i)

        X_shuffle = X.copy()

        for row_i in range(n):
            off_diag = np.r_[0:row_i, row_i + 1:n]
            X_shuffle[row_i, off_diag] = rng.permutation(X[row_i, off_diag])

        np.fill_diagonal(X_shuffle, -np.inf)

        idx_part = np.argpartition(X_shuffle, -k, axis=1)[:, -k:]
        scores_part = np.take_along_axis(X_shuffle, idx_part, axis=1)

        order = np.argsort(scores_part, axis=1)[:, ::-1]
        idx_topk = np.take_along_axis(idx_part, order, axis=1)
        scores_topk = np.take_along_axis(X_shuffle, idx_topk, axis=1)

        shuffle_df = pd.DataFrame(
            {
                "shuffle_id": f"shuffle_{shuffle_i}",
                "concept": np.repeat(concepts, k),
                "neighbour": neighbours[idx_topk.reshape(-1)],
                "similarity": scores_topk.reshape(-1),
            }
        )

        rows.append(shuffle_df)

        print(
            f"Completed relabelling {shuffle_i + 1}/{number_of_relabellings}",
            flush=True,
        )

    return pd.concat(rows, ignore_index=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--similarity_dataframe", required=True)
    parser.add_argument("--relabelled_nearest_neighbours", required=True)
    parser.add_argument("--number_of_relabellings", type=int, required=True)
    parser.add_argument("--random_seed", type=int, default=0)
    parser.add_argument("--number_of_neighbours", type=int, required=True)
    args = parser.parse_args()

    similarity_df = pd.read_parquet(args.similarity_dataframe)

    result = compute_relabelled_nearest_neighbours_numpy(
        similarity_df=similarity_df,
        number_of_relabellings=args.number_of_relabellings,
        number_of_neighbours=args.number_of_neighbours,
        random_seed=args.random_seed,
    )

    output_path = Path(args.relabelled_nearest_neighbours)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(output_path, engine="pyarrow", index=False)

if __name__ == "__main__":
    main()