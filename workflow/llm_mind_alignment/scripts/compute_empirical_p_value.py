#!/usr/bin/env python3
import argparse

import numpy as np
import pandas as pd

def compute_empirical_statistics(
    observed_df: pd.DataFrame,
    relabelled_df: pd.DataFrame,
) -> pd.DataFrame:
    output_rows = []

    for concept, observed_alignment_score in observed_df.set_index("concept")["alignment_score"].items():
        concept_null_scores = relabelled_df[relabelled_df["concept"] == concept]["alignment_score"].to_numpy(dtype=float)

        number_of_relabellings = relabelled_df["shuffle_id"].nunique()

        empirical_null_mean = concept_null_scores.mean()

        number_of_exceedances = np.sum(
                concept_null_scores
                >= observed_alignment_score
            )

        empirical_p_value = (number_of_exceedances + 1)/(number_of_relabellings + 1)

        output_rows.append(
            {
                "concept": concept,
                "observed_common_neighbours": observed_df[observed_df["concept"] == concept]["common_neighbours"].values[0],
                "observed_alignment_score": observed_alignment_score,
                "empirical_null_mean_alignment_score": empirical_null_mean,
                "number_of_relabellings": number_of_relabellings,
                "number_of_null_scores_at_least_as_large": number_of_exceedances,
                "empirical_upper_tail_p_value": empirical_p_value,
            }
        )

    return pd.DataFrame(output_rows)

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Compute an upper-tail empirical p-value separately for "
            "each concept using observed and relabelled alignment-score "
            "Parquet files."
        )
    )
    parser.add_argument(
        "--observed_alignment_scores",
        required=True,
        help=(
            "Path to the Parquet file containing the observed "
            "alignment scores"
        ),
    )
    parser.add_argument(
        "--relabelled_alignment_scores",
        required=True,
        help=(
            "Path to the Parquet file containing the alignment scores "
            "for all relabellings"
        ),
    )

    args = parser.parse_args()

    observed_df = pd.read_parquet(args.observed_alignment_scores, engine="pyarrow")

    relabelled_df = pd.read_parquet(args.relabelled_alignment_scores, engine="pyarrow")

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