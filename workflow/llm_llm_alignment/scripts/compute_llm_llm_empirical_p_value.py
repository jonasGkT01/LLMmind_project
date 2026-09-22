#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from libraries.compute_alignment import compute_mean_alignment_score
from libraries.compute_nearest_neighbours import compute_blockwise_topk_from_embeddings, create_neighbour_mask, relabel_nearest_neighbours
from libraries.compute_similarity import extract_embedding_matrix, normalize_fn_for_similarity_type
from libraries.compute_statistics import create_relabelling_rng, empirical_upper_tail_p_value

def read_embedding_concepts(path):
    parquet_file = pq.ParquetFile(path)
    pandas_metadata = json.loads(parquet_file.schema_arrow.metadata[b"pandas"])
    index_column = pandas_metadata["index_columns"][0]

    return pq.read_table(path, columns=[index_column]).column(index_column).to_pylist()

def select_shared_concepts(path_1, path_2):
    concepts_1 = read_embedding_concepts(path_1)
    concepts_2 = set(read_embedding_concepts(path_2))
    shared_concepts = [concept for concept in concepts_1 if concept in concepts_2]

    if len(shared_concepts) == 0:
        raise ValueError("No shared concepts were found between the two embedding dataframes")

    return shared_concepts

def compute_shared_subset_topk_indices(embedding_path, shared_concepts, number_of_neighbours, normalize_fn):
    # Computes top-k directly within the shared-concept subset (never persisting or reading a full N x N
    # matrix). This must be computed fresh from embeddings rather than filtering a larger, differently
    # scoped top-k file down to shared_concepts: neighbour indices here are positions within
    # shared_concepts specifically, which relabel_nearest_neighbours/create_neighbour_mask below require
    # to be a closed, self-consistent index space for the permutation to be well-defined.
    embedding_df = pd.read_parquet(embedding_path, engine="pyarrow")
    embedding_matrix = extract_embedding_matrix(embedding_df.loc[shared_concepts])

    neighbour_indices, _ = compute_blockwise_topk_from_embeddings(
        embedding_matrix=embedding_matrix,
        number_of_neighbours=number_of_neighbours,
        normalize_fn=normalize_fn,
    )

    return neighbour_indices

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
    number_at_least_as_extreme = 0

    for shuffle_i in range(number_of_relabellings):
        rng = create_relabelling_rng(random_seed, shuffle_i)
        permutation = rng.permutation(neighbours_2.shape[0])
        relabelled_neighbours_2 = relabel_nearest_neighbours(
            observed_neighbours=neighbours_2,
            permutation=permutation,
            inverse_permutation=inverse_permutation,
            concept_indices=concept_indices,
        )
        relabelled_alignment_score = compute_mean_alignment_score(
            neighbour_mask=neighbour_mask_1,
            neighbours=relabelled_neighbours_2,
            concept_indices=concept_indices,
            number_of_neighbours=number_of_neighbours,
        )

        if relabelled_alignment_score >= observed_alignment_score:
            number_at_least_as_extreme += 1

        if shuffle_i == 0 or (shuffle_i + 1) % 100 == 0 or shuffle_i + 1 == number_of_relabellings:
            print(f"completed relabelling {shuffle_i + 1}/{number_of_relabellings}")

    empirical_p_value = empirical_upper_tail_p_value(
        number_at_least_as_large = number_at_least_as_extreme,
        number_of_relabellings = number_of_relabellings,
    )

    return empirical_p_value, number_at_least_as_extreme

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--observed_alignment_score", required=True)
    parser.add_argument("--llm_embeddings_1", required=True)
    parser.add_argument("--llm_embeddings_2", required=True)
    parser.add_argument("--similarity_type", required=True)
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

    normalize_fn = normalize_fn_for_similarity_type(args.similarity_type)

    observed_alignment_score = read_observed_alignment_score(args.observed_alignment_score)

    shared_concepts = select_shared_concepts(args.llm_embeddings_1, args.llm_embeddings_2)

    neighbours_1 = compute_shared_subset_topk_indices(
        embedding_path = args.llm_embeddings_1,
        shared_concepts = shared_concepts,
        number_of_neighbours = args.number_of_neighbours,
        normalize_fn = normalize_fn,
    )
    neighbours_2 = compute_shared_subset_topk_indices(
        embedding_path = args.llm_embeddings_2,
        shared_concepts = shared_concepts,
        number_of_neighbours = args.number_of_neighbours,
        normalize_fn = normalize_fn,
    )

    empirical_p_value, number_at_least_as_extreme = compute_empirical_p_value(
        observed_alignment_score = observed_alignment_score,
        neighbours_1 = neighbours_1,
        neighbours_2 = neighbours_2,
        number_of_neighbours = args.number_of_neighbours,
        number_of_relabellings = args.number_of_relabellings,
        random_seed = args.random_seed,
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
                "number_of_shared_concepts": len(shared_concepts),
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
