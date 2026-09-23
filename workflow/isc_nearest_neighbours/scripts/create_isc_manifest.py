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

# Must match the extensions get_embeddings.load_stimuli() reads, so both sides agree on the stimulus set.
STIMULUS_EXTENSIONS = {".txt", ".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}

def eligible_stimuli_in_dir(stimuli_dir, excluded_stimuli):
    # Same selection as get_embeddings.load_stimuli(): the concepts the ISC side must provide.
    return {
        path.stem
        for path in Path(stimuli_dir).iterdir()
        if path.is_file()
        and path.suffix.lower() in STIMULUS_EXTENSIONS
        and path.stem not in excluded_stimuli
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--isc_dir", required=True)
    parser.add_argument("--excluded_stimuli", required=True)
    parser.add_argument("--stimuli_dirs", nargs="+", required=True)
    parser.add_argument("--output_manifest", required=True)
    args = parser.parse_args()

    isc_dir = Path(args.isc_dir)

    with open(args.excluded_stimuli, "r", encoding="utf-8") as input_file:
        excluded_stimuli = {line.strip() for line in input_file if line.strip()}

    eligible_by_dir = {
        stimuli_dir: eligible_stimuli_in_dir(stimuli_dir, excluded_stimuli)
        for stimuli_dir in args.stimuli_dirs
    }

    eligible_stimuli = next(iter(eligible_by_dir.values()))

    for stimuli_dir, stimuli in eligible_by_dir.items():
        if stimuli != eligible_stimuli:
            raise ValueError(f"Stimulus directories disagree on the eligible stimuli once {args.excluded_stimuli} is applied: {args.stimuli_dirs[0]} has {len(eligible_stimuli)}, {stimuli_dir} has {len(stimuli)} ({len(eligible_stimuli ^ stimuli)} differ)")

    if len(eligible_stimuli) == 0:
        raise ValueError(f"No eligible stimuli in {args.stimuli_dirs} after applying {args.excluded_stimuli}")

    # Built from the eligible stimuli, not by globbing isc_dir: each one must have an ISC file,
    # and leftover files from runs with a different stimulus filter are ignored.
    isc_files_by_task = {
        infer_task_from_isc_path(path): path
        for path in sorted(isc_dir.glob("task-*_isc_mean.npy"))
    }

    missing_isc = sorted(eligible_stimuli - isc_files_by_task.keys())

    if missing_isc:
        raise FileNotFoundError(f"{len(missing_isc)} of {len(eligible_stimuli)} eligible stimuli have no ISC file in {isc_dir}, e.g. {missing_isc[:5]}")

    ignored_isc = isc_files_by_task.keys() - eligible_stimuli

    if ignored_isc:
        print(f"Ignoring {len(ignored_isc)} ISC files in {isc_dir} for stimuli that are not eligible (excluded or stale)")

    rows = [
        {
            "dataset": args.dataset,
            "task": task,
            "isc_file": str(isc_files_by_task[task]),
        }
        for task in sorted(eligible_stimuli)
    ]

    df = pd.DataFrame(rows)

    output = Path(args.output_manifest)
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, sep="\t", index=True)

if __name__ == "__main__":
    main()