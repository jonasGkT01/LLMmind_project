# edited with AI assistance: Claude Code, Claude Opus 5.5 (claude-opus-5-5)
# last AI edit: 2026-10-02, see docs/changelog/developers/ for details
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from libraries.path_metadata import parse_isc_task_path

def load_isc_value(npy_path: Path):
    value = np.load(npy_path)
    # convert 0-d arrays / numpy scalars to plain Python scalars when possible
    if isinstance(value, np.ndarray) and value.shape == ():
        value = value.item()

    return value

def isc_npys_to_dataframe(input_isc_npys: list[str]) -> pd.DataFrame:
    records = []

    for npy_file in input_isc_npys:
        path = Path(npy_file)
        task = parse_isc_task_path(path)
        isc = load_isc_value(path)

        records.append({
            "concept": task, 
            "isc": isc, 
        })

    df = pd.DataFrame(records).set_index("concept")
    return df

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--isc_npys", 
                        type = str, 
                        nargs = "+", 
                        required = True, 
                        help = "List of ISC numpy files, one per task")
    parser.add_argument("--isc_dataframe", 
                        type = str, 
                        required = True, 
                        help = "Path to output parquet dataframe")
    args = parser.parse_args()

    df = isc_npys_to_dataframe(args.isc_npys)

    output_path = Path(args.isc_dataframe)
    output_path.parent.mkdir(parents = True, exist_ok = True)
    df.to_parquet(output_path, engine = "pyarrow", index = True)

if __name__ == "__main__":
    main()
