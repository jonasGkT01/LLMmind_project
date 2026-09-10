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

    if len(observed_df) != 1:
        raise ValueError(f"Expected one observed Spearman coefficient, got {len(observed_df)}")

    required_observed_columns = {
        "number_of_concepts",
        "number_of_pairs",
        "spearman_coefficient",
    }
    required_relabelled_columns = {
        "shuffle_id",
        "spearman_coefficient",
    }

    if not required_observed_columns.issubset(observed_df.columns):
        raise ValueError("Observed alignment dataframe is missing required columns")

    if not required_relabelled_columns.issubset(relabelled_df.columns):
        raise ValueError("Relabelled alignment dataframe is missing required columns")

    number_of_relabellings = relabelled_df["shuffle_id"].nunique()

    if number_of_relabellings != len(relabelled_df):
        raise ValueError("Expected exactly one relabelled coefficient per shuffle")

    observed_coefficient = float(observed_df["spearman_coefficient"].iloc[0])
    number_at_least_as_large = int((relabelled_df["spearman_coefficient"] >= observed_coefficient).sum())
    
    empirical_p_value = empirical_upper_tail_p_value(
        number_at_least_as_large=number_at_least_as_large,
        number_of_relabellings=number_of_relabellings,
    )

    result_df = pd.DataFrame(
        {
            "number_of_concepts": [int(observed_df["number_of_concepts"].iloc[0])],
            "number_of_pairs": [int(observed_df["number_of_pairs"].iloc[0])],
            "observed_spearman_coefficient": [observed_coefficient],
            "empirical_null_mean_spearman_coefficient": [relabelled_df["spearman_coefficient"].mean()],
            "number_of_relabellings": [number_of_relabellings],
            "number_of_null_scores_at_least_as_large": [number_at_least_as_large],
            "empirical_upper_tail_p_value": [empirical_p_value],
        }
    )

    print(
        result_df.to_csv(
            sep="\t",
            index=False,
            float_format="%.6f",
        ),
        end="",
    )

if __name__ == "__main__":
    main()