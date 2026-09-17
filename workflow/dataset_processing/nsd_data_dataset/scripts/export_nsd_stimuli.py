import argparse

from pathlib import Path

import h5py
import numpy as np
import pandas as pd
from PIL import Image

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stimulus_manifest", required=True)
    parser.add_argument("--stimuli_hdf5", required=True)
    parser.add_argument("--output_dir", required=True)
    arguments = parser.parse_args()

    stimulus_manifest = pd.read_csv(arguments.stimulus_manifest, sep="\t")

    required_columns = {
        "stimulus_id",
        "hdf5_index",
    }

    missing_columns = required_columns - set(stimulus_manifest.columns)

    if missing_columns:
        raise ValueError(f"Stimulus manifest is missing columns: {sorted(missing_columns)}")

    if stimulus_manifest.empty:
        raise ValueError(f"Stimulus manifest is empty: {arguments.stimulus_manifest}")

    if stimulus_manifest["stimulus_id"].duplicated().any():
        raise ValueError("Stimulus manifest contains duplicated stimulus identifiers")

    output_directory = Path(arguments.output_dir)
    output_directory.mkdir(parents=True, exist_ok=True)

    with h5py.File(arguments.stimuli_hdf5, "r") as stimulus_file:
        if "imgBrick" not in stimulus_file:
            raise KeyError(f"Dataset 'imgBrick' was not found in {arguments.stimuli_hdf5}")

        image_dataset = stimulus_file["imgBrick"]

        for manifest_row in stimulus_manifest.itertuples(index=False):
            image_index = int(manifest_row.hdf5_index)

            if image_index < 0 or image_index >= len(image_dataset):
                raise IndexError(f"HDF5 image index {image_index} is outside imgBrick with {len(image_dataset)} images")

            image_array = np.asarray(image_dataset[image_index])

            if image_array.ndim != 3 or image_array.shape[-1] != 3:
                raise ValueError(f"Expected an RGB image with shape (height, width, 3), got {image_array.shape}")

            image = Image.fromarray(image_array).convert("RGB")
            output_file = output_directory / f"{manifest_row.stimulus_id}.png"
            image.save(output_file)

    print(f"Exported {len(stimulus_manifest)} images")

if __name__ == "__main__":
    main()