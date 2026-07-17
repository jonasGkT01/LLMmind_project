#!/usr/bin/env python3
import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def validate_similarity_dataframe(similarity_df, path):
    if similarity_df.shape[0] != similarity_df.shape[1]:
        raise ValueError(f"{path} is not square: shape={similarity_df.shape}")

    if similarity_df.index.has_duplicates:
        raise ValueError(f"{path} contains duplicate row labels")

    if similarity_df.columns.has_duplicates:
        raise ValueError(f"{path} contains duplicate column labels")

    row_concepts = list(similarity_df.index)
    column_concepts = list(similarity_df.columns)

    if set(row_concepts) != set(column_concepts):
        raise ValueError(f"{path} does not contain the same concepts in its rows and columns")

    similarity_df = similarity_df.loc[row_concepts, row_concepts]
    values = similarity_df.to_numpy()

    if not np.issubdtype(values.dtype, np.number):
        raise ValueError(f"{path} contains non-numeric similarity values")

    if not np.isfinite(values).all():
        raise ValueError(f"{path} contains non-finite similarity values")

    return similarity_df


def select_shared_concepts(similarity_df_1, similarity_df_2):
    concepts_1 = list(similarity_df_1.index)
    concepts_2 = set(similarity_df_2.index)
    shared_concepts = [concept for concept in concepts_1 if concept in concepts_2]

    if len(shared_concepts) == 0:
        raise ValueError("No shared concepts were found between the two similarity matrices")

    similarity_df_1 = similarity_df_1.loc[shared_concepts, shared_concepts]
    similarity_df_2 = similarity_df_2.loc[shared_concepts, shared_concepts]

    return similarity_df_1, similarity_df_2


def compute_topk_indices(similarity_df, number_of_neighbours):
    similarity = similarity_df.to_numpy(copy=True)

    if similarity.shape[0] < number_of_neighbours + 1:
        raise ValueError(f"Requested {number_of_neighbours} neighbours, but only {similarity.shape[0]} shared concepts are available")

    np.fill_diagonal(similarity, -np.inf)
    partitioned_indices = np.argpartition(similarity, -number_of_neighbours, axis=1)[:, -number_of_neighbours:]
    partitioned_scores = np.take_along_axis(similarity, partitioned_indices, axis=1)
    order = np.argsort(partitioned_scores, axis=1)[:, ::-1]
    topk_indices = np.take_along_axis(partitioned_indices, order, axis=1)

    return topk_indices.astype(np.int64)


def create_neighbour_mask(neighbours):
    number_of_concepts = neighbours.shape[0]
    concept_indices = np.arange(number_of_concepts, dtype=np.int64)
    neighbour_mask = np.zeros((number_of_concepts, number_of_concepts), dtype=bool)
    neighbour_mask[concept_indices[:, None], neighbours] = True

    return neighbour_mask, concept_indices


def compute_mean_alignment_score(neighbour_mask_1, neighbours_2, concept_indices, number_of_neighbours):
    if neighbour_mask_1.shape[0] != neighbours_2.shape[0]:
        raise ValueError("The two nearest-neighbour representations have different numbers of concepts")

    common_neighbours = neighbour_mask_1[concept_indices[:, None], neighbours_2].sum(axis=1)
    alignment_scores = common_neighbours / number_of_neighbours

    return float(alignment_scores.mean())


def relabel_nearest_neighbours(observed_neighbours, permutation, inverse_permutation, concept_indices):
    inverse_permutation[permutation] = concept_indices

    return inverse_permutation[observed_neighbours[permutation]]


def read_observed_alignment_score(path):
    observed_df = pd.read_parquet(path, engine="pyarrow")

    if "alignment_score" not in observed_df.columns:
        raise ValueError(f"{path} does not contain an 'alignment_score' column")

    if observed_df.empty:
        raise ValueError(f"{path} does not contain any rows")

    alignment_scores = observed_df["alignment_score"].to_numpy(dtype=float)

    if not np.isfinite(alignment_scores).all():
        raise ValueError(f"{path} contains non-finite alignment scores")

    return float(alignment_scores.mean())


def compute_empirical_p_value(observed_alignment_score, neighbours_1, neighbours_2, number_of_neighbours, number_of_relabellings, random_seed):
    neighbour_mask_1, concept_indices = create_neighbour_mask(neighbours_1)
    inverse_permutation = np.empty(neighbours_2.shape[0], dtype=np.int64)
    rng = np.random.default_rng(random_seed)
    number_at_least_as_extreme = 0

    for shuffle_i in range(number_of_relabellings):
        permutation = rng.permutation(neighbours_2.shape[0])
        relabelled_neighbours_2 = relabel_nearest_neighbours(
            observed_neighbours=neighbours_2,
            permutation=permutation,
            inverse_permutation=inverse_permutation,
            concept_indices=concept_indices,
        )
        relabelled_alignment_score = compute_mean_alignment_score(
            neighbour_mask_1=neighbour_mask_1,
            neighbours_2=relabelled_neighbours_2,
            concept_indices=concept_indices,
            number_of_neighbours=number_of_neighbours,
        )

        if relabelled_alignment_score >= observed_alignment_score:
            number_at_least_as_extreme += 1

        if shuffle_i == 0 or (shuffle_i + 1) % 100 == 0 or shuffle_i + 1 == number_of_relabellings:
            print(f"completed relabelling {shuffle_i + 1}/{number_of_relabellings}")

    empirical_p_value = (number_at_least_as_extreme + 1) / (number_of_relabellings + 1)

    return empirical_p_value, number_at_least_as_extreme


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--observed_alignment_score", required=True)
    parser.add_argument("--llm_similarity_1", required=True)
    parser.add_argument("--llm_similarity_2", required=True)
    parser.add_argument("--empirical_p_value", required=True)
    parser.add_argument("--number_of_neighbours", type=int, required=True)
    parser.add_argument("--number_of_relabellings", type=int, required=True)
    parser.add_argument("--random_seed", type=int, default=0)
    parser.add_argument("--model_1", required=True)
    parser.add_argument("--model_2", required=True)
    parser.add_argument("--stimuli_type_1", required=True)
    parser.add_argument("--stimuli_type_2", required=True)
    parser.add_argument("--number_of_parameters_1", type=float, required=True)
    parser.add_argument("--number_of_parameters_2", type=float, required=True)
    args = parser.parse_args()

    if args.number_of_neighbours <= 0:
        raise ValueError("--number_of_neighbours must be a positive integer")

    if args.number_of_relabellings <= 0:
        raise ValueError("--number_of_relabellings must be a positive integer")

    observed_alignment_score = read_observed_alignment_score(args.observed_alignment_score)
    similarity_df_1 = pd.read_parquet(args.llm_similarity_1, engine="pyarrow")
    similarity_df_2 = pd.read_parquet(args.llm_similarity_2, engine="pyarrow")
    similarity_df_1 = validate_similarity_dataframe(similarity_df=similarity_df_1, path=args.llm_similarity_1)
    similarity_df_2 = validate_similarity_dataframe(similarity_df=similarity_df_2, path=args.llm_similarity_2)
    similarity_df_1, similarity_df_2 = select_shared_concepts(
        similarity_df_1=similarity_df_1,
        similarity_df_2=similarity_df_2,
    )
    neighbours_1 = compute_topk_indices(
        similarity_df=similarity_df_1,
        number_of_neighbours=args.number_of_neighbours,
    )
    neighbours_2 = compute_topk_indices(
        similarity_df=similarity_df_2,
        number_of_neighbours=args.number_of_neighbours,
    )
    empirical_p_value, number_at_least_as_extreme = compute_empirical_p_value(
        observed_alignment_score=observed_alignment_score,
        neighbours_1=neighbours_1,
        neighbours_2=neighbours_2,
        number_of_neighbours=args.number_of_neighbours,
        number_of_relabellings=args.number_of_relabellings,
        random_seed=args.random_seed,
    )

    result_df = pd.DataFrame(
        [
            {
                "model_1": args.model_1,
                "stimuli_type_1": args.stimuli_type_1,
                "number_of_parameters_1": args.number_of_parameters_1,
                "model_2": args.model_2,
                "stimuli_type_2": args.stimuli_type_2,
                "number_of_parameters_2": args.number_of_parameters_2,
                "number_of_shared_concepts": len(similarity_df_1),
                "number_of_neighbours": args.number_of_neighbours,
                "number_of_relabellings": args.number_of_relabellings,
                "random_seed": args.random_seed,
                "observed_alignment_score": observed_alignment_score,
                "number_at_least_as_extreme": number_at_least_as_extreme,
                "empirical_p_value": empirical_p_value,
            }
        ]
    )

    output_path = Path(args.empirical_p_value)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result_df.to_csv(output_path, sep="\t", index=False)


if __name__ == "__main__":
    main()