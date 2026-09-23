import argparse
from pathlib import Path

import pandas as pd

def infer_task_from_isc_path(path):
    name = Path(path).name

    if not name.startswith("task-"):
        raise ValueError(f"ISC file does not start with task-: {path}")

    if not name.endswith("_isc_mean.npy"):
        raise ValueError(f"Could not infer task from ISC filename: {path}")

    return name.removeprefix("task-").removesuffix("_isc_mean.npy")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--isc_dir", required=True)
    parser.add_argument("--excluded_stimuli", required=True)
    parser.add_argument("--output_manifest", required=True)
    args = parser.parse_args()

    isc_dir = Path(args.isc_dir)

    with open(args.excluded_stimuli, "r", encoding="utf-8") as input_file:
        excluded_stimuli = {line.strip() for line in input_file if line.strip()}

    isc_files = sorted(isc_dir.glob("task-*_isc_mean.npy"))

    if len(isc_files) == 0:
        raise ValueError(f"No ISC NPY files found in: {isc_dir}")

    # The dataset's excluded-stimuli file is the single list of stimuli that must not enter the
    # analysis (it is also what get_embeddings skips), so ISC files left over in isc_dir from an
    # earlier run with a looser stimulus filter are dropped here rather than silently included.
    rows = []
    for path in isc_files:
        task = infer_task_from_isc_path(path)

        if task in excluded_stimuli:
            continue

        rows.append({
            "dataset": args.dataset,
            "task": task,
            "isc_file": str(path),
        })

    if len(rows) == 0:
        raise ValueError(f"Every ISC NPY file in {isc_dir} belongs to an excluded stimulus listed in {args.excluded_stimuli}")

    df = pd.DataFrame(rows)

    output = Path(args.output_manifest)
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, sep="\t", index=True)

if __name__ == "__main__":
    main()