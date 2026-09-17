import argparse

from pathlib import Path

import numpy as np
import pandas as pd
from nilearn import datasets, image

from libraries.fmri_processing import extract_parcels

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--number_of_regions", type=int, required=True)
    parser.add_argument("--number_of_yeo_networks", type=int, required=True)
    parser.add_argument("--atlas_dir", required=True)
    arguments = parser.parse_args()

    parcel_manifest = pd.read_csv(arguments.manifest, sep="\t")

    required_columns = {
        "subject",
        "stimulus_id",
        "bold_file",
        "parcel_time_series",
    }

    missing_columns = required_columns - set(parcel_manifest.columns)

    if missing_columns:
        raise ValueError(f"Parcel manifest is missing columns: {sorted(missing_columns)}")

    if parcel_manifest.empty:
        raise ValueError(f"Parcel manifest is empty: {arguments.manifest}")

    duplicated_outputs = parcel_manifest[parcel_manifest["parcel_time_series"].duplicated(keep=False)]

    if not duplicated_outputs.empty:
        raise ValueError("Parcel manifest contains duplicated parcel output paths")

    atlas = datasets.fetch_atlas_schaefer_2018(
        n_rois=arguments.number_of_regions,
        data_dir=arguments.atlas_dir,
        yeo_networks=arguments.number_of_yeo_networks,
    )

    atlas_image = image.load_img(atlas.maps)
    parcel_matrix_cache = {}

    for manifest_row in parcel_manifest.itertuples(index=False):
        bold_file = Path(manifest_row.bold_file)
        parcel_time_series_file = Path(manifest_row.parcel_time_series)

        if not bold_file.exists():
            raise FileNotFoundError(f"Missing BOLD file: {bold_file}")

        parcel_time_series_file.parent.mkdir(parents=True, exist_ok=True)

        parcel_time_series = extract_parcels(
            bold_file=bold_file,
            atlas_img=atlas_image,
            n_rois=arguments.number_of_regions,
            parcel_matrix_cache=parcel_matrix_cache,
        )

        np.save(parcel_time_series_file, parcel_time_series.astype(np.float32))

        print(f"Saved parcel time series {parcel_time_series_file} with shape {parcel_time_series.shape}")

if __name__ == "__main__":
    main()