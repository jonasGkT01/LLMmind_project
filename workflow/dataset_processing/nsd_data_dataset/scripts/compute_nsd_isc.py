import argparse

from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
from nilearn import datasets, image

from libraries.fmri_processing import compute_leave_one_out_isc

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--number_of_regions", type=int, required=True)
    parser.add_argument("--number_of_yeo_networks", type=int, required=True)
    parser.add_argument("--atlas_dir", required=True)
    arguments = parser.parse_args()

    isc_manifest = pd.read_csv(arguments.manifest, sep="\t")

    required_columns = {
        "stimulus_id",
        "subject",
        "parcel_time_series",
        "isc_numpy_file",
        "isc_nifti_file",
    }

    missing_columns = required_columns - set(isc_manifest.columns)

    if missing_columns:
        raise ValueError(f"ISC manifest is missing columns: {sorted(missing_columns)}")

    if isc_manifest.empty:
        raise ValueError(f"ISC manifest is empty: {arguments.manifest}")

    atlas = datasets.fetch_atlas_schaefer_2018(
        n_rois=arguments.number_of_regions,
        data_dir=arguments.atlas_dir,
        yeo_networks=arguments.number_of_yeo_networks,
    )

    atlas_image = image.load_img(atlas.maps)
    atlas_labels = atlas_image.get_fdata().astype(np.int32)

    for stimulus_identifier, stimulus_manifest in isc_manifest.groupby("stimulus_id", sort=False):
        # A stimulus can be presented to a subject more than once: each presentation is
        # an independent fMRI observation, so repeated subjects are expected here and
        # all of their observations contribute to the ISC average.
        parcel_time_series_files = [
            Path(path)
            for path in stimulus_manifest["parcel_time_series"].tolist()
        ]

        if len(parcel_time_series_files) < 2:
            raise ValueError(f"ISC requires at least two usable fMRI observations for stimulus {stimulus_identifier}, got {len(parcel_time_series_files)}")

        parcel_time_series_arrays = []

        for parcel_time_series_file in parcel_time_series_files:
            if not parcel_time_series_file.exists():
                raise FileNotFoundError(f"Missing parcel time-series file: {parcel_time_series_file}")

            parcel_time_series = np.load(parcel_time_series_file)

            if parcel_time_series.ndim != 2:
                raise ValueError(f"Expected a 2D parcel time series, got shape {parcel_time_series.shape}: {parcel_time_series_file}")

            if parcel_time_series.shape[1] != arguments.number_of_regions:
                raise ValueError(f"Expected {arguments.number_of_regions} regions, got {parcel_time_series.shape[1]}: {parcel_time_series_file}")

            parcel_time_series_arrays.append(parcel_time_series)

        time_series_lengths = [
            parcel_time_series.shape[0]
            for parcel_time_series in parcel_time_series_arrays
        ]

        if len(set(time_series_lengths)) != 1:
            length_details = ", ".join(
                f"{parcel_time_series_file}: {parcel_time_series.shape[0]} timepoints"
                for parcel_time_series_file, parcel_time_series in zip(
                    parcel_time_series_files,
                    parcel_time_series_arrays,
                )
            )

            raise ValueError(f"Mismatched NSD parcel time-series lengths for stimulus {stimulus_identifier}: {length_details}")

        stacked_parcel_time_series = np.stack(parcel_time_series_arrays, axis=0).astype(np.float32)
        mean_isc_values = compute_leave_one_out_isc(stacked_parcel_time_series)

        isc_numpy_files = stimulus_manifest["isc_numpy_file"].astype(str).unique()
        isc_nifti_files = stimulus_manifest["isc_nifti_file"].astype(str).unique()

        if len(isc_numpy_files) != 1:
            raise ValueError(f"Stimulus {stimulus_identifier} has multiple ISC NumPy output files: {isc_numpy_files}")

        if len(isc_nifti_files) != 1:
            raise ValueError(f"Stimulus {stimulus_identifier} has multiple ISC NIfTI output files: {isc_nifti_files}")

        isc_numpy_file = Path(isc_numpy_files[0])
        isc_nifti_file = Path(isc_nifti_files[0])

        isc_numpy_file.parent.mkdir(parents=True, exist_ok=True)
        isc_nifti_file.parent.mkdir(parents=True, exist_ok=True)

        np.save(isc_numpy_file, mean_isc_values)

        isc_volume = np.zeros_like(atlas_labels, dtype=np.float32)

        for parcel_index, isc_value in enumerate(mean_isc_values):
            atlas_label = parcel_index + 1
            isc_volume[atlas_labels == atlas_label] = isc_value

        isc_nifti_image = nib.Nifti1Image(
            isc_volume,
            atlas_image.affine,
            header=atlas_image.header.copy(),
        )

        isc_nifti_image.header.set_data_dtype(np.float32)
        nib.save(isc_nifti_image, isc_nifti_file)

        print(f"Computed ISC for {stimulus_identifier} from {len(parcel_time_series_arrays)} observations and {time_series_lengths[0]} timepoints")

if __name__ == "__main__":
    main()