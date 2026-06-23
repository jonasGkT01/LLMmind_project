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

    concepts = sorted(set(relabelled_nearest_neighbours_df["concept"]) & set(brain_nearest_neighbours_df["concept"]))

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
                "alignment_score_percentage": common_neighbours / number_of_neighbours * 100,
            }
        )

    return pd.DataFrame(
        rows,
        columns=[
            "concept",
            "common_neighbours",
            "alignment_score",
            "alignment_score_percentage",
        ],
    )

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--number_of_neighbours", type=int, required=True)
    parser.add_argument("--model", type=str, required=True)
    parser.add_argument("--relabelled_llm_nearest_neighbours", type=str, required=True)
    parser.add_argument("--isc_nearest_neighbours", type=str, required=True)
    parser.add_argument("--relabelled_alignment_score", type=str, required=True)
    args = parser.parse_args()

    if args.number_of_neighbours <= 0:
        raise ValueError(
            "--number_of_neighbours must be a positive integer"
        )

    relabelled_llm_nearest_neighbours_df = pd.read_parquet(args.relabelled_llm_nearest_neighbours, engine="pyarrow")
    isc_nearest_neighbours_df = pd.read_parquet(args.isc_nearest_neighbours, engine="pyarrow")

    required_columns = {"concept", "neighbour"}

    missing_relabelled_columns = (
        required_columns
        - set(relabelled_llm_nearest_neighbours_df.columns)
    )
    missing_isc_columns = (
        required_columns
        - set(isc_nearest_neighbours_df.columns)
    )

    if missing_relabelled_columns:
        raise ValueError(
            f"The relabelled nearest-neighbours dataframe is missing columns: {sorted(missing_relabelled_columns)}"
        )

    if missing_isc_columns:
        raise ValueError(
            f"The ISC nearest-neighbours dataframe is missing columns: {sorted(missing_isc_columns)}"
        )

    if "shuffle_id" in relabelled_llm_nearest_neighbours_df.columns:
        grouped = relabelled_llm_nearest_neighbours_df.groupby("shuffle_id")
    elif "shuffle_id" in relabelled_llm_nearest_neighbours_df.index.names:
        grouped = relabelled_llm_nearest_neighbours_df.groupby(level="shuffle_id")
    else:
        raise ValueError(
            f"Expected 'shuffle_id' either as a column or as an index level. {sorted(missing_isc_columns)}"
        )

    if "shuffle_id" in relabelled_llm_nearest_neighbours_df.columns:
        grouped = relabelled_llm_nearest_neighbours_df.groupby("shuffle_id")
    elif "shuffle_id" in relabelled_llm_nearest_neighbours_df.index.names:
        grouped = relabelled_llm_nearest_neighbours_df.groupby(level="shuffle_id")
    else:
        raise ValueError(
            f"Expected 'shuffle_id' either as a column or as an index level. Columns are: {list(relabelled_llm_nearest_neighbours_df.columns)}. Index levels are: {relabelled_llm_nearest_neighbours_df.index.names}"
        )

    output_columns = [
        "shuffle_id",
        "model",
        "concept",
        "common_neighbours",
        "alignment_score",
        "alignment_score_percentage",
    ]

    all_alignment_scores = []

    for shuffle_id, shuffle_df in grouped:
        if "shuffle_id" in shuffle_df.columns:
            shuffle_df = shuffle_df.drop(columns="shuffle_id")

        if "shuffle_id" in shuffle_df.index.names:
            shuffle_df = shuffle_df.reset_index(level="shuffle_id", drop=True)

        alignment_score_df = compute_alignment_for_one_shuffle(
            relabelled_nearest_neighbours_df=shuffle_df,
            brain_nearest_neighbours_df=isc_nearest_neighbours_df,
            number_of_neighbours=args.number_of_neighbours,
        )

        alignment_score_df["shuffle_id"] = shuffle_id
        alignment_score_df["model"] = args.model

        alignment_score_df = alignment_score_df[
            output_columns
        ]

        all_alignment_scores.append(alignment_score_df)

    if all_alignment_scores:
        big_alignment_score_df = pd.concat(
            all_alignment_scores,
            ignore_index=True,
        )
    else:
        big_alignment_score_df = pd.DataFrame(
            columns=output_columns,
        )

    output_path = Path(args.relabelled_alignment_score)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    big_alignment_score_df.to_parquet(output_path, engine="pyarrow", index=True)

if __name__ == "__main__":
    main()