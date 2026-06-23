import argparse
import math
import re
import warnings
from pathlib import Path

import pandas as pd

import nibabel as nib

def parse_bold_path(path):
    name = Path(path).name

    pattern = (
        r"sub-(?P<subject>[^_]+)"
        r"_ses-(?P<session>[^_]+)"
        r"_task-CSD"
        r"_run-(?P<run>[^.]+)"
        r"\.nii\.gz$"
    )

    match = re.match(pattern, name)

    if match is None:
        raise ValueError(f"Could not parse BOLD filename: {path}")

    return match.groupdict()

def sample_key(subject, session, run):
    return f"sub-{subject}_ses-{session}_run-{run}"

def stimulus_id_from_image(image):
    return Path(str(image)).stem

def read_run_table(path, encoding):
    return pd.read_csv(path, sep=None, engine="python", encoding=encoding)

def write_lines(values, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w") as f:
        for value in sorted(set(values)):
            f.write(f"{value}\n")

def is_valid_nifti(path):
    try:
        img = nib.load(path)

        # Access metadata.
        _ = img.shape
        _ = img.affine

        # Force the complete compressed NIfTI payload to be read.
        _ = img.dataobj.get_unscaled()

        return True

    except Exception as exc:
        warnings.warn(
            f"Skipping unreadable or corrupted NIfTI file {path}: {exc}",
            RuntimeWarning,
        )
        return False

def write_run_manifests(out, output_run_manifest_dir, output_run_manifest_index):
    output_run_manifest_dir = Path(output_run_manifest_dir)
    output_run_manifest_index = Path(output_run_manifest_index)

    output_run_manifest_dir.mkdir(parents=True, exist_ok=True)
    output_run_manifest_index.parent.mkdir(parents=True, exist_ok=True)

    index_rows = []

    for run_key, run_df in out.groupby("run_key", sort=False):
        run_manifest = output_run_manifest_dir / f"{run_key}.tsv"
        run_df.to_csv(run_manifest, sep="\t", index=False)

        unique_source_bolds = sorted(run_df["source_bold"].unique().tolist())
        unique_run_tables = sorted(run_df["run_table"].unique().tolist())

        if len(unique_source_bolds) != 1:
            raise ValueError(
                f"Run manifest {run_key} has multiple source BOLD files: {unique_source_bolds}"
            )

        if len(unique_run_tables) != 1:
            raise ValueError(
                f"Run manifest {run_key} has multiple run tables: {unique_run_tables}"
            )

        index_rows.append(
            {
                "run_key": run_key,
                "source_bold": unique_source_bolds[0],
                "run_table": unique_run_tables[0],
                "run_manifest": str(run_manifest),
                "n_events": len(run_df),
            }
        )

    pd.DataFrame(index_rows).to_csv(
        output_run_manifest_index,
        sep="\t",
        index=False,
    )

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bold_files", nargs="+", required=True)
    parser.add_argument("--run_tables", nargs="+", required=True)
    parser.add_argument(
        "--output_singleton_stimuli",
        required=True,
        help="Output text file containing stimulus IDs represented by only one NIfTI",
    )
    parser.add_argument("--output_manifest", required=True)
    parser.add_argument("--output_run_manifest_dir", required=True)
    parser.add_argument("--output_run_manifest_index", required=True)
    parser.add_argument("--output_root", required=True)
    parser.add_argument("--tr", required=True, type=float)
    parser.add_argument("--event_duration_s", required=True, type=float)
    parser.add_argument("--onset_shift_s", default=0.0, type=float)
    parser.add_argument("--run_table_encoding", default="gbk")

    args = parser.parse_args()

    if len(args.bold_files) != len(args.run_tables):
        raise ValueError(
            f"The number of BOLD files and run tables must be identical. Got {len(args.bold_files)} BOLD files and {len(args.run_tables)} run tables"
        )

    n_vols = int(math.ceil(args.event_duration_s / args.tr))
    rows = []
    skipped_corrupted = 0

    for bold, run_table in zip(args.bold_files, args.run_tables):
        fields = parse_bold_path(bold)

        subject = fields["subject"]
        session = fields["session"]
        run = fields["run"]
        run_key = sample_key(subject, session, run)

        if not is_valid_nifti(bold):
            skipped_corrupted += 1
            continue

        df = read_run_table(run_table, args.run_table_encoding)

        required_columns = {
            "Index",
            "Onset",
            "Blank",
            "Unmatch",
            "Image",
            "Caption",
        }
        missing_columns = required_columns - set(df.columns)

        if missing_columns:
            raise ValueError(
                f"Run table {run_table} is missing columns: {sorted(missing_columns)}"
            )

        df["Image"] = df["Image"].astype(str)

        valid = df[
            (df["Blank"].astype(int) == 0)
            & (df["Unmatch"].astype(int) == 0)
            & (df["Image"].str.lower() != "none")
            & (df["Image"].str.strip() != "")
        ].copy()

        seen_outputs = set()

        for _, row in valid.iterrows():
            image = str(row["Image"]).strip()
            stimulus_id = stimulus_id_from_image(image)
            event_index = int(row["Index"])

            onset_s = float(row["Onset"])
            crop_start_s = onset_s + float(args.onset_shift_s)

            if crop_start_s < 0:
                raise ValueError(
                    f"Negative crop start for {run_key}, event {event_index}, image {image}: {crop_start_s}"
                )

            start_vol = int(round(crop_start_s / args.tr))
            crop_end_s = crop_start_s + float(args.event_duration_s)
            end_vol = start_vol + n_vols

            output_bold = (
                Path(args.output_root)
                / "single_stimulus_bold"
                / f"sub-{subject}"
                / f"ses-{session}"
                / f"run-{run}"
                / f"{stimulus_id}_event-{event_index}.nii.gz"
            )

            if output_bold in seen_outputs:
                raise ValueError(
                    f"Duplicate output path inside {run_key}: {output_bold}"
                )

            seen_outputs.add(output_bold)

            rows.append(
                {
                    "run_key": run_key,
                    "subject": subject,
                    "session": session,
                    "run": run,
                    "event_index": event_index,
                    "image": image,
                    "stimulus_id": stimulus_id,
                    "caption": str(row["Caption"]),
                    "blank": int(row["Blank"]),
                    "unmatch": int(row["Unmatch"]),
                    "onset_s": onset_s,
                    "onset_shift_s": float(args.onset_shift_s),
                    "crop_start_s": crop_start_s,
                    "event_duration_s": float(args.event_duration_s),
                    "crop_end_s": crop_end_s,
                    "tr": float(args.tr),
                    "start_vol": start_vol,
                    "end_vol": end_vol,
                    "n_vols": n_vols,
                    "source_bold": str(Path(bold).resolve()),
                    "run_table": str(Path(run_table).resolve()),
                    "output_bold": str(output_bold),
                }
            )

    out = pd.DataFrame(rows)

    if out.empty:
        write_lines([], args.output_singleton_stimuli)

        raise ValueError(
            "Global manifest is empty. No valid events were found after excluding unreadable or corrupted BOLD files"
        )

    stimulus_counts = out.groupby("stimulus_id").size()

    valid_stimuli = stimulus_counts[
        stimulus_counts >= 2
    ].index

    singleton_stimuli = stimulus_counts[
        stimulus_counts == 1
    ].index.tolist()

    write_lines(
        singleton_stimuli,
        args.output_singleton_stimuli,
    )

    if singleton_stimuli:
        warnings.warn(
            "Removing stimuli represented by only one valid single-stimulus NIfTI: " + ", ".join(sorted(singleton_stimuli)),
            RuntimeWarning,
        )

    out = out[out["stimulus_id"].isin(valid_stimuli)].copy()

    if out.empty:
        raise ValueError(
            "Global manifest is empty after removing stimuli represented by fewer than two single-stimulus NIfTI files"
        )

    out = out.sort_values(
        ["subject", "session", "run", "event_index"]
    ).reset_index(drop=True)

    output_path = Path(args.output_manifest)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    out.to_csv(output_path, sep="\t", index=False)

    write_run_manifests(
        out=out,
        output_run_manifest_dir=args.output_run_manifest_dir,
        output_run_manifest_index=args.output_run_manifest_index,
    )

    print(f"Wrote global manifest with {len(out)} rows to {output_path}")
    print(f"Wrote run manifests to {args.output_run_manifest_dir}")
    print(f"Wrote run manifest index to {args.output_run_manifest_index}")
    print(f"Skipped {skipped_corrupted} unreadable or corrupted BOLD files")
    print(f"Wrote {len(singleton_stimuli)} singleton stimulus IDs to {args.output_singleton_stimuli}")

if __name__ == "__main__":
    main()