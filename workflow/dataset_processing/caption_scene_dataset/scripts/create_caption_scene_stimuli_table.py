import argparse
from pathlib import Path

import pandas as pd

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--caption_scene_tsv", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    df = pd.read_csv(args.caption_scene_tsv, sep="\t")

    required = {"Image", "Caption"}
    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing columns: {sorted(missing)}. "
            f"Available columns: {list(df.columns)}"
        )

    out = (
        df[["Image", "Caption"]]
        .rename(columns={"Image": "task", "Caption": "stimulus"})
        .dropna()
        .drop_duplicates(subset=["task"])
    )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    out.to_csv(output, sep="\t", index=False)

if __name__ == "__main__":
    main()