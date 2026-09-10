import argparse

import pandas as pd

from libraries.compute_statistics import empirical_upper_tail_p_value

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--observed_alignment", required=True)
    parser.add_argument("--relabelled_alignment", required=True)
    args = parser.parse_args()

    observed_df = pd.read_parquet(args.observed_alignment, engine="pyarrow")
    relabelled_df = pd.read_parquet(args.relabelled_alignment, engine="pyarrow")
    required_observed_columns = {
        "concept",
        "spearman_coefficient",
    }
    required_relabelled_columns = {
        "shuffle_id",
        "concept",
        "spearman_coefficient",
    }

    if not required_observed_columns.issubset(observed_df.columns):
        raise ValueError("Observed alignment dataframe is missing required columns")

    if not required_relabelled_columns.issubset(relabelled_df.columns):
        raise ValueError("Relabelled alignment dataframe is missing required columns")

    if observed_df["concept"].duplicated().any():
        raise ValueError("Observed alignment dataframe contains duplicated concepts")

    observed_concepts = set(observed_df["concept"])
    relabelled_concepts = set(relabelled_df["concept"])

    if observed_concepts != relabelled_concepts:
        raise ValueError("Observed and relabelled alignment dataframes contain different concepts")

    number_of_relabellings = relabelled_df["shuffle_id"].nunique()
    counts_by_concept = relabelled_df.groupby("concept", observed=False,).size()

    if (counts_by_concept != number_of_relabellings).any():
        raise ValueError("Each concept must have exactly one coefficient per relabelling")

    observed_by_concept = observed_df.set_index("concept")
    relabelled_summary_df = (
        relabelled_df
        .merge(
            observed_by_concept[["spearman_coefficient"]],
            left_on="concept",
            right_index=True,
            suffixes=("", "_observed"),
        )
        .assign(
            exceeds_observed=lambda df: (df["spearman_coefficient"] >= df["spearman_coefficient_observed"])
        )
        .groupby("concept", sort=False, observed=False)
        .agg(
            empirical_null_mean_spearman_coefficient=("spearman_coefficient", "mean"),
            number_of_null_scores_at_least_as_large=("exceeds_observed", "sum"),
        )
    )

    summary_df = observed_by_concept.join(relabelled_summary_df)
    summary_df["number_of_relabellings"] = number_of_relabellings
    summary_df["empirical_upper_tail_p_value"] = empirical_upper_tail_p_value(
        number_at_least_as_large=summary_df["number_of_null_scores_at_least_as_large"],
        number_of_relabellings=number_of_relabellings,
    )
    summary_df = summary_df.reset_index().rename(
        columns={"spearman_coefficient": "observed_spearman_coefficient",}
    )

    print(
        summary_df[
            [
                "concept",
                "observed_spearman_coefficient",
                "empirical_null_mean_spearman_coefficient",
                "number_of_relabellings",
                "number_of_null_scores_at_least_as_large",
                "empirical_upper_tail_p_value",
            ]
        ].to_csv(
            sep="\t",
            index=False,
            float_format="%.6f",
        ),
        end="",
    )

if __name__ == "__main__":
    main()