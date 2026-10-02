# edited with AI assistance: Claude Code, Claude Opus 5.5 (claude-opus-5-5)
# last AI edit: 2026-10-02, see docs/changelog/developers/ for details
from pathlib import Path

import numpy as np
import pandas as pd

from libraries.compute_alignment import compute_common_neighbours
from libraries.compute_nearest_neighbours import (
    compute_blockwise_topk_from_embeddings, 
    create_neighbour_mask, 
    relabel_nearest_neighbours, 
)
from libraries.compute_similarity import (
    extract_embedding_matrix, 
    normalize_fn_for_similarity_type, 
)

def compute_topk_on_concept_subset(
    embedding_df, 
    concepts, 
    number_of_neighbours, 
    similarity_type, 
):
    # top-k is recomputed within `concepts`, not filtered from a larger file: the permutation needs
    # neighbour indices to be positions in this closed set
    embedding_matrix = extract_embedding_matrix(embedding_df.loc[concepts])

    neighbour_indices, _ = compute_blockwise_topk_from_embeddings(
        embedding_matrix = embedding_matrix, 
        number_of_neighbours = number_of_neighbours, 
        normalize_fn = normalize_fn_for_similarity_type(similarity_type), 
    )

    return neighbour_indices

def select_common_neighbour_dtype(number_of_neighbours):
    if number_of_neighbours <= np.iinfo(np.uint8).max:
        return np.uint8

    if number_of_neighbours <= np.iinfo(np.uint16).max:
        return np.uint16

    if number_of_neighbours <= np.iinfo(np.uint32).max:
        return np.uint32

    raise ValueError("The requested number of neighbours is too large to store")

def compute_relabelled_common_neighbours_for_all_k(
    fixed_neighbours_at_max_k, 
    relabelled_neighbours_at_max_k, 
    numbers_of_neighbours, 
    number_of_relabellings, 
    random_seed, 
):
    # both arrays hold, per concept, neighbour positions in the same closed concept set. Only the
    # second side is relabelled; one shared permutation per shuffle is reused across every k
    number_of_concepts = fixed_neighbours_at_max_k.shape[0]
    concept_indices = np.arange(number_of_concepts, dtype = np.int64)

    fixed_neighbour_masks_by_k = {}
    common_neighbours_matrices_by_k = {}

    for k in numbers_of_neighbours:
        mask, _ = create_neighbour_mask(fixed_neighbours_at_max_k[:, :k])
        fixed_neighbour_masks_by_k[k] = mask
        common_neighbours_matrices_by_k[k] = np.empty(
            (number_of_relabellings, number_of_concepts), 
            dtype = select_common_neighbour_dtype(k), 
        )

    inverse_permutation = np.empty(number_of_concepts, dtype = np.int64)

    # one stream for all shuffles, as in the Spearman null, so every test of a dataset draws the
    # same permutations and every model shares them
    rng = np.random.default_rng(random_seed)

    for shuffle_i in range(number_of_relabellings):
        permutation = rng.permutation(number_of_concepts)
        relabelled_neighbours = relabel_nearest_neighbours(
            observed_neighbours = relabelled_neighbours_at_max_k, 
            permutation = permutation, 
            inverse_permutation = inverse_permutation, 
            concept_indices = concept_indices, 
        )

        for k in numbers_of_neighbours:
            common_neighbours_matrices_by_k[k][shuffle_i] = compute_common_neighbours(
                neighbours = relabelled_neighbours[:, :k], 
                neighbour_mask = fixed_neighbour_masks_by_k[k], 
                concept_indices = concept_indices, 
            )

        if (
            shuffle_i == 0
            or (shuffle_i + 1) % 100 == 0
            or shuffle_i + 1 == number_of_relabellings
        ):
            print(f"completed relabelling {shuffle_i + 1}/{number_of_relabellings}")

    return common_neighbours_matrices_by_k

def create_relabelled_alignment_dataframe(
    common_neighbours_matrix, 
    concepts, 
    model, 
    number_of_neighbours, 
):
    # alignment_score is not stored: it is exactly common_neighbours / k (see read_relabelled_alignment_scores)
    number_of_relabellings, number_of_concepts = common_neighbours_matrix.shape
    number_of_rows = number_of_relabellings*number_of_concepts
    shuffle_codes = np.repeat(
        np.arange(number_of_relabellings, dtype = np.int32), 
        number_of_concepts
    )
    concept_codes = np.tile(
        np.arange(number_of_concepts, dtype = np.int32), 
        number_of_relabellings
    )

    result_df = pd.DataFrame(
        {
            "shuffle_id": pd.Categorical.from_codes(
                shuffle_codes, 
                categories = [
                    f"shuffle_{shuffle_i}"
                    for shuffle_i in range(number_of_relabellings)
                ], 
                ordered = True, 
            ), 
            "model": pd.Categorical.from_codes(
                np.zeros(number_of_rows, dtype = np.int8), 
                categories = [model], 
            ), 
            "concept": pd.Categorical.from_codes(
                concept_codes, 
                categories = concepts, 
                ordered = True, 
            ), 
            # needed to tell k's apart in the combined all-k file: Snakemake outputs can't depend on
            # wildcards, so separate per-k files from one job aren't possible
            "number_of_neighbours": np.full(
                number_of_rows, 
                number_of_neighbours, 
                dtype = np.int32
            ), 
            "common_neighbours": common_neighbours_matrix.reshape(-1), 
        }
    )

    return result_df

def write_relabelled_common_neighbours(
    results_by_k, 
    numbers_of_neighbours, 
    output_path, 
):
    # one all-k file; no index: the row position carries no information
    combined_df = pd.concat(
        [results_by_k[k] for k in numbers_of_neighbours], 
        ignore_index = True
    )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents = True, exist_ok = True)
    combined_df.to_parquet(
        output_path, 
        engine = "pyarrow", 
        compression = "snappy", 
        index = False
    )
