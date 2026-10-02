# edited with AI assistance: Claude Code, Claude Opus 5.5 (claude-opus-5-5)
# last AI edit: 2026-10-02, see docs/changelog/developers/ for details
import argparse
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
from scipy.ndimage import map_coordinates

# cubic interpolation, as in NSD's own func1pt8-to-MNI mapping (map_interpolation)
SPLINE_ORDER = 3

def parcel_output_path(row, output_root):
    return (
        Path(output_root)
        /"parcels"
        /f"task-{row.stimulus_id}"
        /(
            f"sub-{row.subject}_ses-{row.session}_run-{row.run}_"
            f"task-{row.stimulus_id}_event-{row.event_index}_parcel_ts.npy"
        )
    )

def main():
    parser = argparse.ArgumentParser(description = "Warp one Caption Scene run to MNI, average it per Schaefer parcel and cut out its event windows")
    parser.add_argument("--run_manifest", 
                        required = True, 
                        help = "The run's events (manifest/by_run/<run_key>.tsv)")
    parser.add_argument("--bold", 
                        required = True)
    parser.add_argument("--sampling_coordinates", 
                        required = True, 
                        help = "The subject's .npz from compute_caption_scene_sampling_coordinates.py")
    parser.add_argument("--output_root", 
                        required = True)
    parser.add_argument("--n_rois", 
                        type = int, 
                        required = True)
    args = parser.parse_args()

    # load the events, the sampling coordinates and the run
    manifest = pd.read_csv(
        args.run_manifest, 
        sep = "\t", 
        dtype = {"subject": str, "session": str, "run": str}
    )

    if manifest.empty:
        raise ValueError(f"Run manifest is empty: {args.run_manifest}")

    if set(manifest["source_bold"]) != {str(Path(args.bold).resolve())}:
        raise ValueError(f"{args.run_manifest} does not describe {args.bold}")

    sampling = np.load(args.sampling_coordinates)
    coordinates = sampling["coordinates"].astype(np.float64)
    parcel_index = sampling["labels"].astype(np.int64) - 1
    voxels_per_parcel = np.bincount(parcel_index, minlength = args.n_rois)
    img = nib.load(args.bold)

    if img.ndim != 4:
        raise ValueError(
            f"Expected a 4D BOLD image, got shape {img.shape}: {args.bold}"
        )

    if (
        tuple(img.shape[:3]) != tuple(sampling["bold_shape"])
        or not np.allclose(img.affine, sampling["bold_affine"])
    ):
        raise ValueError(
            f"{args.bold} is not on the grid of {args.sampling_coordinates}"
        )

    if np.any(voxels_per_parcel == 0):
        raise ValueError(
            f"{args.sampling_coordinates} has parcels with no sampled voxel"
        )

    # warp and parcel-average only the volumes inside an event window; this equals cutting the
    # windows first, since both steps act volume by volume
    ends = manifest["start_vol"] + manifest["n_vols"]

    if manifest["start_vol"].min() < 0 or ends.max() > img.shape[3]:
        raise ValueError(
            f"Event windows of {args.run_manifest} exceed the run's "
            f"{img.shape[3]} volumes"
        )

    needed_volumes = sorted(
        {
            volume
            for start, n_vols in zip(manifest["start_vol"], manifest["n_vols"])
            for volume in range(int(start), int(start) + int(n_vols))
        }
    )
    parcel_values = {}

    for volume in needed_volumes:
        data = np.asarray(img.dataobj[..., volume], dtype = np.float64)
        sampled = map_coordinates(data, coordinates, order = SPLINE_ORDER)
        parcel_values[volume] = (
            np.bincount(parcel_index, weights = sampled, minlength = args.n_rois)
            /voxels_per_parcel
        )

    # cut each event window from the parcel series and save it
    for row in manifest.itertuples(index = False):
        window = range(int(row.start_vol), int(row.start_vol) + int(row.n_vols))
        parcel_ts = np.stack(
            [parcel_values[volume] for volume in window]
        ).astype(np.float32)
        output_path = parcel_output_path(row, args.output_root)
        output_path.parent.mkdir(parents = True, exist_ok = True)
        np.save(output_path, parcel_ts)

    print(
        f"Wrote {len(manifest)} event parcel series from {len(needed_volumes)} "
        f"volumes of {args.bold}"
    )

if __name__ == "__main__":
    main()
