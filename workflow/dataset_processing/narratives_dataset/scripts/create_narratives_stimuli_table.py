import argparse
from pathlib import Path

import pandas as pd

def infer_task_name(path: Path) -> str:
    name = path.name

    if name.endswith("_transcript.txt"):
        return name.removesuffix("_transcript.txt")

    if name.endswith(".txt"):
        return name.removesuffix(".txt")

    return path.stem

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stimuli_dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    stimuli_dir = Path(args.stimuli_dir)

    if not stimuli_dir.exists():
        raise FileNotFoundError(f"Stimuli directory does not exist: {stimuli_dir}")

    rows = []

    for path in sorted(stimuli_dir.glob("*.txt")):
        task = infer_task_name(path)

        with open(path, "r", encoding="utf-8") as f:
            stimulus = f.read()

        rows.append(
            {
                "task": task,
                "stimulus": stimulus,
            }
        )

    if not rows:
        raise ValueError(f"No .txt files found in {stimuli_dir}")

    df = pd.DataFrame(rows)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(output, sep="\t", index=False)

if __name__ == "__main__":
    main()