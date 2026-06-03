import numpy as np
import pandas as pd
import argparse
from pathlib import Path


def compute_alignment_for_one_shuffle(
    relabelled_nearest_neighbours_df,
    brain_nearest_neighbours_df,
    number_of_neighbours
):
    relabelled_dict = {
        concept: group.drop(columns="concept").reset_index(drop=True)
        for concept, group in relabelled_nearest_neighbours_df.groupby("concept")
    }

    brain_dict = {
        concept: group.drop(columns="concept").reset_index(drop=True)
        for concept, group in brain_nearest_neighbours_df.groupby("concept")
    }

    concepts = sorted(
        set(relabelled_nearest_neighbours_df["concept"])
        & set(brain_nearest_neighbours_df["concept"])
    )

    rows = []

    for c in concepts:
        neighbours_relabelled = set(relabelled_dict[c]["neighbour"])
        neighbours_brain = set(brain_dict[c]["neighbour"])

        common_neighbours = len(neighbours_relabelled & neighbours_brain)

        rows.append({
            "concept": c,
            "common_neighbours": common_neighbours,
            "alignment_score": common_neighbours / number_of_neighbours,
            "alignment_score_percentage": common_neighbours / number_of_neighbours * 100
        })

    alignment_score_df = pd.DataFrame(rows).set_index("concept")
    alignment_score_df.index.name = "concept"

    return alignment_score_df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--number_of_neighbours",
        type=int,
        required=True,
        help="Set the number of neighbours to compute")
    parser.add_argument(
        "--model",
        type=str,
        required=True,
        help="Model for which the alignment score is computed")
    parser.add_argument(
        "--relabelled_llm_nearest_neighbours",
        type=str,
        required=True,
        help="Path to the big dataframe containing all relabelled nearest neighbours")
    parser.add_argument(
        "--isc_nearest_neighbours",
        type=str,
        required=True,
        help="Path to dataframe of computed nearest neighbours for the brain")
    parser.add_argument(
        "--relabelled_alignment_score",
        type=str,
        required=True,
        help="Path to the output big dataframe containing all relabelled alignment scores"
    )
    args = parser.parse_args()

    relabelled_llm_nearest_neighbours_df = pd.read_parquet(args.relabelled_llm_nearest_neighbours, engine="pyarrow")

    isc_nearest_neighbours_df = pd.read_parquet(args.isc_nearest_neighbours, engine="pyarrow")

    all_alignment_scores = {}

    for shuffle_id, shuffle_df in relabelled_llm_nearest_neighbours_df.groupby(level="shuffle_id"):
        shuffle_df = shuffle_df.reset_index(level="shuffle_id", drop=True)

        alignment_score_df = compute_alignment_for_one_shuffle(
            relabelled_nearest_neighbours_df=shuffle_df,
            brain_nearest_neighbours_df=isc_nearest_neighbours_df,
            number_of_neighbours=args.number_of_neighbours
        )

        all_alignment_scores[shuffle_id] = alignment_score_df

    big_alignment_score_df = pd.concat(
        all_alignment_scores,
        names=["shuffle_id", "concept"]
    )

    output_path = Path(args.relabelled_alignment_score)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    big_alignment_score_df.to_parquet(
        output_path,
        engine="pyarrow",
        index=True
    )

if __name__ == "__main__":
    main()