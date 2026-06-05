import argparse
from pathlib import Path

import pandas as pd

def infer_task_from_isc_path(path):
    name = Path(path).name

    if not name.startswith("task-"):
        raise ValueError(f"ISC file does not start with task-: {path}")

    if name.endswith("_isc_mean.nii.gz"):
        return name.removeprefix("task-").removesuffix("_isc_mean.nii.gz")

    if name.endswith("_isc_mean.npy"):
        return name.removeprefix("task-").removesuffix("_isc_mean.npy")

    raise ValueError(f"Could not infer task from ISC filename: {path}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--isc_dir", required=True)
    parser.add_argument("--output_manifest", required=True)
    args = parser.parse_args()

    isc_dir = Path(args.isc_dir)

    isc_files = sorted(isc_dir.glob("task-*_isc_mean.nii.gz"))

    if len(isc_files) == 0:
        raise ValueError(f"No ISC NIfTI files found in: {isc_dir}")

    rows = []
    for path in isc_files:
        rows.append({
            "dataset": args.dataset,
            "task": infer_task_from_isc_path(path),
            "isc_file": str(path),
        })

    df = pd.DataFrame(rows)

    output = Path(args.output_manifest)
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, sep="\t", index=False)

if __name__ == "__main__":
    main()