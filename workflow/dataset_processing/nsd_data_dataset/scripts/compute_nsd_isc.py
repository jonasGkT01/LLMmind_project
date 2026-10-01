# edited with AI assistance: Claude Code, Claude Opus 5.5 (claude-opus-5-5)
# last AI edit: 2026-10-01, see docs/changelog/developers/ for details

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

import nibabel as nib
from nilearn import datasets, image

from libraries.fmri_processing import compute_isc_from_files, single_value

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
        # Each presentation is an independent observation: a subject may appear more
        # than once, and every presentation enters the ISC average.
        mean_isc_values = compute_isc_from_files(
            stimulus_manifest["parcel_time_series"].tolist(),
            n_rois = arguments.number_of_regions,
        )

        group = f"Stimulus {stimulus_identifier}"
        isc_numpy_file = Path(single_value(stimulus_manifest, "isc_numpy_file", group))
        isc_nifti_file = Path(single_value(stimulus_manifest, "isc_nifti_file", group))

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

        print(
            f"Computed ISC for {stimulus_identifier} "
            f"from {len(stimulus_manifest)} observations"
        )

if __name__ == "__main__":
    main()