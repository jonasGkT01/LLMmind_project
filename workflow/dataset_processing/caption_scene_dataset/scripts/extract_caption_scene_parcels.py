import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from nilearn import datasets, image

from libraries.fmri_processing import extract_parcels

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