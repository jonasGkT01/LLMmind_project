# edited with AI assistance: Claude Code, Claude Opus 5.5 (claude-opus-5-5)
# last AI edit: 2026-10-02, see docs/changelog/developers/ for details

import numpy as np
import pandas as pd

from libraries.path_metadata import parse_alignment_path

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

def read_alignment_scores(path, dataset, similarity_type, number_of_neighbours):
    # one observed LLM-brain or LLM-LLM alignment-score file, checked against the expected
    # configuration, and the hypergeometric expectation k/(n - 1) shared by all its concepts
    metadata = parse_alignment_path(path)
    expected_metadata = {
        "kind": "score", 
        "dataset": dataset, 
        "similarity_type": similarity_type, 
        "number_of_neighbours": number_of_neighbours,
    }

    for key, value in expected_metadata.items():
        if metadata[key] != value:
            raise ValueError(
                f"{path} has {key}={metadata[key]}, expected {value}"
            )

    # load and validate the scores
    df = pd.read_parquet(
        path, 
        engine = "pyarrow", 
        columns = ["concept", "alignment_score"],
    )
    df["concept"] = df["concept"].astype(str)
    duplicated_concepts = df.loc[df["concept"].duplicated(), "concept"].tolist()

    if duplicated_concepts:
        raise ValueError(
            f"{path} contains duplicated concepts: {duplicated_concepts[:10]}"
        )

    scores = pd.to_numeric(df["alignment_score"], errors = "coerce")

    if (scores.isna() | (scores < 0) | (scores > 1)).any():
        raise ValueError(
            f"{path} contains alignment scores that are not numbers in [0, 1]"
        )

    df["alignment_score"] = scores.astype(float)
    population_size = len(df) - 1

    if not 0 < number_of_neighbours <= population_size:
        raise ValueError(
            f"{path} uses {number_of_neighbours} neighbours, "
            f"but has only {len(df)} concepts"
        )

    return df, metadata, number_of_neighbours/population_size

def common_hypergeometric_expectation(expectations):
    # the hypergeometric expectation shared by a set of alignment-score files
    expectations = set(expectations)

    if len(expectations) != 1:
        raise ValueError(
            "The alignment-score files do not share one hypergeometric expectation: "
            f"{sorted(expectations)}"
        )

    return expectations.pop()
