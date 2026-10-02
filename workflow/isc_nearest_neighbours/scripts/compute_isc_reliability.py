# written with AI assistance: Claude Code, Claude Opus 5.5 (claude-opus-5-5)
# last AI edit: 2026-10-02, see docs/changelog/developers/ for details
import argparse

import numpy as np
import pandas as pd

from libraries.compute_isc import compute_split_half_isc_reliability, load_isc_inputs

def main():
    parser = argparse.ArgumentParser(description = "Split-half reliability of every stimulus's 200-parcel ISC vector")
    parser.add_argument("--manifest", 
                        required = True, 
                        help = "The dataset's ISC manifest: one row per parcel file")
    parser.add_argument("--stimulus_column", 
                        required = True)
    parser.add_argument("--parcel_column", 
                        required = True)
    parser.add_argument("--truncate_to_shortest", 
                        action = "store_true", 
                        help = "Truncate a stimulus's files to the shortest one, as its ISC does")
    parser.add_argument("--n_rois", 
                        type = int, 
                        required = True)
    parser.add_argument("--number_of_splits", 
                        type = int, 
                        required = True)
    parser.add_argument("--random_seed", 
                        type = int, 
                        required = True)
    parser.add_argument("--output", 
                        required = True)
    args = parser.parse_args()

    # load the manifest
    manifest = pd.read_csv(args.manifest, sep = "\t", dtype = {"subject": str})
    required_columns = {args.stimulus_column, args.parcel_column, "subject"}
    missing_columns = required_columns - set(manifest.columns)

    if missing_columns:
        raise ValueError(
            f"{args.manifest} is missing columns: {sorted(missing_columns)}"
        )

    # one random stream for all stimuli, in sorted order, so the splits are reproducible
    rng = np.random.default_rng(args.random_seed)
    rows = []

    for stimulus, stimulus_df in manifest.groupby(args.stimulus_column, sort = True):
        data = load_isc_inputs(
            stimulus_df[args.parcel_column].tolist(), 
            args.n_rois, 
            subjects = stimulus_df["subject"].tolist(), 
            truncate_to_shortest = args.truncate_to_shortest, 
        )
        split_half_r = compute_split_half_isc_reliability(
            data, 
            args.number_of_splits, 
            rng
        )
        rows.append(
            {
                "stimulus": stimulus, 
                "number_of_subjects": data.shape[0], 
                "number_of_time_points": data.shape[1], 
                "split_half_r": split_half_r, 
                "spearman_brown_r": 2*split_half_r/(1 + split_half_r), 
            }
        )

    # save one row per stimulus
    pd.DataFrame(rows).to_csv(
        args.output, 
        sep = "\t", 
        index = False, 
        float_format = "%.6g"
    )

if __name__ == "__main__":
    main()
