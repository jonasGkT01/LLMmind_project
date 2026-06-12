import argparse
from pathlib import Path

import pandas as pd

def compute_alignment_for_one_shuffle(
    relabelled_nearest_neighbours_df,
    brain_nearest_neighbours_df,
    number_of_neighbours,
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

    for concept in concepts:
        neighbours_relabelled = set(relabelled_dict[concept]["neighbour"])
        neighbours_brain = set(brain_dict[concept]["neighbour"])

        common_neighbours = len(neighbours_relabelled & neighbours_brain)

        rows.append(
            {
                "concept": concept,
                "common_neighbours": common_neighbours,
                "alignment_score": common_neighbours / number_of_neighbours,
                "alignment_score_percentage": (
                    common_neighbours / number_of_neighbours * 100
                ),
            }
        )

    return pd.DataFrame(rows)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--number_of_neighbours", type=int, required=True)
    parser.add_argument("--model", type=str, required=True)
    parser.add_argument("--relabelled_llm_nearest_neighbours", type=str, required=True)
    parser.add_argument("--isc_nearest_neighbours", type=str, required=True)
    parser.add_argument("--relabelled_alignment_score", type=str, required=True)
    args = parser.parse_args()

    relabelled_llm_nearest_neighbours_df = pd.read_parquet(
        args.relabelled_llm_nearest_neighbours,
        engine="pyarrow",
    )

    isc_nearest_neighbours_df = pd.read_parquet(
        args.isc_nearest_neighbours,
        engine="pyarrow",
    )

    if "shuffle_id" in relabelled_llm_nearest_neighbours_df.columns:
        grouped = relabelled_llm_nearest_neighbours_df.groupby("shuffle_id")
    elif "shuffle_id" in relabelled_llm_nearest_neighbours_df.index.names:
        grouped = relabelled_llm_nearest_neighbours_df.groupby(level="shuffle_id")
    else:
        raise ValueError(
            "Expected 'shuffle_id' either as a column or as an index level. "
            f"Columns are: {list(relabelled_llm_nearest_neighbours_df.columns)}. "
            f"Index levels are: {relabelled_llm_nearest_neighbours_df.index.names}."
        )

    all_alignment_scores = []

    for shuffle_id, shuffle_df in grouped:
        if "shuffle_id" in shuffle_df.index.names:
            shuffle_df = shuffle_df.reset_index(level="shuffle_id", drop=True)

        alignment_score_df = compute_alignment_for_one_shuffle(
            relabelled_nearest_neighbours_df=shuffle_df,
            brain_nearest_neighbours_df=isc_nearest_neighbours_df,
            number_of_neighbours=args.number_of_neighbours,
        )

        alignment_score_df["shuffle_id"] = shuffle_id
        alignment_score_df["model"] = args.model

        all_alignment_scores.append(alignment_score_df)

    big_alignment_score_df = pd.concat(all_alignment_scores, ignore_index=True)

    big_alignment_score_df = big_alignment_score_df[
        [
            "shuffle_id",
            "model",
            "concept",
            "common_neighbours",
            "alignment_score",
            "alignment_score_percentage",
        ]
    ]

    output_path = Path(args.relabelled_alignment_score)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    big_alignment_score_df.to_parquet(
        output_path,
        engine="pyarrow",
        index=False,
    )

if __name__ == "__main__":
    main()