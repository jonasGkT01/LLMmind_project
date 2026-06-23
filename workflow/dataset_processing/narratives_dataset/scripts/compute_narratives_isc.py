import argparse
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
from nilearn import datasets, image
from scipy.stats import pearsonr

def safe_pearsonr(x, y):
    if np.allclose(x, x[0]) or np.allclose(y, y[0]):
        return 0.0

    r, _ = pearsonr(x, y)
    return float(np.nan_to_num(r, nan=0.0, posinf=0.0, neginf=0.0))

def compute_isc(parcel_ts_files):
    data_list = [np.load(f) for f in parcel_ts_files]

    time_lengths = [x.shape[0] for x in data_list]
    if len(set(time_lengths)) != 1:
        minimum_time = min(time_lengths)
        data_list = [x[:minimum_time, :] for x in data_list]

    n_subjects = len(data_list)
    n_parcels = data_list[0].shape[1]

    if n_subjects < 2:
        raise ValueError("ISC requires at least two parcel time-series files")

    data = np.stack(data_list, axis=0)

    isc = np.zeros((n_subjects, n_parcels), dtype=np.float32)

    for s in range(n_subjects):
        others_mean = data[np.arange(n_subjects) != s].mean(axis=0)

        for p in range(n_parcels):
            isc[s, p] = safe_pearsonr(data[s, :, p], others_mean[:, p])

    return isc.mean(axis=0).astype(np.float32)

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
        parcel_ts_files = task_df["parcel_ts"].tolist()
        isc_npy_values = task_df["isc_npy"].unique()
        isc_nii_values = task_df["isc_nii"].unique()

        if len(isc_npy_values) != 1:
            raise ValueError(f"Task {task} has multiple isc_npy outputs: {isc_npy_values}")

        if len(isc_nii_values) != 1:
            raise ValueError(f"Task {task} has multiple isc_nii outputs: {isc_nii_values}")

#        print(f"Computing ISC for task {task} from {len(parcel_ts_files)} files")

        isc_mean = compute_isc(parcel_ts_files)

        save_isc_outputs(
            isc_mean=isc_mean,
            isc_npy=isc_npy_values[0],
            isc_nii=isc_nii_values[0],
            atlas_data=atlas_data,
            atlas_img=atlas_img,
        )

if __name__ == "__main__":
    main()