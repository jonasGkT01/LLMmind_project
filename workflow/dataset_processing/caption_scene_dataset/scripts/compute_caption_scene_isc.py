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

def parcel_output_path(row, parcel_root):
    return (
        Path(parcel_root)
        / f"task-{row.stimulus_id}"
        / (
            f"sub-{row.subject}_ses-{row.session}_run-{row.run}_"
            f"task-{row.stimulus_id}_event-{row.event_index}_parcel_ts.npy"
        )
    )

def compute_isc(parcel_ts_files, n_rois):
    if len(parcel_ts_files) < 2:
        raise ValueError(
            f"ISC requires at least two parcel time-series files, "
            f"got {len(parcel_ts_files)}."
        )

    data_list = [np.load(f) for f in parcel_ts_files]

    for path, arr in zip(parcel_ts_files, data_list):
        if arr.ndim != 2:
            raise ValueError(
                f"Expected 2D parcel time series, got shape {arr.shape}: {path}"
            )

        if arr.shape[1] != n_rois:
            raise ValueError(
                f"Expected {n_rois} parcels, got {arr.shape[1]} parcels: {path}"
            )

    time_lengths = [x.shape[0] for x in data_list]

    if len(set(time_lengths)) != 1:
        details = ", ".join(
            f"{path}: {arr.shape[0]} timepoints"
            for path, arr in zip(parcel_ts_files, data_list)
        )

        raise ValueError(
            "Mismatched time lengths across parcel time-series files. "
            f"Details: {details}"
        )

    n_subjects = len(data_list)
    n_parcels = data_list[0].shape[1]

    data = np.stack(data_list, axis=0).astype(np.float32)

    isc = np.zeros((n_subjects, n_parcels), dtype=np.float32)

    for subject_idx in range(n_subjects):
        other_subjects = np.arange(n_subjects) != subject_idx
        others_mean = data[other_subjects].mean(axis=0)

        for parcel_idx in range(n_parcels):
            isc[subject_idx, parcel_idx] = safe_pearsonr(
                data[subject_idx, :, parcel_idx],
                others_mean[:, parcel_idx],
            )

    return isc.mean(axis=0).astype(np.float32)

def save_isc(isc_mean, isc_npy, isc_nii, atlas_data, atlas_img):
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
        header=atlas_img.header.copy(),
    )

    out_img.header.set_data_dtype(np.float32)

    nib.save(out_img, isc_nii)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--parcel_root", required=True)
    parser.add_argument("--isc_npy_root", required=True)
    parser.add_argument("--isc_nii_root", required=True)
    parser.add_argument("--n_rois", type=int, required=True)
    parser.add_argument("--yeo_networks", type=int, required=True)
    parser.add_argument("--atlas_dir", type=str, required=True)
    args = parser.parse_args()

    manifest = pd.read_csv(args.manifest, sep="\t")

    required_columns = {
        "subject",
        "session",
        "run",
        "event_index",
        "stimulus_id",
    }

    missing_columns = required_columns - set(manifest.columns)

    if missing_columns:
        raise ValueError(f"Manifest is missing columns: {sorted(missing_columns)}")

    for column in required_columns:
        manifest[column] = manifest[column].astype(str)

    atlas = datasets.fetch_atlas_schaefer_2018(
        n_rois=args.n_rois,
        data_dir=args.atlas_dir,
        yeo_networks=args.yeo_networks,
    )

    atlas_img = image.load_img(atlas.maps)
    atlas_data = atlas_img.get_fdata().astype(int)

    for stimulus_id, rows in manifest.groupby("stimulus_id", sort=True):
        parcel_ts_files = [
            parcel_output_path(row, args.parcel_root)
            for row in rows.itertuples(index=False)
        ]

        missing_files = [str(f) for f in parcel_ts_files if not f.exists()]

        if missing_files:
            raise FileNotFoundError(
                f"Missing parcel time-series files for stimulus_id={stimulus_id}: "
                + ", ".join(missing_files)
            )

        isc_npy = Path(args.isc_npy_root) / f"task-{stimulus_id}_isc_mean.npy"
        isc_nii = Path(args.isc_nii_root) / f"task-{stimulus_id}_isc_mean.nii.gz"

        print(f"Computing ISC for stimulus_id={stimulus_id} from {len(parcel_ts_files)} files")

        isc_mean = compute_isc(parcel_ts_files, args.n_rois)

        save_isc(
            isc_mean=isc_mean,
            isc_npy=isc_npy,
            isc_nii=isc_nii,
            atlas_data=atlas_data,
            atlas_img=atlas_img,
        )

if __name__ == "__main__":
    main()