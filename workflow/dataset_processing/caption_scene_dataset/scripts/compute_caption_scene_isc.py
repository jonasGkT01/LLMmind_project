# edited with AI assistance: Claude Code, Claude Opus 5.5 (claude-opus-5-5)
# last AI edit: 2026-10-01, see docs/changelog/developers/ for details

import argparse
from pathlib import Path

import numpy as np

import nibabel as nib
from nilearn import datasets, image

from libraries.fmri_processing import compute_isc_from_files

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

    print(f"Computing ISC {args.isc_npy} from {len(args.parcel_ts)} parcel files")

    isc_mean = compute_isc_from_files(args.parcel_ts, n_rois = args.n_rois)

    save_isc(
        isc_mean=isc_mean,
        isc_npy=args.isc_npy,
        isc_nii=args.isc_nii,
        atlas_data=atlas_data,
        atlas_img=atlas_img,
    )

if __name__ == "__main__":
    main()