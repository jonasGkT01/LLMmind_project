import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from nilearn import datasets, image

from libraries.fmri_processing import extract_parcels

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--n_rois", type=int, required=True)
    parser.add_argument("--yeo_networks", type=int, required=True)
    parser.add_argument("--atlas_dir", type=str, required=True)
    args = parser.parse_args()

    manifest = pd.read_csv(args.manifest, sep="\t")

    required_columns = {"bold_file", "parcel_ts"}
    missing_columns = required_columns - set(manifest.columns)

    if missing_columns:
        raise ValueError(f"Manifest is missing columns: {sorted(missing_columns)}")

    atlas = datasets.fetch_atlas_schaefer_2018(
        n_rois=args.n_rois,
        data_dir=args.atlas_dir,
        yeo_networks=args.yeo_networks,
    )

    atlas_img = image.load_img(atlas.maps)
    parcel_matrix_cache = {}

    for row in manifest.itertuples(index=False):
        bold_file = Path(row.bold_file)
        parcel_ts = Path(row.parcel_ts)

        if not bold_file.exists():
            raise FileNotFoundError(f"Missing BOLD file: {bold_file}")

        parcel_ts.parent.mkdir(parents=True, exist_ok=True)

        print(f"Extracting parcels from: {bold_file}")

        ts = extract_parcels(
            bold_file=bold_file,
            atlas_img=atlas_img,
            n_rois=args.n_rois,
            parcel_matrix_cache=parcel_matrix_cache,
        )

        np.save(parcel_ts, ts.astype(np.float32))

if __name__ == "__main__":
    main()