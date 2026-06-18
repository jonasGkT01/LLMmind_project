#!/usr/bin/env python3
import argparse

import pandas as pd
from scipy.stats import hypergeom

def compute_hypergeometric_statistics(
    observed_df: pd.DataFrame,
    number_of_neighbours: int,
) -> pd.DataFrame:
    number_of_concepts = len(observed_df)
    population_size = number_of_concepts - 1

    output_df = observed_df[
        [
            "concept",
            "common_neighbours",
            "alignment_score",
        ]
    ].copy()

    output_df["hypergeometric_upper_tail_p_value"] = hypergeom.sf(
        output_df["common_neighbours"] - 1,
        population_size,
        number_of_neighbours,
        number_of_neighbours,
    )

    return output_df

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Compute an upper-tail hypergeometric p-value separately "
            "for each concept from an observed alignment-score Parquet file."
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
        "--number_of_neighbours",
        type=int,
        required=True,
        help="Number of nearest neighbours used to compute alignment",
    )

    args = parser.parse_args()

    observed_df = pd.read_parquet(
        args.observed_alignment_scores,
        engine="pyarrow",
    )

    summary_df = compute_hypergeometric_statistics(
        observed_df=observed_df,
        number_of_neighbours=args.number_of_neighbours,
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