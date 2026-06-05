import argparse
from pathlib import Path

import pandas as pd


def sample_key(subject, session, run):
    return f"sub-{subject}_ses-{session}_run-{run}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--session", required=True)
    parser.add_argument("--run", required=True)
    parser.add_argument("--stimulus_id", required=True)
    parser.add_argument("--output_caption", required=True)
    args = parser.parse_args()

    run_key = sample_key(args.subject, args.session, args.run)

    manifest = pd.read_csv(args.manifest, sep="\t")

    required_columns = {
        "run_key",
        "stimulus_id",
        "caption",
        "output_caption",
    }

    missing_columns = required_columns - set(manifest.columns)
    if missing_columns:
        raise ValueError(
            f"Manifest is missing required columns: {sorted(missing_columns)}. "
            f"Available columns are: {list(manifest.columns)}"
        )

    rows = manifest[
        (manifest["run_key"].astype(str) == run_key)
        & (manifest["stimulus_id"].astype(str) == args.stimulus_id)
        & (manifest["output_caption"].astype(str) == args.output_caption)
    ]

    if len(rows) == 0:
        raise ValueError(
            f"No manifest row found for run_key={run_key}, "
            f"stimulus_id={args.stimulus_id}, output_caption={args.output_caption}"
        )

    if len(rows) > 1:
        captions = (
            rows["caption"]
            .dropna()
            .astype(str)
            .map(str.strip)
            .loc[lambda s: s != ""]
            .drop_duplicates()
            .tolist()
        )
    else:
        caption = rows.iloc[0]["caption"]
        captions = [] if pd.isna(caption) else [str(caption).strip()]

    output_caption = Path(args.output_caption)
    output_caption.parent.mkdir(parents=True, exist_ok=True)

    output_caption.write_text("\n".join(captions) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()