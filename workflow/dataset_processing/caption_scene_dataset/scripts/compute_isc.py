import argparse
from pathlib import Path

import nibabel as nib
import numpy as np
from nilearn import datasets, image
from scipy.stats import pearsonr

def safe_pearsonr(x, y):
    if np.allclose(x, x[0]) or np.allclose(y, y[0]):
        return 0.0

    r, _ = pearsonr(x, y)

    return float(np.nan_to_num(r, nan=0.0, posinf=0.0, neginf=0.0))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--parcel_ts", nargs="+", required=True)
    parser.add_argument("--isc_npy", required=True)
    parser.add_argument("--isc_nii", required=True)
    parser.add_argument("--n_rois", type=int, required=True)
    parser.add_argument("--yeo_networks", type=int, required=True)
    parser.add_argument("--atlas_dir", type=str, required=True)
    args = parser.parse_args()

    isc_npy = Path(args.isc_npy)
    isc_nii = Path(args.isc_nii)

    isc_npy.parent.mkdir(parents=True, exist_ok=True)
    isc_nii.parent.mkdir(parents=True, exist_ok=True)

    parcel_ts_files = args.parcel_ts

    if len(parcel_ts_files) < 2:
        raise ValueError(
            f"ISC requires at least two parcel time-series files, "
            f"got {len(parcel_ts_files)}."
        )

    atlas = datasets.fetch_atlas_schaefer_2018(
        n_rois=args.n_rois,
        data_dir=args.atlas_dir,
        yeo_networks=args.yeo_networks,
    )

    atlas_img = image.load_img(atlas.maps)
    atlas_data = atlas_img.get_fdata().astype(int)

    data_list = [np.load(f) for f in parcel_ts_files]

    for path, arr in zip(parcel_ts_files, data_list):
        if arr.ndim != 2:
            raise ValueError(
                f"Expected 2D parcel time series, got shape {arr.shape}: {path}"
            )

        if arr.shape[1] != args.n_rois:
            raise ValueError(
                f"Expected {args.n_rois} parcels, got {arr.shape[1]} parcels: {path}"
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

    isc_mean = isc.mean(axis=0).astype(np.float32)

    np.save(isc_npy, isc_mean)

    out_data = np.zeros_like(atlas_data, dtype=np.float32)

    for parcel_idx in range(n_parcels):
        label_value = parcel_idx + 1
        out_data[atlas_data == label_value] = isc_mean[parcel_idx]

    out_img = nib.Nifti1Image(
        out_data,
        affine=atlas_img.affine,
        header=atlas_img.header.copy(),
    )

    out_img.header.set_data_dtype(np.float32)

    nib.save(out_img, isc_nii)

if __name__ == "__main__":
    main()