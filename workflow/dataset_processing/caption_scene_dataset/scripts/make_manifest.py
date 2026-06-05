import argparse
import math
import re
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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bold_files", nargs="+", required=True)
    parser.add_argument("--run_tables", nargs="+", required=True)
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

    n_vols = int(math.ceil(args.event_duration_s / args.tr))
    rows = []

    for bold, run_table in zip(args.bold_files, args.run_tables):
        fields = parse_bold_path(bold)

        subject = fields["subject"]
        session = fields["session"]
        run = fields["run"]
        run_key = sample_key(subject, session, run)

        df = read_run_table(run_table, args.run_table_encoding)

        required = {"Index", "Onset", "Blank", "Unmatch", "Image", "Caption"}
        missing = required - set(df.columns)

        if missing:
            raise ValueError(
                f"Run table {run_table} is missing columns: {sorted(missing)}"
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
            image = str(row["Image"])
            stimulus_id = stimulus_id_from_image(image)
            event_index = int(row["Index"])

            onset_s = float(row["Onset"])
            shifted_onset_s = onset_s + float(args.onset_shift_s)

            if shifted_onset_s < 0:
                raise ValueError(
                    f"Negative shifted onset for {run_key}, {image}: {shifted_onset_s}"
                )

            start_vol = int(round(shifted_onset_s / args.tr))

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
                    "onset_s": onset_s,
                    "shifted_onset_s": shifted_onset_s,
                    "tr": args.tr,
                    "start_vol": start_vol,
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

if __name__ == "__main__":
    main()