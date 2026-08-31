#!/usr/bin/env python3
import argparse

import numpy as np
import pandas as pd

from libraries.compute_statistics import empirical_upper_tail_p_value

def compute_empirical_statistics(observed_df: pd.DataFrame, relabelled_df: pd.DataFrame) -> pd.DataFrame:
    number_of_relabellings = relabelled_df["shuffle_id"].nunique()

    observed_by_concept = observed_df.set_index("concept")

    relabelled_summary_df = (
        relabelled_df
        .merge(
            observed_by_concept[["alignment_score"]],
            left_on="concept",
            right_index=True,
            suffixes=("", "_observed"),
        )
        .assign(
            exceeds_observed=lambda df: df["alignment_score"] >= df["alignment_score_observed"]
        )
        .groupby("concept", sort=False)
        .agg(
            empirical_null_mean_alignment_score=("alignment_score", "mean"),
            number_of_null_scores_at_least_as_large=("exceeds_observed", "sum"),
        )
    )

    summary_df = observed_by_concept.join(relabelled_summary_df)

    summary_df["number_of_relabellings"] = number_of_relabellings
    summary_df["empirical_upper_tail_p_value"] = (
        empirical_upper_tail_p_value(
            number_at_least_as_large = summary_df["number_of_null_scores_at_least_as_large"],
            number_of_relabellings = number_of_relabellings,
        )
    )

    summary_df = summary_df.reset_index()

    summary_df = summary_df.rename(
        columns={
            "common_neighbours": "observed_common_neighbours",
            "alignment_score": "observed_alignment_score",
        }
    )

    return summary_df[
        [
            "concept",
            "observed_common_neighbours",
            "observed_alignment_score",
            "empirical_null_mean_alignment_score",
            "number_of_relabellings",
            "number_of_null_scores_at_least_as_large",
            "empirical_upper_tail_p_value",
        ]
    ]

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute an upper-tail empirical p-value separately for each concept using observed and relabelled alignment-score Parquet files"
    )
    parser.add_argument(
        "--observed_alignment_score",
        required=True,
        help="Path to the Parquet file containing the observed alignment scores",)
    parser.add_argument(
        "--relabelled_alignment_score",
        required=True,
        help="Path to the Parquet file containing the alignment scores for all relabellings",)
    args = parser.parse_args()

    observed_df = pd.read_parquet(args.observed_alignment_score, engine="pyarrow")
    relabelled_df = pd.read_parquet(args.relabelled_alignment_score, engine="pyarrow")

    summary_df = compute_empirical_statistics(
        observed_df=observed_df,
        relabelled_df=relabelled_df,
    )

    print(
        summary_df.to_csv(
            sep="\t",
            index=False,
            float_format="%.6f",
        ),
        end="",
    )

if __name__ == "__main__":
    main()