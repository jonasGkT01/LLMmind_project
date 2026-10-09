# edited with AI assistance: Claude Code, Claude Opus 5.5 (claude-opus-5-5)
# last AI edit: 2026-10-09, see docs/changelog/developers/ for details
import argparse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
from nilearn import image

from libraries.fmri_processing import extract_parcels

TEMPLATEFLOW_URL = "https://templateflow.s3.amazonaws.com/tpl-MNI152NLin2009cAsym"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", 
                        required = True)
    parser.add_argument("--n_rois", 
                        type = int, 
                        required = True)
    parser.add_argument("--yeo_networks", 
                        type = int, 
                        required = True)
    parser.add_argument("--atlas_dir", 
                        type = str, 
                        required = True)
    args = parser.parse_args()

    manifest = pd.read_csv(args.manifest, sep = "\t")

    required_columns = {"bold_file", "parcel_ts"}
    missing_columns = required_columns - set(manifest.columns)

    if missing_columns:
        raise ValueError(f"Manifest is missing columns: {sorted(missing_columns)}")

    # download the Schaefer atlas in the space of the Narratives BOLD (MNI152NLin2009cAsym)
    # from TemplateFlow; nilearn's copy is in MNI152NLin6Asym
    atlas_name = (
        "tpl-MNI152NLin2009cAsym_res-01_atlas-Schaefer2018_"
        f"desc-{args.n_rois}Parcels{args.yeo_networks}Networks_dseg.nii.gz"
    )
    atlas_file = Path(args.atlas_dir)/atlas_name

    if not atlas_file.exists():
        atlas_file.parent.mkdir(parents = True, exist_ok = True)
        urllib.request.urlretrieve(f"{TEMPLATEFLOW_URL}/{atlas_name}", atlas_file)

    atlas_img = image.load_img(atlas_file)
    parcel_matrix_cache = {}

    for row in manifest.itertuples(index = False):
        bold_file = Path(row.bold_file)
        parcel_ts = Path(row.parcel_ts)

        if not bold_file.exists():
            raise FileNotFoundError(f"Missing BOLD file: {bold_file}")

        parcel_ts.parent.mkdir(parents = True, exist_ok = True)

        print(f"Extracting parcels from: {bold_file}")

        ts = extract_parcels(
            bold_file = bold_file, 
            atlas_img = atlas_img, 
            n_rois = args.n_rois, 
            parcel_matrix_cache = parcel_matrix_cache, 
        )

        np.save(parcel_ts, ts.astype(np.float32))

if __name__ == "__main__":
    main()
