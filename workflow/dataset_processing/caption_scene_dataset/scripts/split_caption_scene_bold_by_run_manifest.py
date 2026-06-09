import argparse
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd

def sample_key(subject, session, run):
    subject = f"{int(subject):02d}"
    session = f"{int(session):02d}"
    run = f"{int(run):03d}"

    return f"sub-{subject}_ses-{session}_run-{run}"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bold", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--session", required=True)
    parser.add_argument("--run", required=True)
    parser.add_argument("--stimulus_id", required=True)
    parser.add_argument("--event_index", required=True)
    parser.add_argument("--output_bold", required=True)

    args = parser.parse_args()

    run_key = sample_key(args.subject, args.session, args.run)

    manifest = pd.read_csv(args.manifest, sep="\t")

    required_columns = {
        "run_key",
        "stimulus_id",
        "event_index",
        "start_vol",
        "n_vols",
        "source_bold",
        "output_bold",
    }

    missing_columns = required_columns - set(manifest.columns)

    if missing_columns:
        raise ValueError(
            f"Manifest is missing required columns: {sorted(missing_columns)}. "
            f"Available columns are: {list(manifest.columns)}"
        )

    rows = manifest[
        (manifest["run_key"].astype(str) == run_key)
        & (manifest["stimulus_id"].astype(str) == str(args.stimulus_id))
        & (manifest["event_index"].astype(str) == str(args.event_index))
    ]

    if len(rows) == 0:
        raise ValueError(
            f"No manifest row found for run_key={run_key}, "
            f"stimulus_id={args.stimulus_id}, "
            f"event_index={args.event_index}, "
            f"output_bold={args.output_bold}"
        )

    if len(rows) > 1:
        raise ValueError(
            f"Multiple manifest rows found for run_key={run_key}, "
            f"stimulus_id={args.stimulus_id}, "
            f"event_index={args.event_index}, "
            f"output_bold={args.output_bold}"
        )

    row = rows.iloc[0]

    start_vol = int(row["start_vol"])
    n_vols = int(row["n_vols"])
    end_vol = start_vol + n_vols

    output_bold = Path(args.output_bold)
    output_bold.parent.mkdir(parents=True, exist_ok=True)

    img = nib.load(args.bold)

    if img.ndim != 4:
        raise ValueError(f"Expected a 4D BOLD image, got shape {img.shape}: {args.bold}")

    if start_vol < 0:
        raise ValueError(f"start_vol cannot be negative: {start_vol}")

    if n_vols <= 0:
        raise ValueError(f"n_vols must be positive: {n_vols}")

    if end_vol > img.shape[3]:
        raise ValueError(
            f"Requested volumes [{start_vol}:{end_vol}] exceed BOLD length "
            f"{img.shape[3]} for {args.bold}"
        )

    cropped = np.asanyarray(
        img.dataobj[..., start_vol:end_vol],
        dtype=np.float32,
    )

    cropped_img = nib.Nifti1Image(
        cropped,
        affine=img.affine,
        header=img.header.copy(),
    )

    cropped_img.header.set_data_dtype(np.float32)
    cropped_img.header.set_data_shape(cropped.shape)

    nib.save(cropped_img, output_bold)

if __name__ == "__main__":
    main()
paste only script, being carefull in indent it as the one I shared