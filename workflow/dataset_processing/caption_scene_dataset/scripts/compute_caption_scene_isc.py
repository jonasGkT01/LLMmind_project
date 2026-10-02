# edited with AI assistance: Claude Code, Claude Opus 5.5 (claude-opus-5-5)
# last AI edit: 2026-10-02, see docs/changelog/developers/ for details

import argparse
from pathlib import Path

import numpy as np

from libraries.compute_isc import compute_isc_from_files

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--parcel_ts", 
                        nargs = "+", 
                        required = True)
    parser.add_argument("--subjects", 
                        nargs = "+", 
                        required = True, 
                        help = "The subject of each --parcel_ts file, in the same order")
    parser.add_argument("--isc_npy", 
                        required = True)
    parser.add_argument("--n_rois", 
                        type = int, 
                        required = True)
    args = parser.parse_args()

    print(f"Computing ISC {args.isc_npy} from {len(args.parcel_ts)} parcel files")

    # average each subject's repeated presentations first
    isc_mean = compute_isc_from_files(
        args.parcel_ts, 
        n_rois = args.n_rois, 
        subjects = args.subjects, 
    )

    isc_npy = Path(args.isc_npy)
    isc_npy.parent.mkdir(parents = True, exist_ok = True)
    np.save(isc_npy, isc_mean)

if __name__ == "__main__":
    main()
