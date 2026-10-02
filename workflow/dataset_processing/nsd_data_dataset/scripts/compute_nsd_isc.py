# edited with AI assistance: Claude Code, Claude Opus 5.5 (claude-opus-5-5)
# last AI edit: 2026-10-02, see docs/changelog/developers/ for details

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from libraries.fmri_processing import compute_isc_from_files, single_value

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", 
                        required = True)
    parser.add_argument("--number_of_regions", 
                        type = int, 
                        required = True)
    arguments = parser.parse_args()

    isc_manifest = pd.read_csv(arguments.manifest, sep = "\t")

    required_columns = {
        "stimulus_id", 
        "subject", 
        "parcel_time_series", 
        "isc_numpy_file", 
    }

    missing_columns = required_columns - set(isc_manifest.columns)

    if missing_columns:
        raise ValueError(f"ISC manifest is missing columns: {sorted(missing_columns)}")

    if isc_manifest.empty:
        raise ValueError(f"ISC manifest is empty: {arguments.manifest}")

    for stimulus_identifier, stimulus_manifest in isc_manifest.groupby(
        "stimulus_id", 
        sort = False
    ):
        # each presentation is an independent observation: a subject may appear more
        # than once, and every presentation enters the ISC average
        mean_isc_values = compute_isc_from_files(
            stimulus_manifest["parcel_time_series"].tolist(), 
            n_rois = arguments.number_of_regions, 
        )

        group = f"Stimulus {stimulus_identifier}"
        isc_numpy_file = Path(single_value(stimulus_manifest, "isc_numpy_file", group))

        isc_numpy_file.parent.mkdir(parents = True, exist_ok = True)
        np.save(isc_numpy_file, mean_isc_values)

        print(
            f"Computed ISC for {stimulus_identifier} "
            f"from {len(stimulus_manifest)} observations"
        )

if __name__ == "__main__":
    main()
