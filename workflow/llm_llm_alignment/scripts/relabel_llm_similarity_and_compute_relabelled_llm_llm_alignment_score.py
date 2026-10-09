# edited with AI assistance: Claude Code, Claude Opus 5.5 (claude-opus-5-5)
# last AI edit: 2026-10-09, see docs/changelog/developers/ for details
import argparse

from libraries.compute_relabelled_alignment import (
    compute_relabelled_common_neighbours_for_all_k, 
    compute_topk_on_concept_subset, 
    create_relabelled_alignment_dataframe, 
    write_relabelled_common_neighbours, 
)
from libraries.parquet_io import read_parquet

def select_shared_concepts(embedding_df_1, embedding_df_2):
    # the first model's concept order fixes the positions every permutation works on
    concepts_2 = set(embedding_df_2.index)
    shared_concepts = [
        concept
        for concept in embedding_df_1.index
        if concept in concepts_2
    ]

    if len(shared_concepts) == 0:
        raise ValueError(
            "No shared concepts were found between the two embedding dataframes"
        )

    return shared_concepts

def compute_relabelled_alignment_scores_for_all_k(
    embedding_df_1, 
    embedding_df_2, 
    number_of_relabellings, 
    numbers_of_neighbours, 
    random_seed, 
    model, 
    similarity_type, 
):
    # both top-k's are recomputed on the shared concepts, the closed set every permutation works on.
    # Model 1 stays fixed and model 2 is relabelled, as the brain stays fixed in the LLM-brain case
    concepts = select_shared_concepts(embedding_df_1, embedding_df_2)
    max_k = max(numbers_of_neighbours)

    neighbours_1 = compute_topk_on_concept_subset(
        embedding_df = embedding_df_1, 
        concepts = concepts, 
        number_of_neighbours = max_k, 
        similarity_type = similarity_type, 
    )
    neighbours_2 = compute_topk_on_concept_subset(
        embedding_df = embedding_df_2, 
        concepts = concepts, 
        number_of_neighbours = max_k, 
        similarity_type = similarity_type, 
    )

    common_neighbours_matrices_by_k = compute_relabelled_common_neighbours_for_all_k(
        fixed_neighbours_at_max_k = neighbours_1, 
        relabelled_neighbours_at_max_k = neighbours_2, 
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
    parser.add_argument("--embedding_dataframe_1", 
                        required = True)
    parser.add_argument("--embedding_dataframe_2", 
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
                        required = True, 
                        help = "The relabelled (second) model, stored in the output's model column")
    args = parser.parse_args()

    if args.number_of_relabellings <= 0:
        raise ValueError("--number_of_relabellings must be a positive integer")

    if any(k <= 0 for k in args.number_of_neighbours):
        raise ValueError("--number_of_neighbours must all be positive integers")

    embedding_df_1 = read_parquet(args.embedding_dataframe_1)
    embedding_df_2 = read_parquet(args.embedding_dataframe_2)

    results_by_k = compute_relabelled_alignment_scores_for_all_k(
        embedding_df_1 = embedding_df_1, 
        embedding_df_2 = embedding_df_2, 
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
