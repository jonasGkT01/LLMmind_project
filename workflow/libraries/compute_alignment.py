# edited with AI assistance: Claude Code, Claude Opus 5.5 (claude-opus-5-5)
# last AI edit: 2026-10-02, see docs/changelog/developers/ for details

import numpy as np
import pandas as pd

def nearest_neighbours_to_dict(nearest_neighbours_df):
    return {
        concept: set(group["neighbour"])
        for concept, group in nearest_neighbours_df.groupby("concept")
    }

def compute_alignment_scores(
    nearest_neighbours_df_1,
    nearest_neighbours_df_2,
    number_of_neighbours,
):
    nearest_neighbours_dict_1 = nearest_neighbours_to_dict(nearest_neighbours_df_1)
    nearest_neighbours_dict_2 = nearest_neighbours_to_dict(nearest_neighbours_df_2)

    if set(nearest_neighbours_dict_1) != set(nearest_neighbours_dict_2):
        raise ValueError("The two representations have different concepts, and therefore cannot be compared.")

    rows = []

    # iterate in sorted order, so the rows are written in the same order on every run
    for concept in sorted(nearest_neighbours_dict_1):
        neighbours_1 = nearest_neighbours_dict_1[concept]
        neighbours_2 = nearest_neighbours_dict_2[concept]

        common_neighbours = len(neighbours_1 & neighbours_2)

        rows.append(
            {
                "concept": concept,
                "common_neighbours": common_neighbours,
                "alignment_score": common_neighbours/number_of_neighbours,
            }
        )

    return pd.DataFrame(
        rows, 
        columns = ["concept", "common_neighbours", "alignment_score",],
    )

def compute_common_neighbours(neighbours, neighbour_mask, concept_indices,):
    return neighbour_mask[concept_indices[:, None], neighbours,].sum(axis=1)

def compute_mean_alignment_score(
    neighbour_mask,
    neighbours,
    concept_indices,
    number_of_neighbours,
):
    if neighbour_mask.shape[0] != neighbours.shape[0]:
        raise ValueError("The two nearest-neighbour representations have different numbers of concepts")

    common_neighbours = compute_common_neighbours(neighbours = neighbours, neighbour_mask = neighbour_mask, concept_indices = concept_indices,)

    alignment_scores = common_neighbours/number_of_neighbours

    return float(alignment_scores.mean())

def read_relabelled_alignment_scores(path, number_of_neighbours):
    # one k's rows of an all-k relabelled file, with alignment_score = common_neighbours / k
    relabelled_df = pd.read_parquet(
        path,
        engine="pyarrow",
        columns=["shuffle_id", "concept", "common_neighbours"],
        filters=[("number_of_neighbours", "==", number_of_neighbours)],
    )

    if relabelled_df.empty:
        raise ValueError(f"{path} has no rows for number_of_neighbours={number_of_neighbours}")

    relabelled_df["alignment_score"] = relabelled_df["common_neighbours"].to_numpy(dtype=np.float64)/number_of_neighbours

    return relabelled_df
