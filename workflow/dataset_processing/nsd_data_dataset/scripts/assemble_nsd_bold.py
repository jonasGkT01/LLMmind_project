import argparse
import tempfile

from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
from nsdcode.nsd_mapdata import NSDmapdata

NSD_MAP_SOURCE_SPACE = "func1pt8"
NSD_MAP_TARGET_SPACE = "MNI"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--dataset_dir", required=True)
    parser.add_argument("--interpolation", default="cubic")
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

    nsd_mapper = NSDmapdata(arguments.dataset_dir)

    # Each occurrence (a single presentation of a stimulus to a subject) is its own
    # independent fMRI observation and is cropped and mapped to MNI space on its own,
    # rather than concatenated with other presentations into one continuous time series.
    # Occurrences are grouped by their source run file only to avoid reloading the same
    # BOLD run from disk more than once.
    for (subject, source_bold), source_occurrences in occurrence_manifest.groupby(["subject", "source_bold"], sort=False):
        source_bold_image = nib.load(str(source_bold))

        if source_bold_image.ndim != 4:
            raise ValueError(f"Expected a 4D BOLD image, got shape {source_bold_image.shape}: {source_bold}")

        for occurrence in source_occurrences.itertuples(index=False):
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

            with tempfile.TemporaryDirectory(prefix="nsd_map_") as temporary_directory:
                native_bold_file = (
                    Path(temporary_directory)
                    / f"sub-{int(subject):02d}_task-{occurrence.stimulus_id}_rep-{int(occurrence.repetition):02d}_func1pt8.nii.gz"
                )

                native_bold_image = nib.Nifti1Image(
                    cropped_bold_data,
                    source_bold_image.affine,
                    header=source_bold_image.header.copy(),
                )

                native_bold_image.header.set_data_dtype(np.float32)
                native_bold_image.header.set_data_shape(cropped_bold_data.shape)
                nib.save(native_bold_image, native_bold_file)

                nsd_mapper.fit(
                    int(subject),
                    NSD_MAP_SOURCE_SPACE,
                    NSD_MAP_TARGET_SPACE,
                    str(native_bold_file),
                    interptype=arguments.interpolation,
                    badval=0,
                    outputfile=str(output_bold_file),
                )

            mapped_bold_image = nib.load(str(output_bold_file))

            if mapped_bold_image.ndim != 4 or mapped_bold_image.shape[3] != cropped_bold_data.shape[3]:
                raise ValueError(f"Unexpected mapped output shape {mapped_bold_image.shape}: {output_bold_file}")

            print(
                f"{occurrence.stimulus_id} subject {int(subject):02d} repetition {int(occurrence.repetition)}: "
                f"{cropped_bold_data.shape[3]} volumes mapped to MNI"
            )

if __name__ == "__main__":
    main()
