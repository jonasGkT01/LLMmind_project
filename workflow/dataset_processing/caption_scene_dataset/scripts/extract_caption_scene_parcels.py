import argparse
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
from nilearn import datasets, image
from scipy import sparse

def parcel_output_path(row, output_root):
    return (
        Path(output_root)
        / "parcels"
        / f"task-{row.stimulus_id}"
        / (
            f"sub-{row.subject}_ses-{row.session}_run-{row.run}_"
            f"task-{row.stimulus_id}_event-{row.event_index}_parcel_ts.npy"
        )
    )

def build_parcel_matrix(labels_3d, n_rois):
    labels = labels_3d.reshape(-1).astype(np.int32)
    valid = (labels > 0) & (labels <= n_rois)

    voxel_idx = np.where(valid)[0]
    parcel_idx = labels[valid] - 1

    counts = np.bincount(parcel_idx, minlength=n_rois).astype(np.float32)

    if np.any(counts == 0):
        missing = np.where(counts == 0)[0] + 1
        raise ValueError(f"Atlas has empty parcels after resampling: {missing.tolist()}")

    weights = 1.0 / counts[parcel_idx]

    return sparse.csr_matrix(
        (weights, (parcel_idx, voxel_idx)),
        shape=(n_rois, labels.size),
        dtype=np.float32,
    )

def bold_grid_key(img):
    return (
        img.shape[:3],
        tuple(np.round(img.affine.ravel(), 6)),
    )

def get_resampled_parcel_matrix(img, atlas_img, n_rois, cache):
    key = bold_grid_key(img)

    if key not in cache:
        resampled_atlas_img = image.resample_to_img(
            atlas_img,
            img,
            interpolation="nearest",
            force_resample=True,
            copy_header=True,
        )

        labels = resampled_atlas_img.get_fdata().astype(np.int32)
        cache[key] = build_parcel_matrix(labels, n_rois)

    return cache[key]

def extract_parcels(
    bold_file,
    atlas_img,
    n_rois,
    parcel_matrix_cache,
):
    img = nib.load(str(bold_file))

    if img.ndim != 4:
        raise ValueError(f"Expected 4D BOLD image, got shape {img.shape}: {bold_file}")

    parcel_matrix = get_resampled_parcel_matrix(
        img=img,
        atlas_img=atlas_img,
        n_rois=n_rois,
        cache=parcel_matrix_cache,
    )

    data = np.asarray(img.dataobj, dtype=np.float32)
    n_tp = data.shape[3]

    flat = data.reshape(-1, n_tp)
    ts = parcel_matrix @ flat
    ts = ts.T.astype(np.float32)

    return ts

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output_root", required=True)
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
        "output_bold",
    }

    missing_columns = required_columns - set(manifest.columns)

    if missing_columns:
        raise ValueError(f"Manifest is missing columns: {sorted(missing_columns)}")

    for column in required_columns:
        manifest[column] = manifest[column].astype(str)

    if manifest.empty:
        raise ValueError(f"Manifest is empty: {args.manifest}")

    atlas = datasets.fetch_atlas_schaefer_2018(
        n_rois=args.n_rois,
        data_dir=args.atlas_dir,
        yeo_networks=args.yeo_networks,
    )

    atlas_img = image.load_img(atlas.maps)
    parcel_matrix_cache = {}

    for row in manifest.itertuples(index=False):
        bold_file = Path(row.output_bold)
        parcel_ts = parcel_output_path(row, args.output_root)

        if not bold_file.exists():
            raise FileNotFoundError(f"Missing single-stimulus BOLD file: {bold_file}")

        parcel_ts.parent.mkdir(parents=True, exist_ok=True)

#        print(f"Extracting parcels from: {bold_file}")

        ts = extract_parcels(
            bold_file=bold_file,
            atlas_img=atlas_img,
            n_rois=args.n_rois,
            parcel_matrix_cache=parcel_matrix_cache,
        )

        np.save(parcel_ts, ts.astype(np.float32))

if __name__ == "__main__":
    main()