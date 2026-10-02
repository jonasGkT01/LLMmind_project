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
    parser.add_argument("--n_rois", 
                        type = int, 
                        required = True)
    parser.add_argument("--expected_subjects", 
                        type = int, 
                        required = True)
    args = parser.parse_args()

    manifest = pd.read_csv(args.manifest, sep = "\t",)

    required_columns = {"task", "subject", "parcel_ts", "isc_npy",}

    missing_columns = required_columns - set(manifest.columns)

    if missing_columns:
        raise ValueError(f"Manifest is missing columns: {sorted(missing_columns)}")

    for task, task_df in manifest.groupby("task", sort = False,):
        subjects = task_df["subject"].tolist()

        if len(subjects) != len(set(subjects)):
            raise ValueError(f"Task {task} contains duplicate subjects.")

        if len(subjects) != args.expected_subjects:
            raise ValueError(
                f"Task {task}: expected {args.expected_subjects} subjects, "
                f"found {len(subjects)}"
            )

        print(f"Computing ISC for {task} from {len(subjects)} subjects")

        isc_mean = compute_isc_from_files(
            task_df["parcel_ts"].tolist(), 
            n_rois = args.n_rois, 
        )

        output_path = Path(single_value(task_df, "isc_npy", f"Task {task}"))
        output_path.parent.mkdir(parents = True, exist_ok = True,)
        np.save(output_path, isc_mean)

if __name__ == "__main__":
    main()
