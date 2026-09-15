#!/usr/bin/env python3

import argparse
from pathlib import Path

import pandas as pd

def read_model_level_score(path):
    model_level_df = pd.read_csv(path, sep="\t")

    required_columns = {
        "dataset",
        "model",
        "stimuli_type",
        "similarity_type",
        "number_of_concepts",
        "number_of_pairs",
        "observed_spearman_coefficient",
        "empirical_null_mean_spearman_coefficient",
        "number_of_relabellings",
        "number_of_null_scores_at_least_as_large",
        "empirical_upper_tail_p_value",
    }

    missing_columns = required_columns - set(model_level_df.columns)

    if missing_columns:
        raise ValueError(f"Model-level Spearman file {path} is missing columns: {sorted(missing_columns)}")

    if len(model_level_df) != 1:
        raise ValueError(f"Expected exactly one row in model-level Spearman file {path}, but found {len(model_level_df)}")

    return model_level_df

def reshape_summary(summary_df):
    metadata_columns = ["dataset", "stimuli_type", "similarity_type", "model",]

    duplicated_results = summary_df[summary_df.duplicated(subset=metadata_columns, keep=False,)]

    if not duplicated_results.empty:
        duplicated_keys = duplicated_results[metadata_columns].drop_duplicates().to_dict(orient="records")
        raise ValueError(f"Duplicate model-level Spearman results were found: {duplicated_keys[:10]}")

    statistic_columns = [
        column
        for column in summary_df.columns
        if column not in metadata_columns
    ]

    for column in statistic_columns:
        summary_df[column] = pd.to_numeric(summary_df[column], errors="raise")

    summary_long_df = summary_df.melt(
        id_vars=metadata_columns,
        value_vars=statistic_columns,
        var_name="statistic",
        value_name="value",
    )

    statistic_order = {
        statistic: index
        for index, statistic in enumerate(statistic_columns)
    }

    summary_long_df["_statistic_order"] = summary_long_df["statistic"].map(statistic_order)

    summary_long_df = summary_long_df.sort_values(
        [
            "dataset",
            "stimuli_type",
            "similarity_type",
            "model",
            "_statistic_order",
        ]
    ).drop(columns="_statistic_order").reset_index(drop=True)

    summary_long_df = summary_long_df[
        [
            "dataset",
            "stimuli_type",
            "similarity_type",
            "model",
            "statistic",
            "value",
        ]
    ]

    return summary_long_df

def main():
    parser = argparse.ArgumentParser(description="Aggregate all model-level Spearman alignment TSV files into one long summary TSV")
    parser.add_argument("--model_level_scores",
                        nargs="+",
                        required=True,
                        help="Model-level Spearman alignment TSV files",)
    parser.add_argument("--all_spearman_alignment_scores_tsv",
                        required=True,
                        help="Output long model-level Spearman summary TSV",)
    args = parser.parse_args()

    model_level_dfs = [
        read_model_level_score(path)
        for path in args.model_level_scores
    ]

    if not model_level_dfs:
        raise ValueError("No model-level Spearman results were available for aggregation")

    summary_df = pd.concat(model_level_dfs, ignore_index=True,)

    summary_long_df = reshape_summary(summary_df)

    output_path = Path(args.all_spearman_alignment_scores_tsv)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    summary_long_df.to_csv(
        output_path,
        sep="\t",
        index=False,
        float_format="%.10g",
    )

if __name__ == "__main__":
    main()