import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from libraries.compute_spearman_alignment import align_similarity_dataframes, rank_upper_triangle

def compute_relabelled_coefficients(brain_rank_geometry, model_rank_geometry, row_indices, column_indices, number_of_concepts, number_of_relabellings, random_seed):
    model_rank_matrix = np.zeros(
        (number_of_concepts, number_of_concepts),
        dtype=np.float64,
    )
    model_rank_matrix[row_indices, column_indices] = model_rank_geometry
    model_rank_matrix[column_indices, row_indices] = model_rank_geometry
    coefficients = np.empty(number_of_relabellings, dtype=np.float64)

    for shuffle_i in range(number_of_relabellings):
        rng = np.random.default_rng(random_seed + shuffle_i)
        permutation = rng.permutation(number_of_concepts)
        relabelled_model_geometry = model_rank_matrix[
            permutation[row_indices],
            permutation[column_indices],
        ]
        coefficients[shuffle_i] = np.dot(
            brain_rank_geometry,
            relabelled_model_geometry,
        )

        if shuffle_i == 0 or (shuffle_i + 1) % 100 == 0 or shuffle_i + 1 == number_of_relabellings:
            print(f"completed relabelling {shuffle_i + 1}/{number_of_relabellings}")

    return np.clip(coefficients, -1.0, 1.0)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--brain_similarity", required=True)
    parser.add_argument("--model_similarity", required=True)
    parser.add_argument("--observed_alignment", required=True)
    parser.add_argument("--relabelled_alignment", required=True)
    parser.add_argument("--number_of_relabellings", type=int, required=True)
    parser.add_argument("--random_seed", type=int, default=0)
    args = parser.parse_args()

    if args.number_of_relabellings <= 0:
        raise ValueError("--number_of_relabellings must be a positive integer")

    brain_similarity_df = pd.read_parquet(args.brain_similarity, engine="pyarrow")
    model_similarity_df = pd.read_parquet(args.model_similarity, engine="pyarrow")
    brain_similarity, model_similarity, concepts = align_similarity_dataframes(
        brain_similarity_df=brain_similarity_df,
        model_similarity_df=model_similarity_df,
    )

    brain_rank_geometry, row_indices, column_indices = rank_upper_triangle(
        similarity=brain_similarity,
        name="brain pairwise",
    )
    model_rank_geometry, model_row_indices, model_column_indices = rank_upper_triangle(
        similarity=model_similarity,
        name="model pairwise",
    )

    if not np.array_equal(row_indices, model_row_indices) or not np.array_equal(column_indices, model_column_indices):
        raise ValueError("Brain and model upper-triangle indices do not match")

    observed_coefficient = float(
        np.clip(
            np.dot(brain_rank_geometry, model_rank_geometry),
            -1.0,
            1.0,
        )
    )
    relabelled_coefficients = compute_relabelled_coefficients(
        brain_rank_geometry=brain_rank_geometry,
        model_rank_geometry=model_rank_geometry,
        row_indices=row_indices,
        column_indices=column_indices,
        number_of_concepts=len(concepts),
        number_of_relabellings=args.number_of_relabellings,
        random_seed=args.random_seed,
    )

    observed_df = pd.DataFrame(
        {
            "number_of_concepts": [len(concepts)],
            "number_of_pairs": [len(row_indices)],
            "spearman_coefficient": [observed_coefficient],
        }
    )
    relabelled_df = pd.DataFrame(
        {
            "shuffle_id": pd.Categorical.from_codes(
                np.arange(args.number_of_relabellings, dtype=np.int32),
                categories=[
                    f"shuffle_{shuffle_i}"
                    for shuffle_i in range(args.number_of_relabellings)
                ],
                ordered=True,
            ),
            "spearman_coefficient": relabelled_coefficients,
        }
    )

    observed_path = Path(args.observed_alignment)
    relabelled_path = Path(args.relabelled_alignment)
    observed_path.parent.mkdir(parents=True, exist_ok=True)
    relabelled_path.parent.mkdir(parents=True, exist_ok=True)
    observed_df.to_parquet(observed_path, engine="pyarrow", compression="snappy", index=False)
    relabelled_df.to_parquet(relabelled_path, engine="pyarrow", compression="snappy", index=False)

if __name__ == "__main__":
    main()