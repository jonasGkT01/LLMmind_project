import argparse
from pathlib import Path

import pandas as pd

def stimulus_id_from_image(image):
    return Path(str(image)).stem

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image_caption_table", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output_dir", required=True)
    args = parser.parse_args()

    df = pd.read_csv(args.image_caption_table, sep="\t")
    manifest = pd.read_csv(args.manifest, sep="\t")

    required_columns = {"Image", "Caption"}
    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"Image-caption table is missing columns: {sorted(missing_columns)}. "
            f"Available columns are: {list(df.columns)}"
        )

    if "stimulus_id" not in manifest.columns:
        raise ValueError(
            f"Manifest is missing column: stimulus_id. "
            f"Available columns are: {list(manifest.columns)}"
        )

    manifest_stimuli = set(
        manifest["stimulus_id"]
        .dropna()
        .astype(str)
        .str.strip()
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for _, row in df.iterrows():
        image = str(row["Image"]).strip()
        caption = str(row["Caption"]).strip()

        if image == "" or image.lower() == "none":
            continue

        stimulus_id = stimulus_id_from_image(image)

        if stimulus_id not in manifest_stimuli:
            continue

        output_caption = output_dir / f"{stimulus_id}.txt"
        output_caption.write_text(caption + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()