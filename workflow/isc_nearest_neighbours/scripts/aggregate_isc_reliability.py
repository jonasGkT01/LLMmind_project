# written with AI assistance: Claude Code, Claude Opus 5.5 (claude-opus-5-5)
# last AI edit: 2026-10-02, see docs/changelog/developers/ for details
import argparse

import numpy as np
import pandas as pd

# an ISC value at least this large in absolute value is treated as near ±1
NEAR_ONE_ISC = 0.9

def main():
    parser = argparse.ArgumentParser(description = "Summarise the ISC reliability and the ISC values of every dataset in one table")
    parser.add_argument("--datasets", 
                        nargs = "+", 
                        required = True)
    parser.add_argument("--reliability_tsvs", 
                        nargs = "+", 
                        required = True, 
                        help = "One isc_reliability.tsv per dataset, in --datasets order")
    parser.add_argument("--isc_dataframes", 
                        nargs = "+", 
                        required = True, 
                        help = "One isc_dataframe.parquet per dataset, in --datasets order")
    parser.add_argument("--output", 
                        required = True)
    args = parser.parse_args()

    if not len(args.datasets) == len(args.reliability_tsvs) == len(args.isc_dataframes):
        raise ValueError("Give one reliability TSV and one ISC dataframe per dataset")

    # one row per dataset: the reliability of its ISC vectors and the distribution of its ISC values
    rows = []

    for dataset, reliability_tsv, isc_dataframe in zip(
        args.datasets, 
        args.reliability_tsvs, 
        args.isc_dataframes, 
    ):
        reliability = pd.read_csv(reliability_tsv, sep = "\t")
        with_value = reliability.dropna(subset = ["split_half_r"])
        isc_values = np.abs(
            np.concatenate(pd.read_parquet(isc_dataframe)["isc"].to_numpy())
        )
        row = {
            "dataset": dataset, 
            "number_of_stimuli": len(reliability), 
            "number_of_stimuli_with_value": len(with_value), 
            "median_number_of_time_points": (
                reliability["number_of_time_points"].median()
            ), 
        }

        for column in ["split_half_r", "spearman_brown_r"]:
            row[f"median_{column}"] = with_value[column].median()
            row[f"q25_{column}"] = with_value[column].quantile(0.25)
            row[f"q75_{column}"] = with_value[column].quantile(0.75)

        row["median_absolute_isc"] = np.median(isc_values)
        row[f"fraction_absolute_isc_at_least_{NEAR_ONE_ISC}"] = np.mean(
            isc_values >= NEAR_ONE_ISC
        )
        rows.append(row)

    pd.DataFrame(rows).to_csv(
        args.output, 
        sep = "\t", 
        index = False, 
        float_format = "%.6g"
    )

if __name__ == "__main__":
    main()
