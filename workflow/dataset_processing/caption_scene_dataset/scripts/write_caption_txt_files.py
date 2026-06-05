import argparse
from pathlib import Path

import pandas as pd

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--stimulus_id", required=True)
    parser.add_argument("--output_caption", required=True)
    args = parser.parse_args()

    manifest = pd.read_csv(args.manifest, sep="\t")

    required_columns = {
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
        (manifest["stimulus_id"].astype(str) == str(args.stimulus_id))
        & (manifest["output_caption"].astype(str) == str(args.output_caption))
    ]

    if len(rows) == 0:
        raise ValueError(
            f"No manifest row found for stimulus_id={args.stimulus_id}, "
            f"output_caption={args.output_caption}"
        )

    captions = (
        rows["caption"]
        .dropna()
        .astype(str)
        .map(str.strip)
        .loc[lambda s: s != ""]
        .drop_duplicates()
        .tolist()
    )

    output_caption = Path(args.output_caption)
    output_caption.parent.mkdir(parents=True, exist_ok=True)

    output_caption.write_text("\n".join(captions) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()