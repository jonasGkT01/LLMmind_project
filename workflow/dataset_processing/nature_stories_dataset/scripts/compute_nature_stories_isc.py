import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from libraries.fmri_processing import (
    compute_leave_one_out_isc,
)


def compute_isc(
    parcel_ts_files,
    n_rois,
    expected_subjects,
):
    if len(parcel_ts_files) != expected_subjects:
        raise ValueError(
            f"Expected {expected_subjects} subjects, "
            f"found {len(parcel_ts_files)}."
        )

    data_list = []

    for parcel_file in parcel_ts_files:

        parcel_file = Path(
            parcel_file
        )

        if not parcel_file.exists():
            raise FileNotFoundError(
                f"Missing parcel file: "
                f"{parcel_file}"
            )

        data = np.load(
            parcel_file
        )

        if data.ndim != 2:
            raise ValueError(
                f"{parcel_file} has shape "
                f"{data.shape}; expected "
                "time x parcels."
            )

        if data.shape[1] != n_rois:
            raise ValueError(
                f"{parcel_file} contains "
                f"{data.shape[1]} parcels; "
                f"expected {n_rois}."
            )

        data_list.append(
            data
        )

    time_lengths = [
        data.shape[0]
        for data in data_list
    ]

    if len(set(time_lengths)) != 1:
        raise ValueError(
            "Nature Stories has inconsistent "
            "time lengths across subjects: "
            f"{time_lengths}"
        )

    data = np.stack(
        data_list,
        axis=0,
    )

    # subjects x time x parcels
    return compute_leave_one_out_isc(
        data
    )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--manifest",
        required=True,
    )

    parser.add_argument(
        "--n_rois",
        type=int,
        required=True,
    )

    parser.add_argument(
        "--expected_subjects",
        type=int,
        required=True,
    )

    args = parser.parse_args()

    manifest = pd.read_csv(
        args.manifest,
        sep="\t",
    )

    required_columns = {
        "task",
        "subject",
        "parcel_ts",
        "isc_npy",
    }

    missing_columns = (
        required_columns
        - set(manifest.columns)
    )

    if missing_columns:
        raise ValueError(
            "Manifest is missing columns: "
            f"{sorted(missing_columns)}"
        )

    for task, task_df in manifest.groupby(
        "task",
        sort=False,
    ):

        subjects = (
            task_df["subject"]
            .tolist()
        )

        if len(subjects) != len(
            set(subjects)
        ):
            raise ValueError(
                f"Task {task} contains duplicate "
                "subjects."
            )

        parcel_ts_files = (
            task_df["parcel_ts"]
            .tolist()
        )

        isc_outputs = (
            task_df["isc_npy"]
            .unique()
        )

        if len(isc_outputs) != 1:
            raise ValueError(
                f"Task {task} has multiple ISC "
                f"outputs: {isc_outputs}"
            )

        print(
            f"Computing ISC for {task} "
            f"from {len(parcel_ts_files)} subjects"
        )

        isc_mean = compute_isc(
            parcel_ts_files=parcel_ts_files,
            n_rois=args.n_rois,
            expected_subjects=args.expected_subjects,
        )

        if isc_mean.shape != (
            args.n_rois,
        ):
            raise ValueError(
                f"Unexpected ISC shape for {task}: "
                f"{isc_mean.shape}"
            )

        output_path = Path(
            isc_outputs[0]
        )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        np.save(
            output_path,
            isc_mean.astype(
                np.float32
            ),
        )


if __name__ == "__main__":
    main()