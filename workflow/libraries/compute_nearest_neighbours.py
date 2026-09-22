import json

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

DEFAULT_COLUMN_BLOCK_SIZE = 4096

def stream_nearest_neighbours_from_parquet(
    similarity_parquet_path,
    number_of_neighbours,
    column_block_size = DEFAULT_COLUMN_BLOCK_SIZE,
):
    """
        Compute top-k nearest neighbours for a symmetric similarity matrix stored as Parquet, without ever
        loading the full N x N matrix into memory.

        Rows and columns share the same concept order (guaranteed by the script that produced the Parquet
        file), so by symmetry a column-projected read of a block of concepts already contains everything
        needed to rank those concepts' neighbours against every other concept. At N~66k this keeps peak
        memory around column_block_size/N of the full matrix instead of several full copies of it, which is
        what previously caused an out-of-memory kill on nsd_data (N=66,216, a 43.8 GB Parquet file).
    """
    parquet_file = pq.ParquetFile(similarity_parquet_path)
    pandas_metadata = json.loads(parquet_file.schema_arrow.metadata[b"pandas"])
    index_column = pandas_metadata["index_columns"][0]
    concepts = [name for name in parquet_file.schema_arrow.names if name != index_column]
    number_of_concepts = len(concepts)

    if parquet_file.metadata.num_rows != number_of_concepts:
        raise ValueError(
            f"{similarity_parquet_path} is not square: {number_of_concepts} concept columns but "
            f"{parquet_file.metadata.num_rows} rows"
        )

    row_labels = pq.read_table(similarity_parquet_path, columns=[index_column],).column(index_column).to_pylist()

    if row_labels != concepts:
        raise ValueError(f"{similarity_parquet_path} rows and columns are not in the same order")

    if number_of_concepts - 1 < number_of_neighbours:
        raise ValueError(f"Requested {number_of_neighbours} neighbours, but only {number_of_concepts - 1} candidates are available")

    concepts_array = np.array(concepts)
    neighbour_indices = np.empty((number_of_concepts, number_of_neighbours), dtype=np.int64)
    neighbour_scores = np.empty((number_of_concepts, number_of_neighbours), dtype=np.float64)

    for block_start in range(0, number_of_concepts, column_block_size):
        block_concepts = concepts[block_start:block_start + column_block_size]
        block_width = len(block_concepts)

        table = pq.read_table(similarity_parquet_path, columns=[index_column, *block_concepts],)
        block_df = table.to_pandas(ignore_metadata=True,).set_index(index_column)
        block = block_df.loc[concepts, block_concepts].to_numpy(dtype=np.float64, copy=True)

        block_rows = np.arange(block_start, block_start + block_width,)
        block[block_rows, np.arange(block_width),] = -np.inf

        idx_part = np.argpartition(block, -number_of_neighbours, axis=0,)[-number_of_neighbours:]
        scores_part = np.take_along_axis(block, idx_part, axis=0,)
        order = np.argsort(-scores_part, axis=0,)
        idx_topk = np.take_along_axis(idx_part, order, axis=0,)
        scores_topk = np.take_along_axis(scores_part, order, axis=0,)

        neighbour_indices[block_start:block_start + block_width, :] = idx_topk.T
        neighbour_scores[block_start:block_start + block_width, :] = scores_topk.T

    return pd.DataFrame(
        {
            "concept": np.repeat(concepts_array, number_of_neighbours,),
            "neighbour": concepts_array[neighbour_indices.reshape(-1)],
            "similarity": neighbour_scores.reshape(-1),
        }
    )

def compute_topk_indices(similarity, number_of_neighbours,):
    if similarity.shape[1] - 1 < number_of_neighbours:
        raise ValueError(f"Requested {number_of_neighbours} neighbours, but only {similarity.shape[1] - 1} candidates are available")

    similarity = similarity.copy()
    np.fill_diagonal(similarity, -np.inf)

    idx_part = np.argpartition(similarity, -number_of_neighbours, axis = 1,)[:, -number_of_neighbours:]
    scores_part = np.take_along_axis(similarity, idx_part, axis = 1,)
    order = np.argsort(scores_part, axis = 1,)[:, ::-1]
    idx_topk = np.take_along_axis(idx_part, order, axis = 1,)

    return idx_topk.astype(np.int64)

def create_nearest_neighbours_dataframe(similarity_df, number_of_neighbours,):
    similarity = similarity_df.to_numpy(copy=True)

    idx_topk = compute_topk_indices(similarity = similarity, number_of_neighbours=number_of_neighbours,)
    scores_topk = np.take_along_axis(similarity, idx_topk, axis = 1,)

    concepts = similarity_df.index.to_numpy()
    neighbours = similarity_df.columns.to_numpy()

    return pd.DataFrame(
        {
            "concept": np.repeat(concepts, number_of_neighbours,),
            "neighbour": neighbours[idx_topk.reshape(-1)],
            "similarity": scores_topk.reshape(-1),
        }
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