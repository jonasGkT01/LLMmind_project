# edited with AI assistance: Claude Code, Claude Opus 5.5 (claude-opus-5-5)
# last AI edit: 2026-10-09, see docs/changelog/developers/ for details
import argparse

import numpy as np

from libraries.compute_nearest_neighbours import require_stored_number_of_neighbours
from libraries.compute_relabelled_alignment import (
    compute_relabelled_common_neighbours_for_all_k, 
    compute_topk_on_concept_subset, 
    create_relabelled_alignment_dataframe, 
    write_relabelled_common_neighbours, 
)
from libraries.parquet_io import read_parquet

def make_concept_index(concepts):
    return {concept: i for i, concept in enumerate(concepts)}

def encode_brain_nearest_neighbours(
    brain_nearest_neighbours_df, 
    concepts, 
    number_of_neighbours, 
):
    concept_to_index = make_concept_index(concepts)
    neighbours_by_concept = brain_nearest_neighbours_df.groupby(
        "concept", 
        sort = False, 
        observed = True
    )["neighbour"].apply(
        list
    ).to_dict()
    rows = []

    for concept in concepts:
        concept_neighbours = neighbours_by_concept.get(concept, [])

        if len(concept_neighbours) < number_of_neighbours:
            raise ValueError(
                f"Concept {concept} has only {len(concept_neighbours)} brain "
                f"neighbours, but {number_of_neighbours} were requested"
            )

        encoded_neighbours = []

        for neighbour in concept_neighbours[:number_of_neighbours]:
            if neighbour not in concept_to_index:
                raise ValueError(
                    f"Brain neighbour {neighbour} for concept {concept} is not present "
                    "in the relabelling concept set"
                )

            encoded_neighbours.append(concept_to_index[neighbour])

        rows.append(encoded_neighbours)

    return np.asarray(rows, dtype = np.int64)

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
    # brain neighbours must be positions in it, so the LLM top-k is recomputed on this subset
    concepts = brain_nearest_neighbours_df["concept"].unique()

    missing_embedding_concepts = sorted(set(concepts) - set(embedding_df.index))

    if missing_embedding_concepts:
        raise ValueError(
            f"The model's embeddings are missing {len(missing_embedding_concepts)} "
            "concept(s) required for relabelling, e.g. "
            f"{missing_embedding_concepts[:5]}"
        )

    max_k = max(numbers_of_neighbours)

    observed_llm_neighbours = compute_topk_on_concept_subset(
        embedding_df = embedding_df, 
        concepts = concepts, 
        number_of_neighbours = max_k, 
        similarity_type = similarity_type, 
    )

    brain_neighbours_at_max_k = encode_brain_nearest_neighbours(
        brain_nearest_neighbours_df = brain_nearest_neighbours_df, 
        concepts = concepts, 
        number_of_neighbours = max_k, 
    )

    # the brain side stays fixed and the LLM side is relabelled
    common_neighbours_matrices_by_k = compute_relabelled_common_neighbours_for_all_k(
        fixed_neighbours_at_max_k = brain_neighbours_at_max_k, 
        relabelled_neighbours_at_max_k = observed_llm_neighbours, 
        numbers_of_neighbours = numbers_of_neighbours, 
        number_of_relabellings = number_of_relabellings, 
        random_seed = random_seed, 
    )

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
    parser.add_argument("--embedding_dataframe", 
                        required = True)
    parser.add_argument("--isc_nearest_neighbours", 
                        required = True)
    parser.add_argument("--similarity_type", 
                        required = True)
    parser.add_argument("--relabelled_common_neighbours", 
                        required = True, 
                        help = "Single output holding every --number_of_neighbours' rows, distinguished by "
                               "a number_of_neighbours column; consumers read one k with "
                               "compute_relabelled_alignment.read_relabelled_alignment_scores()")
    parser.add_argument("--number_of_relabellings", 
                        type = int, 
                        required = True)
    parser.add_argument("--number_of_neighbours", 
                        type = int, 
                        nargs = "+", 
                        required = True)
    parser.add_argument("--random_seed", 
                        type = int, 
                        required = True)
    parser.add_argument("--model", 
                        type = str, 
                        required = True)
    args = parser.parse_args()

    if args.number_of_relabellings <= 0:
        raise ValueError("--number_of_relabellings must be a positive integer")

    if any(k <= 0 for k in args.number_of_neighbours):
        raise ValueError("--number_of_neighbours must all be positive integers")

    require_stored_number_of_neighbours(
        args.isc_nearest_neighbours, 
        max(args.number_of_neighbours)
    )
    brain_nearest_neighbours_df = read_parquet(args.isc_nearest_neighbours)

    embedding_df = read_parquet(args.embedding_dataframe)

    results_by_k = compute_relabelled_alignment_scores_for_all_k(
        embedding_df = embedding_df, 
        brain_nearest_neighbours_df = brain_nearest_neighbours_df, 
        number_of_relabellings = args.number_of_relabellings, 
        numbers_of_neighbours = args.number_of_neighbours, 
        random_seed = args.random_seed, 
        model = args.model, 
        similarity_type = args.similarity_type, 
    )

    write_relabelled_common_neighbours(
        results_by_k, 
        args.number_of_neighbours, 
        args.relabelled_common_neighbours
    )

if __name__ == "__main__":
    main()
