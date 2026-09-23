import argparse

from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd

from nilearn import datasets, image
from nsdcode.nsd_datalocation import nsd_datalocation
from nsdcode.parse_case import parse_case
from nsdcode.load_data import load_transform
from nsdcode.interp_wrapper import interp_wrapper

from libraries.fmri_processing import get_resampled_parcel_matrix

NSD_MAP_SOURCE_SPACE = "func1pt8"
NSD_MAP_TARGET_SPACE = "MNI"
NSD_MAP_OUTPUT_CLASS = np.float32
NSD_MNI_VOXEL_SIZE = 1
NSD_MNI_ORIGIN = np.asarray([183 - 91, 127, 73]) - 1

_subject_mni_transform_cache = {}
_parcel_matrix_cache = {}
_atlas_image_cache = {}

def get_subject_mni_transform(dataset_dir, subject):
    # NSDmapdata.fit() reloads the ~50MB func1pt8-to-MNI deformation field from disk
    # and rebuilds the flattened interpolation coordinates from it on every single
    # call, at a cost of several seconds. Since this only depends on the subject, and
    # this script calls the mapping once per stimulus occurrence (tens of thousands of
    # times across all subjects), that redundant reload dominates the runtime. Loading
    # and building it once per subject and reusing it here removes that redundancy
    # without changing the mapping itself.
    if subject not in _subject_mni_transform_cache:
        nsd_path = nsd_datalocation(dataset_dir)
        transforms_dir = Path(nsd_path) / "ppdata" / f"subj{subject:02d}" / "transforms"
        casenum, transform_file = parse_case(NSD_MAP_SOURCE_SPACE, NSD_MAP_TARGET_SPACE, str(transforms_dir))

        if casenum != 1:
            raise ValueError(f"Expected a volume-to-volume transform for {NSD_MAP_SOURCE_SPACE}->{NSD_MAP_TARGET_SPACE}, got case {casenum}")

        transform = load_transform(casenum, transform_file)
        target_shape = transform.shape[:3]

        coords = np.c_[
            transform[:, :, :, 0].ravel(order="F"),
            transform[:, :, :, 1].ravel(order="F"),
            transform[:, :, :, 2].ravel(order="F"),
        ].T
        coords[coords == 9999] = np.nan
        coords -= 1

        # interp_wrapper() mutates invalid (non-finite) coordinates in place, which
        # would silently stop marking those locations as invalid on a second reuse.
        # Sharing the same array across calls is only safe when there is nothing to
        # mutate, so fall back to copying per occurrence if any turn up.
        reusable = not np.any(~np.isfinite(coords))

        _subject_mni_transform_cache[subject] = (coords, target_shape, reusable)

    return _subject_mni_transform_cache[subject]

def nsd_mni_affine():
    # Same affine nsdcode's nsd_write_vol() gives the MNI volumes it writes out, so the
    # atlas is resampled onto exactly the grid the mapped data lives on.
    affine = np.diag([NSD_MNI_VOXEL_SIZE] * 3 + [1]).astype(np.float64)
    affine[:3, -1] = -NSD_MNI_ORIGIN * NSD_MNI_VOXEL_SIZE

    return affine

def get_mni_parcel_matrix(target_shape, atlas_maps, number_of_regions):
    if atlas_maps not in _atlas_image_cache:
        _atlas_image_cache[atlas_maps] = image.load_img(atlas_maps)

    mni_grid_image = nib.Nifti1Image(np.zeros(target_shape, dtype=np.float32), nsd_mni_affine())

    return get_resampled_parcel_matrix(
        img=mni_grid_image,
        atlas_img=_atlas_image_cache[atlas_maps],
        n_rois=number_of_regions,
        cache=_parcel_matrix_cache,
    )

def map_occurrence_to_mni(cropped_bold_data, coords, target_shape, reusable, interptype, badval):
    occurrence_coords = coords if reusable else coords.copy()

    mapped_volumes = []

    for volume_index in range(cropped_bold_data.shape[-1]):
        mapped_volume = interp_wrapper(
            cropped_bold_data[..., volume_index],
            occurrence_coords,
            interptype=interptype,
        ).astype(NSD_MAP_OUTPUT_CLASS)

        mapped_volume[np.isnan(mapped_volume)] = badval
        mapped_volumes.append(np.reshape(mapped_volume, target_shape, order="F"))

    mapped_bold_data = np.moveaxis(np.asarray(mapped_volumes), 0, -1)

    # In the case of the target being MNI, the volumes are LPI, so the first (X)
    # dimension must be flipped (see NSDmapdata.fit()'s docstring).
    return np.flip(mapped_bold_data, axis=0)

def process_group(dataset_dir, subject, source_bold, occurrences, interptype, badval, atlas_maps, number_of_regions):
    # Runs in a worker process when --jobs > 1: each worker keeps its own transform and
    # parcel-matrix caches, so a worker only pays the per-subject load once across however
    # many (subject, source_bold) groups it is assigned.
    source_bold_image = nib.load(str(source_bold))

    if source_bold_image.ndim != 4:
        raise ValueError(f"Expected a 4D BOLD image, got shape {source_bold_image.shape}: {source_bold}")

    coords, target_shape, reusable = get_subject_mni_transform(dataset_dir, subject)
    parcel_matrix = get_mni_parcel_matrix(target_shape, atlas_maps, number_of_regions)

    processed_volumes = 0

    for occurrence in occurrences.itertuples(index=False):
        start_volume = int(occurrence.start_vol)
        end_volume = int(occurrence.end_vol)
        n_vols = int(occurrence.n_vols)

        if start_volume < 0 or end_volume > source_bold_image.shape[3] or end_volume <= start_volume:
            raise ValueError(f"Invalid crop [{start_volume}:{end_volume}] for {source_bold}")

        if end_volume - start_volume != n_vols:
            raise ValueError(f"Expected {n_vols} volumes for {source_bold}, got {end_volume - start_volume}")

        cropped_bold_data = np.asarray(
            source_bold_image.dataobj[..., start_volume:end_volume],
            dtype=np.float32,
        )

        mapped_bold_data = map_occurrence_to_mni(
            cropped_bold_data,
            coords,
            target_shape,
            reusable,
            interptype,
            badval,
        )

        # Same reduction as libraries.fmri_processing.extract_parcels, applied to the
        # in-memory MNI data instead of a NIfTI written to and re-read from disk.
        parcel_time_series = (parcel_matrix @ mapped_bold_data.reshape(-1, n_vols)).T.astype(np.float32)

        if parcel_time_series.shape != (n_vols, number_of_regions):
            raise ValueError(f"Unexpected parcel time-series shape {parcel_time_series.shape} for {source_bold} [{start_volume}:{end_volume}]")

        parcel_time_series_file = Path(occurrence.parcel_time_series)
        parcel_time_series_file.parent.mkdir(parents=True, exist_ok=True)
        np.save(parcel_time_series_file, parcel_time_series)

        processed_volumes += n_vols

    return len(occurrences), processed_volumes

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--dataset_dir", required=True)
    parser.add_argument("--interpolation", default="cubic")
    parser.add_argument("--number_of_regions", type=int, required=True)
    parser.add_argument("--number_of_yeo_networks", type=int, required=True)
    parser.add_argument("--atlas_dir", required=True)
    parser.add_argument("--jobs", type=int, default=1)
    arguments = parser.parse_args()

    parcel_manifest = pd.read_csv(arguments.manifest, sep="\t")

    required_columns = {
        "subject",
        "stimulus_id",
        "repetition",
        "source_bold",
        "start_vol",
        "end_vol",
        "n_vols",
        "parcel_time_series",
    }

    missing_columns = required_columns - set(parcel_manifest.columns)

    if missing_columns:
        raise ValueError(f"Parcel manifest is missing columns: {sorted(missing_columns)}")

    if parcel_manifest.empty:
        raise ValueError(f"Parcel manifest is empty: {arguments.manifest}")

    duplicated_outputs = parcel_manifest[parcel_manifest["parcel_time_series"].duplicated(keep=False)]

    if not duplicated_outputs.empty:
        raise ValueError("Parcel manifest contains duplicated parcel output paths")

    # Fetched once here (downloading it on first use) so worker processes only ever load it from disk.
    atlas = datasets.fetch_atlas_schaefer_2018(
        n_rois=arguments.number_of_regions,
        data_dir=arguments.atlas_dir,
        yeo_networks=arguments.number_of_yeo_networks,
    )
    atlas_maps = str(atlas.maps)

    # Each occurrence (a single presentation of a stimulus to a subject) is its own
    # independent fMRI observation and is cropped, mapped to MNI space and reduced to
    # parcels on its own, rather than concatenated with other presentations into one
    # continuous time series. Occurrences are grouped by their source run file to avoid
    # reloading the same BOLD run from disk more than once, and the groups are the unit of
    # work handed out to worker processes (sorted by subject so a worker's groups share,
    # and reuse, the same cached transform as much as possible).
    groups = sorted(
        parcel_manifest.groupby(["subject", "source_bold"], sort=False),
        key=lambda group: group[0][0],
    )

    group_arguments = [
        (arguments.dataset_dir, int(subject), source_bold, occurrences, arguments.interpolation, 0, atlas_maps, arguments.number_of_regions)
        for (subject, source_bold), occurrences in groups
    ]

    if arguments.jobs <= 1:
        for process_group_arguments in group_arguments:
            n_occurrences, n_volumes = process_group(*process_group_arguments)
            print(f"subject {process_group_arguments[1]:02d} {process_group_arguments[2]}: {n_occurrences} occurrences ({n_volumes} volumes) mapped to MNI parcels")
    else:
        with ProcessPoolExecutor(max_workers=arguments.jobs) as executor:
            futures = {
                executor.submit(process_group, *process_group_arguments): process_group_arguments
                for process_group_arguments in group_arguments
            }

            for future in as_completed(futures):
                process_group_arguments = futures[future]
                n_occurrences, n_volumes = future.result()
                print(f"subject {process_group_arguments[1]:02d} {process_group_arguments[2]}: {n_occurrences} occurrences ({n_volumes} volumes) mapped to MNI parcels")

if __name__ == "__main__":
    main()
