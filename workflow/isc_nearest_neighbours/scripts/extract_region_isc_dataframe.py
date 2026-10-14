# written with AI assistance: Claude Code, Claude Opus 5.5 (claude-opus-5-5)
# last AI edit: 2026-10-14, see docs/changelog/developers/ for details
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from libraries.parquet_io import read_parquet

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--isc_dataframe",
                        type = str,
                        required = True,
                        help = "Path to the whole-cortex ISC parquet dataframe")
    parser.add_argument("--region_parcels",
                        type = int,
                        nargs = "+",
                        required = True,
                        help = "1-based Schaefer label IDs of the region's parcels")
    parser.add_argument("--n_rois",
                        type = int,
                        required = True,
                        help = "Number of Schaefer parcels of the whole-cortex ISC vectors")
    parser.add_argument("--region_isc_dataframe",
                        type = str,
                        required = True,
                        help = "Path to the output region ISC parquet dataframe")
    args = parser.parse_args()

    # load the whole-cortex ISC vectors as a concepts x parcels matrix
    isc_df = read_parquet(args.isc_dataframe)
    isc = np.stack(isc_df["isc"].to_numpy())

    if isc.ndim != 2 or isc.shape[1] != args.n_rois:
        raise ValueError(
            f"Expected ISC vectors of {args.n_rois} values in {args.isc_dataframe}, "
            f"found shape {isc.shape}"
        )

    region_parcels = sorted(args.region_parcels)

    if len(set(region_parcels)) != len(region_parcels) or not (
        1 <= region_parcels[0] and region_parcels[-1] <= args.n_rois
    ):
        raise ValueError(
            f"Region parcels must be unique label IDs between 1 and {args.n_rois}: "
            f"{args.region_parcels}"
        )

    # keep only the region's parcels (position = label ID - 1), in label order
    region_isc = isc[:, np.asarray(region_parcels) - 1]

    # save with the layout of the whole-cortex dataframe: same concepts, one isc vector each
    region_df = pd.DataFrame(
        {"isc": list(region_isc)},
        index = isc_df.index,
    )
    output_path = Path(args.region_isc_dataframe)
    output_path.parent.mkdir(parents = True, exist_ok = True)
    region_df.to_parquet(output_path, engine = "pyarrow", index = True)

if __name__ == "__main__":
    main()
