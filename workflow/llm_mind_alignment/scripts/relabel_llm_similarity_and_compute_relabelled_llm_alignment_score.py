import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from libraries.compute_alignment import compute_common_neighbours
from libraries.compute_nearest_neighbours import (
    compute_blockwise_topk_from_embeddings,
    create_neighbour_mask,
    relabel_nearest_neighbours,
    require_stored_number_of_neighbours,
)
from libraries.compute_similarity import extract_embedding_matrix, normalize_fn_for_similarity_type
from libraries.compute_statistics import create_relabelling_rng

def make_concept_index(concepts):
    return {concept: i for i, concept in enumerate(concepts)}

def encode_brain_nearest_neighbours(brain_nearest_neighbours_df, concepts, number_of_neighbours):
    concept_to_index = make_concept_index(concepts)
    neighbours_by_concept = brain_nearest_neighbours_df.groupby("concept", sort=False)["neighbour"].agg(list).to_dict()
    rows = []

    for concept in concepts:
        concept_neighbours = neighbours_by_concept.get(concept, [])

        if len(concept_neighbours) < number_of_neighbours:
            raise ValueError(f"Concept {concept} has only {len(concept_neighbours)} brain neighbours, but {number_of_neighbours} were requested")

        encoded_neighbours = []

        for neighbour in concept_neighbours[:number_of_neighbours]:
            if neighbour not in concept_to_index:
                raise ValueError(f"Brain neighbour {neighbour} for concept {concept} is not present in the relabelling concept set")

            encoded_neighbours.append(concept_to_index[neighbour])

        rows.append(encoded_neighbours)

    return np.asarray(rows, dtype=np.int64)

def select_common_neighbour_dtype(number_of_neighbours):
    if number_of_neighbours <= np.iinfo(np.uint8).max:
        return np.uint8

    if number_of_neighbours <= np.iinfo(np.uint16).max:
        return np.uint16

    if number_of_neighbours <= np.iinfo(np.uint32).max:
        return np.uint32

    raise ValueError("The requested number of neighbours is too large to store")

def create_relabelled_alignment_dataframe(common_neighbours_matrix, concepts, model, number_of_neighbours):
    number_of_relabellings, number_of_concepts = common_neighbours_matrix.shape
    number_of_rows = number_of_relabellings * number_of_concepts
    shuffle_codes = np.repeat(np.arange(number_of_relabellings, dtype=np.int32), number_of_concepts)
    concept_codes = np.tile(np.arange(number_of_concepts, dtype=np.int32), number_of_relabellings)
    common_neighbours = common_neighbours_matrix.reshape(-1)
    alignment_scores = common_neighbours.astype(np.float64) / number_of_neighbours

    result_df = pd.DataFrame(
        {
            "shuffle_id": pd.Categorical.from_codes(
                shuffle_codes,
                categories=[f"shuffle_{shuffle_i}" for shuffle_i in range(number_of_relabellings)],
                ordered=True,
            ),
            "model": pd.Categorical.from_codes(
                np.zeros(number_of_rows, dtype=np.int8),
                categories=[model],
            ),
            "concept": pd.Categorical.from_codes(
                concept_codes,
                categories=concepts,
                ordered=True,
            ),
            # Needed to tell k's apart in the combined all-k file (see main()): Snakemake outputs
            # can't depend on wildcards, so separate per-k files from one job aren't possible.
            "number_of_neighbours": np.full(number_of_rows, number_of_neighbours, dtype=np.int32),
            "common_neighbours": common_neighbours,
            "alignment_score": alignment_scores,
            "alignment_score_percentage": alignment_scores * 100,
        }
    )

    return result_df

def compute_relabelled_alignment_scores_for_all_k(
    embedding_df,
    brain_nearest_neighbours_df,
    number_of_relabellings,
    numbers_of_neighbours,
    random_seed,
    model,
    similarity_type,
):
    # `concepts` (the ISC-eligible ones) is the closed set every permutation works on. Both LLM and
    # brain neighbours must be positions in it, so the LLM top-k is recomputed on this subset.
    concepts = brain_nearest_neighbours_df["concept"].unique()

    missing_embedding_concepts = sorted(set(concepts) - set(embedding_df.index))

    if missing_embedding_concepts:
        raise ValueError(
            f"The model's embeddings are missing {len(missing_embedding_concepts)} concept(s) required "
            f"for relabelling, e.g. {missing_embedding_concepts[:5]}"
        )

    max_k = max(numbers_of_neighbours)
    concept_indices = np.arange(len(concepts), dtype=np.int64)

    restricted_embedding_matrix = extract_embedding_matrix(embedding_df.loc[concepts])
    normalize_fn = normalize_fn_for_similarity_type(similarity_type)

    observed_llm_neighbours, _ = compute_blockwise_topk_from_embeddings(
        embedding_matrix = restricted_embedding_matrix,
        number_of_neighbours = max_k,
        normalize_fn = normalize_fn,
    )

    brain_neighbours_at_max_k = encode_brain_nearest_neighbours(
        brain_nearest_neighbours_df = brain_nearest_neighbours_df,
        concepts = concepts,
        number_of_neighbours = max_k,
    )

    brain_neighbour_masks_by_k = {}
    common_neighbours_matrices_by_k = {}

    for k in numbers_of_neighbours:
        mask, _ = create_neighbour_mask(brain_neighbours_at_max_k[:, :k])
        brain_neighbour_masks_by_k[k] = mask
        common_neighbours_matrices_by_k[k] = np.empty(
            (number_of_relabellings, len(concepts)),
            dtype = select_common_neighbour_dtype(k),
        )

    inverse_permutation = np.empty(len(concepts), dtype=np.int64)

    for shuffle_i in range(number_of_relabellings):
        rng = create_relabelling_rng(random_seed, shuffle_i)
        permutation = rng.permutation(len(concepts))
        relabelled_llm_neighbours = relabel_nearest_neighbours(
            observed_neighbours=observed_llm_neighbours,
            permutation=permutation,
            inverse_permutation=inverse_permutation,
            concept_indices=concept_indices,
        )

        for k in numbers_of_neighbours:
            common_neighbours_matrices_by_k[k][shuffle_i] = compute_common_neighbours(
                neighbours = relabelled_llm_neighbours[:, :k],
                neighbour_mask = brain_neighbour_masks_by_k[k],
                concept_indices = concept_indices,
            )

        if shuffle_i == 0 or (shuffle_i + 1) % 100 == 0 or shuffle_i + 1 == number_of_relabellings:
            print(f"completed relabelling {shuffle_i + 1}/{number_of_relabellings}")

    return {
        k: create_relabelled_alignment_dataframe(
            common_neighbours_matrix = common_neighbours_matrices_by_k[k],
            concepts = concepts,
            model = model,
            number_of_neighbours = k,
        )
        for k in numbers_of_neighbours
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--embedding_dataframe", required=True)
    parser.add_argument("--isc_nearest_neighbours", required=True)
    parser.add_argument("--similarity_type", required=True)
    parser.add_argument("--relabelled_common_neighbours", required=True,
                        help="Single output holding every --number_of_neighbours' rows, distinguished by "
                             "a number_of_neighbours column; per-k files are sliced from it separately "
                             "(extract_relabelled_alignment_score_for_k.py) since a Snakemake rule's "
                             "output can't itself be a function of wildcards")
    parser.add_argument("--number_of_relabellings", type=int, required=True)
    parser.add_argument("--number_of_neighbours", type=int, nargs="+", required=True)
    parser.add_argument("--random_seed", type=int, default=0)
    parser.add_argument("--model", type=str, required=True)
    args = parser.parse_args()

    if args.number_of_relabellings <= 0:
        raise ValueError("--number_of_relabellings must be a positive integer")

    if any(k <= 0 for k in args.number_of_neighbours):
        raise ValueError("--number_of_neighbours must all be positive integers")

    require_stored_number_of_neighbours(args.isc_nearest_neighbours, max(args.number_of_neighbours))
    brain_nearest_neighbours_df = pd.read_parquet(args.isc_nearest_neighbours, engine="pyarrow")

    embedding_df = pd.read_parquet(args.embedding_dataframe)

    results_by_k = compute_relabelled_alignment_scores_for_all_k(
        embedding_df=embedding_df,
        brain_nearest_neighbours_df=brain_nearest_neighbours_df,
        number_of_relabellings=args.number_of_relabellings,
        numbers_of_neighbours=args.number_of_neighbours,
        random_seed=args.random_seed,
        model=args.model,
        similarity_type=args.similarity_type,
    )

    combined_df = pd.concat(
        [results_by_k[k] for k in args.number_of_neighbours],
        ignore_index=True,
    )

    output_path = Path(args.relabelled_common_neighbours)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined_df.to_parquet(output_path, engine="pyarrow", compression="snappy", index=True)

if __name__ == "__main__":
    main()
