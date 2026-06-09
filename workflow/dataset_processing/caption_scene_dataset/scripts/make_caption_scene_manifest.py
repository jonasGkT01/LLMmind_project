import argparse
import math
import re
import warnings
from pathlib import Path

import pandas as pd

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

def load_corrupted_niis(corrupted_niis):
    corrupted_niis = Path(corrupted_niis)

    if not corrupted_niis.exists():
        raise FileNotFoundError(f"Corrupted NIfTI list does not exist: {corrupted_niis}")

    corrupted_paths = set()

    with corrupted_niis.open("r") as f:
        for line in f:
            path = line.strip()

            if path:
                corrupted_paths.add(str(Path(path)))
                corrupted_paths.add(str(Path(path).resolve()))

    return corrupted_paths

def is_corrupted_bold(bold, corrupted_paths):
    bold_path = Path(bold)

    return (
        str(bold_path) in corrupted_paths
        or str(bold_path.resolve()) in corrupted_paths
    )

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bold_files", nargs="+", required=True)
    parser.add_argument("--run_tables", nargs="+", required=True)
    parser.add_argument("--corrupted_niis", required=True)
    parser.add_argument("--output_manifest", required=True)
    parser.add_argument("--output_root", required=True)
    parser.add_argument("--tr", required=True, type=float)
    parser.add_argument("--event_duration_s", required=True, type=float)
    parser.add_argument("--onset_shift_s", default=0.0, type=float)
    parser.add_argument("--run_table_encoding", default="gbk")

    args = parser.parse_args()

    if len(args.bold_files) != len(args.run_tables):
        raise ValueError(
            "The number of BOLD files and run tables must be identical. "
            f"Got {len(args.bold_files)} BOLD files and {len(args.run_tables)} run tables."
        )

    corrupted_paths = load_corrupted_niis(args.corrupted_niis)

    n_vols = int(math.ceil(args.event_duration_s / args.tr))
    rows = []
    skipped_corrupted = 0

    for bold, run_table in zip(args.bold_files, args.run_tables):
        fields = parse_bold_path(bold)

        subject = fields["subject"]
        session = fields["session"]
        run = fields["run"]
        run_key = sample_key(subject, session, run)

        if is_corrupted_bold(bold, corrupted_paths):
            skipped_corrupted += 1
            warnings.warn(
                f"Skipping corrupted BOLD file while creating manifest: {bold}. "
                f"No expected single-stimulus outputs will be added for {run_key}.",
                RuntimeWarning,
            )
            continue

        df = read_run_table(run_table, args.run_table_encoding)

        required_columns = {"Index", "Onset", "Blank", "Unmatch", "Image", "Caption"}
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
                    f"Negative crop start for {run_key}, event {event_index}, "
                    f"image {image}: {crop_start_s}"
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
        raise ValueError("Global manifest is empty. No valid CSD events were found.")

    out = out.sort_values(
        ["subject", "session", "run", "event_index"]
    ).reset_index(drop=True)

    output_path = Path(args.output_manifest)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    out.to_csv(output_path, sep="\t", index=False)

    print(f"Wrote global manifest with {len(out)} rows to {output_path}")
    print(f"Skipped {skipped_corrupted} corrupted BOLD files listed in {args.corrupted_niis}")

if __name__ == "__main__":
    main()