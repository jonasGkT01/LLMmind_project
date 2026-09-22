from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

DEFAULT_COLUMN_BLOCK_SIZE = 4096
NEAREST_NEIGHBOURS_COUNT_METADATA_KEY = b"llmmind.number_of_neighbours"

def compute_blockwise_topk_from_embeddings(
    embedding_matrix,
    number_of_neighbours,
    normalize_fn,
    row_block_size = DEFAULT_COLUMN_BLOCK_SIZE,
):
    """
        Compute top-k nearest-neighbour indices and scores for every row of `embedding_matrix` against
        every other row, without ever materializing the full N x N similarity matrix: normalize once
        (cheap, O(N x D)), then for each row-block multiply the block against the full normalized matrix
        (block_size x N, the same per-block memory footprint already used by the *_from_parquet readers
        above) and immediately reduce that block to its top-k, discarding it. This is what lets the
        similarity-computing scripts skip writing the dense matrix to disk at all.
    """
    number_of_concepts = embedding_matrix.shape[0]

    if number_of_concepts - 1 < number_of_neighbours:
        raise ValueError(f"Requested {number_of_neighbours} neighbours, but only {number_of_concepts - 1} candidates are available")

    normalized = normalize_fn(embedding_matrix)

    neighbour_indices = np.empty((number_of_concepts, number_of_neighbours), dtype=np.int64)
    neighbour_scores = np.empty((number_of_concepts, number_of_neighbours), dtype=np.float64)

    for block_start in range(0, number_of_concepts, row_block_size):
        block_end = min(block_start + row_block_size, number_of_concepts)
        block = normalized[block_start:block_end] @ normalized.T

        block_rows = np.arange(block_end - block_start)
        block[block_rows, np.arange(block_start, block_end)] = -np.inf

        idx_part = np.argpartition(block, -number_of_neighbours, axis=1,)[:, -number_of_neighbours:]
        scores_part = np.take_along_axis(block, idx_part, axis=1,)
        order = np.argsort(-scores_part, axis=1,)
        idx_topk = np.take_along_axis(idx_part, order, axis=1,)
        scores_topk = np.take_along_axis(scores_part, order, axis=1,)

        neighbour_indices[block_start:block_end, :] = idx_topk
        neighbour_scores[block_start:block_end, :] = scores_topk

    return neighbour_indices, neighbour_scores

def write_nearest_neighbours_parquet(
    concepts,
    neighbour_indices,
    neighbour_scores,
    number_of_neighbours,
    output_path,
):
    """
        Write a compact nearest-neighbours table: `concept`/`neighbour` are dictionary-encoded (via
        pandas Categorical, sharing one `concepts` category list) instead of the plain repeated strings
        the old per-k files used, and the realized `number_of_neighbours` is stored as file-level
        metadata so a consumer that later needs k neighbours can assert this file actually has at least
        that many before trusting a slice of it (see `require_stored_number_of_neighbours`) — this file
        is unversioned by k in its name, so that safeguard is what protects against silently reading a
        stale, too-small file after a dataset's configured max-k grows.
    """
    concepts_array = np.asarray(concepts)
    category_dtype = pd.CategoricalDtype(categories=concepts_array, ordered=False)
    number_of_concepts = len(concepts_array)

    result_df = pd.DataFrame(
        {
            "concept": pd.Categorical.from_codes(
                np.repeat(np.arange(number_of_concepts), number_of_neighbours),
                dtype=category_dtype,
            ),
            "neighbour": pd.Categorical.from_codes(
                neighbour_indices.reshape(-1),
                dtype=category_dtype,
            ),
            "similarity": neighbour_scores.reshape(-1).astype(np.float32),
        }
    )

    table = pa.Table.from_pandas(result_df, preserve_index=False)
    existing_metadata = table.schema.metadata or {}
    table = table.replace_schema_metadata(
        {**existing_metadata, NEAREST_NEIGHBOURS_COUNT_METADATA_KEY: str(number_of_neighbours).encode()}
    )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, output_path)

def read_stored_number_of_neighbours(path):
    """Read the neighbour count written by `write_nearest_neighbours_parquet`, raising if it's absent."""
    parquet_file = pq.ParquetFile(path)
    metadata = parquet_file.schema_arrow.metadata or {}

    if NEAREST_NEIGHBOURS_COUNT_METADATA_KEY not in metadata:
        raise ValueError(
            f"{path} is missing the '{NEAREST_NEIGHBOURS_COUNT_METADATA_KEY.decode()}' metadata key; "
            f"it may predate the max-k neighbours format and should be regenerated"
        )

    return int(metadata[NEAREST_NEIGHBOURS_COUNT_METADATA_KEY])

def require_stored_number_of_neighbours(path, requested_number_of_neighbours):
    """Fail loudly if a stored max-k neighbours file doesn't actually contain the k a caller needs."""
    stored_number_of_neighbours = read_stored_number_of_neighbours(path)

    if stored_number_of_neighbours < requested_number_of_neighbours:
        raise ValueError(
            f"{path} was generated with only {stored_number_of_neighbours} neighbours per concept, but "
            f"{requested_number_of_neighbours} were requested. Regenerate it with a larger "
            f"--number_of_neighbours (e.g. bump the dataset's configured neighbourhood sizes)."
        )

    return stored_number_of_neighbours

def slice_top_k_neighbours(neighbours_df, number_of_neighbours):
    """Take each concept's first `number_of_neighbours` rows from an already rank-ordered neighbours table."""
    return (
        neighbours_df
        .groupby("concept", sort=False, observed=True)
        .head(number_of_neighbours)
    )

def create_neighbour_mask(neighbours):
    number_of_concepts = neighbours.shape[0]
    concept_indices = np.arange(number_of_concepts, dtype=np.int64,)

    neighbour_mask = np.zeros((number_of_concepts, number_of_concepts), dtype = bool,)

    neighbour_mask[concept_indices[:, None], neighbours,] = True

    return neighbour_mask, concept_indices

def relabel_nearest_neighbours(
    observed_neighbours,
    permutation,
    inverse_permutation,
    concept_indices,
):
    inverse_permutation[permutation] = concept_indices

    return inverse_permutation[observed_neighbours[permutation]]