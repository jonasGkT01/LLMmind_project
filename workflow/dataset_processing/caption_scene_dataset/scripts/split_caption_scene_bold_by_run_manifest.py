import argparse
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd

def validate_manifest(manifest):
    required_columns = {
        "source_bold",
        "output_bold",
        "start_vol",
        "n_vols",
    }

    missing_columns = required_columns - set(manifest.columns)

    if missing_columns:
        raise ValueError(
            f"Manifest is missing required columns: {sorted(missing_columns)}. Available columns are: {list(manifest.columns)}"
        )

def write_crop(img, output_bold, start_vol, n_vols):
    output_bold = Path(output_bold)
    output_bold.parent.mkdir(parents=True, exist_ok=True)

    start_vol = int(start_vol)
    n_vols = int(n_vols)
    end_vol = start_vol + n_vols

    if start_vol < 0:
        raise ValueError(f"start_vol cannot be negative: {start_vol}")

    if n_vols <= 0:
        raise ValueError(f"n_vols must be positive: {n_vols}")

    if end_vol > img.shape[3]:
        raise ValueError(
            f"Requested volumes [{start_vol}:{end_vol}] exceed BOLD length {img.shape[3]}"
        )

    cropped = np.asarray(img.dataobj[..., start_vol:end_vol], dtype=np.float32)

    cropped_img = nib.Nifti1Image(
        cropped,
        affine=img.affine,
        header=img.header.copy(),
    )

    cropped_img.header.set_data_dtype(np.float32)
    cropped_img.header.set_data_shape(cropped.shape)

    nib.save(cropped_img, str(output_bold))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args()

    manifest = pd.read_csv(args.manifest, sep="\t")
    validate_manifest(manifest)

    manifest["source_bold"] = manifest["source_bold"].astype(str)
    manifest["output_bold"] = manifest["output_bold"].astype(str)

    source_bolds = manifest["source_bold"].drop_duplicates().tolist()

    if len(source_bolds) != 1:
        raise ValueError(
            f"This split script expects one source BOLD file per manifest. Found {len(source_bolds)} source BOLD files: {source_bolds}"
        )

    source_bold = Path(source_bolds[0])

    if not source_bold.exists():
        raise FileNotFoundError(f"Missing source BOLD file: {source_bold}")

#    print(f"Loading source BOLD once: {source_bold}")

    img = nib.load(str(source_bold))

    if img.ndim != 4:
        raise ValueError(f"Expected 4D BOLD image, got shape {img.shape}: {source_bold}")

    for row in manifest.itertuples(index=False):
        write_crop(
            img=img,
            output_bold=row.output_bold,
            start_vol=row.start_vol,
            n_vols=row.n_vols,
        )

if __name__ == "__main__":
    main()