import argparse
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
from nilearn import datasets, image

from libraries.fmri_processing import compute_leave_one_out_isc

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
            f"ISC requires at least two parcel time-series files, got {len(parcel_ts_files)}"
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
            f"Mismatched time lengths across parcel time-series files. Details: {details}"
        )

    data = np.stack(
        data_list,
        axis=0,
    ).astype(np.float32)
    
    return compute_leave_one_out_isc(data)

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
    parser.add_argument("--parcel_ts", nargs="+", required=True)
    parser.add_argument("--isc_npy", required=True)
    parser.add_argument("--isc_nii", required=True)
    parser.add_argument("--n_rois", type=int, required=True)
    parser.add_argument("--yeo_networks", type=int, required=True)
    parser.add_argument("--atlas_dir", type=str, required=True)
    args = parser.parse_args()

    atlas = datasets.fetch_atlas_schaefer_2018(
        n_rois=args.n_rois,
        data_dir=args.atlas_dir,
        yeo_networks=args.yeo_networks,
    )

    atlas_img = image.load_img(atlas.maps)
    atlas_data = atlas_img.get_fdata().astype(int)

#    print(f"Computing ISC from {len(args.parcel_ts)} parcel files")

    isc_mean = compute_isc(args.parcel_ts, args.n_rois)

    save_isc(
        isc_mean=isc_mean,
        isc_npy=args.isc_npy,
        isc_nii=args.isc_nii,
        atlas_data=atlas_data,
        atlas_img=atlas_img,
    )

if __name__ == "__main__":
    main()