# edited with AI assistance: Claude Code, Claude Opus 5.5 (claude-opus-5-5)
# last AI edit: 2026-10-01, see docs/changelog/developers/ for details

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

import nibabel as nib
from nilearn import datasets, image

from libraries.fmri_processing import compute_isc_from_files, single_value

def save_isc_outputs(isc_mean, isc_npy, isc_nii, atlas_data, atlas_img):
    isc_npy = Path(isc_npy)
    isc_nii = Path(isc_nii)

    isc_npy.parent.mkdir(parents=True, exist_ok=True)
    isc_nii.parent.mkdir(parents=True, exist_ok=True)

    np.save(isc_npy, isc_mean)

    out_data = np.zeros_like(atlas_data, dtype=np.float32)

    for parcel_idx in range(len(isc_mean)):
        label_value = parcel_idx + 1
        out_data[atlas_data == label_value] = isc_mean[parcel_idx]

    out_img = nib.Nifti1Image(
        out_data,
        affine=atlas_img.affine,
        header=atlas_img.header,
    )

    nib.save(out_img, isc_nii)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--n_rois", type=int, required=True)
    parser.add_argument("--yeo_networks", type=int, required=True)
    parser.add_argument("--atlas_dir", type=str, required=True)
    args = parser.parse_args()

    manifest = pd.read_csv(args.manifest, sep="\t")

    required_columns = {"task", "parcel_ts", "isc_npy", "isc_nii"}
    missing_columns = required_columns - set(manifest.columns)

    if missing_columns:
        raise ValueError(f"Manifest is missing columns: {sorted(missing_columns)}")

    atlas = datasets.fetch_atlas_schaefer_2018(
        n_rois=args.n_rois,
        data_dir=args.atlas_dir,
        yeo_networks=args.yeo_networks,
    )

    atlas_img = image.load_img(atlas.maps)
    atlas_data = atlas_img.get_fdata().astype(int)

    for task, task_df in manifest.groupby("task", sort=False):
        isc_mean = compute_isc_from_files(
            task_df["parcel_ts"].tolist(),
            n_rois = args.n_rois,
            truncate_to_shortest = True,
        )

        save_isc_outputs(
            isc_mean = isc_mean,
            isc_npy = single_value(task_df, "isc_npy", f"Task {task}"),
            isc_nii = single_value(task_df, "isc_nii", f"Task {task}"),
            atlas_data = atlas_data,
            atlas_img = atlas_img,
        )

if __name__ == "__main__":
    main()