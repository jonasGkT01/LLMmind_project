import argparse
from pathlib import Path

import numpy as np
from nilearn import datasets
from nilearn.maskers import NiftiLabelsMasker

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bold_file", required=True)
    parser.add_argument("--parcel_ts", required=True)
    parser.add_argument("--n_rois", type=int, required=True)
    parser.add_argument("--yeo_networks", type=int, required=True)
    parser.add_argument("--atlas_dir", type=str, required=True)
    args = parser.parse_args()

    bold_file = args.bold_file
    parcel_ts = Path(args.parcel_ts)

    parcel_ts.parent.mkdir(parents=True, exist_ok=True)

    atlas = datasets.fetch_atlas_schaefer_2018(
        n_rois=args.n_rois,
        data_dir=args.atlas_dir,
        yeo_networks=args.yeo_networks,
    )

    masker = NiftiLabelsMasker(
        labels_img=atlas.maps,
        standardize="zscore_sample",
        detrend=True,
    )

    ts = masker.fit_transform(bold_file)

    if ts.ndim != 2:
        raise ValueError(
            f"Expected parcel time series with 2 dimensions, got shape {ts.shape} "
            f"from BOLD file: {bold_file}"
        )

    if ts.shape[1] != args.n_rois:
        raise ValueError(
            f"Expected {args.n_rois} parcels, got {ts.shape[1]} parcels "
            f"from BOLD file: {bold_file}"
        )

    np.save(parcel_ts, ts.astype(np.float32))

if __name__ == "__main__":
    main()