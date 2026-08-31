import numpy as np
import pandas as pd

def compute_topk_indices(
    similarity,
    number_of_neighbours,
):
    if similarity.shape[1] - 1 < number_of_neighbours:
        raise ValueError(
            f"Requested {number_of_neighbours} neighbours, but only {similarity.shape[1] - 1} candidates are available"
        )

    similarity = similarity.copy()
    np.fill_diagonal(similarity, -np.inf)

    idx_part = np.argpartition(similarity, -number_of_neighbours, axis = 1,)[:, -number_of_neighbours:]
    scores_part = np.take_along_axis(similarity, idx_part, axis = 1,)
    order = np.argsort(scores_part, axis = 1,)[:, ::-1]
    idx_topk = np.take_along_axis(idx_part, order, axis = 1,)

    return idx_topk.astype(np.int64)


def create_nearest_neighbours_dataframe(
    similarity_df,
    number_of_neighbours,
):
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