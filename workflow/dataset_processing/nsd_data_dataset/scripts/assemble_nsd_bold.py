import argparse

from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd

from nsdcode.nsd_datalocation import nsd_datalocation
from nsdcode.parse_case import parse_case
from nsdcode.load_data import load_transform
from nsdcode.interp_wrapper import interp_wrapper
from nsdcode.nsd_output import nsd_write_vol

NSD_MAP_SOURCE_SPACE = "func1pt8"
NSD_MAP_TARGET_SPACE = "MNI"
NSD_MAP_OUTPUT_CLASS = np.float64
NSD_MNI_VOXEL_SIZE = 1
NSD_MNI_ORIGIN = np.asarray([183 - 91, 127, 73]) - 1

_subject_mni_transform_cache = {}

def get_subject_mni_transform(dataset_dir, subject):
    # NSDmapdata.fit() reloads the ~50MB func1pt8-to-MNI deformation field from disk
    # and rebuilds the flattened interpolation coordinates from it on every single
    # call, at a cost of several seconds. Since this only depends on the subject, and
    # this script calls the mapping once per stimulus occurrence (hundreds of
    # thousands of times across all subjects), that redundant reload dominates the
    # runtime. Loading and building it once per subject and reusing it here removes
    # that redundancy without changing the mapping itself.
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

    # In the case of the target being MNI, we write out LPI NIFTIs, so the first
    # (X) dimension must be flipped (see NSDmapdata.fit()'s docstring).
    return np.flip(mapped_bold_data, axis=0)

def process_group(dataset_dir, subject, source_bold, occurrences, interptype, badval):
    # Runs in a worker process when --jobs > 1: each worker keeps its own
    # get_subject_mni_transform cache, so a worker only pays the per-subject load
    # once across however many (subject, source_bold) groups it is assigned.
    source_bold_image = nib.load(str(source_bold))

    if source_bold_image.ndim != 4:
        raise ValueError(f"Expected a 4D BOLD image, got shape {source_bold_image.shape}: {source_bold}")

    coords, target_shape, reusable = get_subject_mni_transform(dataset_dir, subject)

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

        output_bold_file = Path(occurrence.output_bold)
        output_bold_file.parent.mkdir(parents=True, exist_ok=True)

        mapped_bold_data = map_occurrence_to_mni(
            cropped_bold_data,
            coords,
            target_shape,
            reusable,
            interptype,
            badval,
        )

        nsd_write_vol(
            mapped_bold_data,
            NSD_MNI_VOXEL_SIZE,
            str(output_bold_file),
            origin=NSD_MNI_ORIGIN,
        )

        mapped_bold_image = nib.load(str(output_bold_file))

        if mapped_bold_image.ndim != 4 or mapped_bold_image.shape[3] != cropped_bold_data.shape[3]:
            raise ValueError(f"Unexpected mapped output shape {mapped_bold_image.shape}: {output_bold_file}")

        processed_volumes += cropped_bold_data.shape[3]

    return len(occurrences), processed_volumes

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--dataset_dir", required=True)
    parser.add_argument("--interpolation", default="cubic")
    parser.add_argument("--jobs", type=int, default=1)
    arguments = parser.parse_args()

    occurrence_manifest = pd.read_csv(arguments.manifest, sep="\t")

    required_columns = {
        "subject",
        "stimulus_id",
        "repetition",
        "source_bold",
        "start_vol",
        "end_vol",
        "n_vols",
        "output_bold",
    }

    missing_columns = required_columns - set(occurrence_manifest.columns)

    if missing_columns:
        raise ValueError(f"Occurrence manifest is missing columns: {sorted(missing_columns)}")

    if occurrence_manifest.empty:
        raise ValueError(f"Occurrence manifest is empty: {arguments.manifest}")

    duplicated_outputs = occurrence_manifest[occurrence_manifest["output_bold"].duplicated(keep=False)]

    if not duplicated_outputs.empty:
        raise ValueError("Occurrence manifest contains duplicated output BOLD paths")

    # Each occurrence (a single presentation of a stimulus to a subject) is its own
    # independent fMRI observation and is cropped and mapped to MNI space on its own,
    # rather than concatenated with other presentations into one continuous time series.
    # Occurrences are grouped by their source run file to avoid reloading the same BOLD
    # run from disk more than once, and the groups are the unit of work handed out to
    # worker processes (sorted by subject so a worker's groups share, and reuse, the
    # same cached transform as much as possible).
    groups = sorted(
        occurrence_manifest.groupby(["subject", "source_bold"], sort=False),
        key=lambda group: group[0][0],
    )

    if arguments.jobs <= 1:
        for (subject, source_bold), occurrences in groups:
            n_occurrences, n_volumes = process_group(
                arguments.dataset_dir, int(subject), source_bold, occurrences, arguments.interpolation, 0
            )
            print(f"subject {int(subject):02d} {source_bold}: {n_occurrences} occurrences ({n_volumes} volumes) mapped to MNI")
    else:
        with ProcessPoolExecutor(max_workers=arguments.jobs) as executor:
            futures = {
                executor.submit(
                    process_group, arguments.dataset_dir, int(subject), source_bold, occurrences, arguments.interpolation, 0
                ): (subject, source_bold)
                for (subject, source_bold), occurrences in groups
            }

            for future in as_completed(futures):
                subject, source_bold = futures[future]
                n_occurrences, n_volumes = future.result()
                print(f"subject {int(subject):02d} {source_bold}: {n_occurrences} occurrences ({n_volumes} volumes) mapped to MNI")

if __name__ == "__main__":
    main()
