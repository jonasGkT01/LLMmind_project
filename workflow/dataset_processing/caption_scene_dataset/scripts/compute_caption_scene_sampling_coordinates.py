# written with AI assistance: Claude Code, Claude Opus 5.5 (claude-opus-5-5)
# last AI edit: 2026-10-02, see docs/changelog/developers/ for details
import argparse
from pathlib import Path
import subprocess
import tempfile

import nibabel as nib
from nilearn import datasets
import numpy as np

# an atlas voxel is sampled only if it maps fully inside the native field of view
INSIDE_THRESHOLD = 0.999

def check_common_grid(bold_files):
    # every run of a subject must share one BOLD grid, so one set of coordinates serves all
    first = nib.load(bold_files[0])

    for bold_file in bold_files[1:]:
        img = nib.load(bold_file)

        if (
            img.shape[:3] != first.shape[:3]
            or not np.allclose(img.affine, first.affine)
        ):
            raise ValueError(
                f"{bold_file} is not on the same grid as {bold_files[0]}: "
                f"{img.shape[:3]} vs {first.shape[:3]}"
            )

    return first

def warp_to_atlas(image, atlas_file, warp, affine, default_value, work_dir, name):
    # resample a native-grid image onto the atlas grid with the T1w-to-MNI transforms
    source = Path(work_dir)/f"{name}.nii.gz"
    target = Path(work_dir)/f"mni_{name}.nii.gz"
    nib.save(image, source)
    subprocess.run(
        [
            "antsApplyTransforms", 
            "-d", "3", 
            "-i", str(source), 
            "-r", str(atlas_file), 
            "-o", str(target), 
            "-t", str(warp), 
            "-t", str(affine), 
            "-n", "Linear", 
            "-f", str(default_value), 
            "--float", 
        ], 
        check = True, 
    )

    return nib.load(target).get_fdata()

def main():
    parser = argparse.ArgumentParser(description = "For every atlas voxel in a parcel, find the native BOLD voxel coordinate to sample")
    parser.add_argument("--bold_files", 
                        nargs = "+", 
                        required = True, 
                        help = "All BOLD runs of one subject")
    parser.add_argument("--affine", 
                        required = True, 
                        help = "antsRegistration affine (T1w to MNI)")
    parser.add_argument("--warp", 
                        required = True, 
                        help = "antsRegistration warp field (T1w to MNI)")
    parser.add_argument("--n_rois", 
                        type = int, 
                        required = True)
    parser.add_argument("--yeo_networks", 
                        type = int, 
                        required = True)
    parser.add_argument("--atlas_dir", 
                        required = True)
    parser.add_argument("--output", 
                        required = True)
    args = parser.parse_args()

    # load the atlas and check the runs' common grid
    atlas_file = datasets.fetch_atlas_schaefer_2018(
        n_rois = args.n_rois, 
        data_dir = args.atlas_dir, 
        yeo_networks = args.yeo_networks, 
    ).maps
    atlas = np.asarray(nib.load(atlas_file).dataobj).astype(np.int32)
    in_parcel = (atlas > 0) & (atlas <= args.n_rois)
    bold = check_common_grid(args.bold_files)
    shape = bold.shape[:3]

    # warp the native voxel indices (i, j, k) and a field-of-view mask onto the atlas grid
    indices = np.indices(shape).astype(np.float32)

    with tempfile.TemporaryDirectory(dir = Path(args.output).parent) as work_dir:
        coordinates = np.stack(
            [
                warp_to_atlas(
                    nib.Nifti1Image(indices[axis], bold.affine), 
                    atlas_file, 
                    args.warp, 
                    args.affine, 
                    -1, 
                    work_dir, 
                    f"index_{axis}", 
                )[in_parcel]
                for axis in range(3)
            ]
        )
        inside = warp_to_atlas(
            nib.Nifti1Image(np.ones(shape, dtype = np.float32), bold.affine), 
            atlas_file, 
            args.warp, 
            args.affine, 
            0, 
            work_dir, 
            "inside", 
        )[in_parcel]

    upper = (np.asarray(shape) - 1)[:, None]
    valid = (
        (inside >= INSIDE_THRESHOLD)
        & np.all(coordinates >= 0, axis = 0)
        & np.all(coordinates <= upper, axis = 0)
    )
    labels = atlas[in_parcel]

    # report the share of each parcel inside the native field of view; stop on empty parcels
    voxels = np.bincount(labels, minlength = args.n_rois + 1)[1:]
    covered = np.bincount(labels[valid], minlength = args.n_rois + 1)[1:]
    coverage = covered/voxels

    if np.any(covered == 0):
        raise ValueError(
            f"Parcels with no voxel inside the BOLD field of view: "
            f"{(np.where(covered == 0)[0] + 1).tolist()}"
        )

    print(
        f"Parcel coverage: minimum {coverage.min():.3f}, "
        f"median {np.median(coverage):.3f}, "
        f"{int(np.sum(coverage < 0.9))} parcels below 0.9"
    )

    # save the coordinates of the sampled voxels, their parcels and the grid they refer to
    np.savez_compressed(
        args.output, 
        coordinates = coordinates[:, valid].astype(np.float32), 
        labels = labels[valid].astype(np.int16), 
        bold_shape = np.asarray(shape), 
        bold_affine = bold.affine, 
    )

if __name__ == "__main__":
    main()
