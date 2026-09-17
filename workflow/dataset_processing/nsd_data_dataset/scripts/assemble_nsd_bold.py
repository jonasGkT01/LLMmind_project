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

    nsd_mapper = NSDmapdata(arguments.dataset_dir)

    for (subject, stimulus_identifier), stimulus_occurrences in occurrence_manifest.groupby(["subject", "stimulus_id"], sort=False):
        stimulus_occurrences = stimulus_occurrences.sort_values("repetition")
        output_bold_files = stimulus_occurrences["output_bold"].astype(str).unique()

        if len(output_bold_files) != 1:
            raise ValueError(f"Multiple output BOLD files found for subject {subject}, stimulus {stimulus_identifier}: {output_bold_files}")

        repetition_numbers = stimulus_occurrences["repetition"].astype(int).tolist()
        expected_repetition_numbers = list(range(1, len(stimulus_occurrences) + 1))

        if repetition_numbers != expected_repetition_numbers:
            raise ValueError(f"Unexpected repetition sequence for subject {subject}, stimulus {stimulus_identifier}: {repetition_numbers}")

        volumes_per_repetition_values = stimulus_occurrences["n_vols"].astype(int).unique()

        if len(volumes_per_repetition_values) != 1:
            raise ValueError(f"Multiple repetition lengths found for subject {subject}, stimulus {stimulus_identifier}: {volumes_per_repetition_values}")

        volumes_per_repetition = int(volumes_per_repetition_values[0])
        reference_bold_image = None
        cropped_bold_arrays = []

        for occurrence in stimulus_occurrences.itertuples(index=False):
            source_bold_image = nib.load(str(occurrence.source_bold))
            start_volume = int(occurrence.start_vol)
            end_volume = int(occurrence.end_vol)

            if source_bold_image.ndim != 4:
                raise ValueError(f"Expected a 4D BOLD image, got shape {source_bold_image.shape}: {occurrence.source_bold}")

            if start_volume < 0 or end_volume > source_bold_image.shape[3] or end_volume <= start_volume:
                raise ValueError(f"Invalid crop [{start_volume}:{end_volume}] for {occurrence.source_bold}")

            if end_volume - start_volume != volumes_per_repetition:
                raise ValueError(f"Expected {volumes_per_repetition} volumes for {occurrence.source_bold}, got {end_volume - start_volume}")

            if reference_bold_image is None:
                reference_bold_image = source_bold_image
            else:
                same_spatial_shape = reference_bold_image.shape[:3] == source_bold_image.shape[:3]
                same_affine = np.allclose(reference_bold_image.affine, source_bold_image.affine, atol=1e-5)

                if not same_spatial_shape or not same_affine:
                    raise ValueError(f"Functional geometry changed within subject {int(subject):02d}")

            cropped_bold_arrays.append(
                np.asarray(
                    source_bold_image.dataobj[..., start_volume:end_volume],
                    dtype=np.float32,
                )
            )

        assembled_bold_data = np.concatenate(cropped_bold_arrays, axis=3)
        expected_number_of_volumes = volumes_per_repetition * len(stimulus_occurrences)

        if assembled_bold_data.shape[3] != expected_number_of_volumes:
            raise ValueError(f"Expected {expected_number_of_volumes} assembled volumes for subject {subject}, stimulus {stimulus_identifier}, got {assembled_bold_data.shape[3]}")

        output_bold_file = Path(output_bold_files[0])
        output_bold_file.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(prefix="nsd_map_") as temporary_directory:
            native_bold_file = Path(temporary_directory) / f"sub-{int(subject):02d}_task-{stimulus_identifier}_func1pt8.nii.gz"

            native_bold_image = nib.Nifti1Image(
                assembled_bold_data,
                reference_bold_image.affine,
                header=reference_bold_image.header.copy(),
            )

            native_bold_image.header.set_data_dtype(np.float32)
            native_bold_image.header.set_data_shape(assembled_bold_data.shape)
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

        if mapped_bold_image.ndim != 4 or mapped_bold_image.shape[3] != assembled_bold_data.shape[3]:
            raise ValueError(f"Unexpected mapped output shape {mapped_bold_image.shape}: {output_bold_file}")

        print(f"{stimulus_identifier} subject {int(subject):02d}: {assembled_bold_data.shape[3]} volumes mapped to MNI")

if __name__ == "__main__":
    main()