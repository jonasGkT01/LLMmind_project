import argparse
from pathlib import Path

import pandas as pd

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output_manifest", required=True)
    args = parser.parse_args()

    output_manifest = Path(args.output_manifest)
    output_manifest.parent.mkdir(parents=True, exist_ok=True)

    # Temporary example.
    # Replace this block with dataset-specific discovery logic.
    raise NotImplementedError(
        "Add dataset-specific logic here to discover stimulus_id values."
    )

    rows = []
    for stimulus_id in stimulus_ids:
        rows.append(
            {
                "stimulus_id": stimulus_id,
                "isc_npy": (
                    f"results/mind/{args.dataset}/isc/"
                    f"task-{stimulus_id}_isc_mean.npy"
                ),
            }
        )

    pd.DataFrame(rows).to_csv(output_manifest, sep="\t", index=False)

if __name__ == "__main__":
    main()