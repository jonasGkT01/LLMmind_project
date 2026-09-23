import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import re
import warnings

import numpy as np
import pandas as pd

import nibabel as nib

NSD_FUNCTIONAL_SPACE_DIRECTORY = "func1pt8mm"

DESIGN_FILE_PATTERN = re.compile(r"design_session(?P<session>\d+)_run(?P<run>\d+)\.tsv$")
BOLD_FILE_PATTERN = re.compile(r"timeseries_session(?P<session>\d+)_run(?P<run>\d+)\.nii\.gz$")

def nsd_stimulus_identifier(nsd_image_identifier):
    return f"nsd-{int(nsd_image_identifier):05d}"

def write_lines(values, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        for value in sorted(set(values)):
            f.write(f"{value}\n")

def discover_subject_runs(dataset_directory, subject):
    functional_space_directory = dataset_directory / "nsddata_timeseries" / "ppdata" / f"subj{subject:02d}" / NSD_FUNCTIONAL_SPACE_DIRECTORY
    design_directory = functional_space_directory / "design"
    bold_directory = functional_space_directory / "timeseries"

    if not design_directory.is_dir():
        raise FileNotFoundError(f"Missing design directory: {design_directory}")

    if not bold_directory.is_dir():
        raise FileNotFoundError(f"Missing BOLD directory: {bold_directory}")

    design_files_by_run = {}
    bold_files_by_run = {}

    for design_file in sorted(design_directory.glob("design_session*_run*.tsv")):
        match = DESIGN_FILE_PATTERN.match(design_file.name)

        if match is None:
            continue

        run_identifier = (int(match["session"]), int(match["run"]))

        if run_identifier in design_files_by_run:
            raise ValueError(f"Duplicate design file for subject {subject}, session {run_identifier[0]}, run {run_identifier[1]}")

        design_files_by_run[run_identifier] = design_file

    for bold_file in sorted(bold_directory.glob("timeseries_session*_run*.nii.gz")):
        match = BOLD_FILE_PATTERN.match(bold_file.name)

        if match is None:
            continue

        run_identifier = (int(match["session"]), int(match["run"]))

        if run_identifier in bold_files_by_run:
            raise ValueError(f"Duplicate BOLD file for subject {subject}, session {run_identifier[0]}, run {run_identifier[1]}")

        bold_files_by_run[run_identifier] = bold_file

    design_runs = set(design_files_by_run)
    bold_runs = set(bold_files_by_run)

    runs_without_bold = sorted(design_runs - bold_runs)
    runs_without_design = sorted(bold_runs - design_runs)

    if runs_without_bold or runs_without_design:
        raise ValueError(f"Unmatched NSD runs for subject {subject}. Design files without BOLD files: {runs_without_bold}. BOLD files without design files: {runs_without_design}.")

    matched_runs = sorted(design_runs)

    if not matched_runs:
        raise ValueError(f"No matching design and BOLD runs found for subject {subject}")

    return [
        (session, run, design_files_by_run[(session, run)], bold_files_by_run[(session, run)])
        for session, run in matched_runs
    ]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset_dir", required=True)
    parser.add_argument("--subjects", nargs="+", type=int, required=True)
    parser.add_argument("--tr", type=float, required=True)
    parser.add_argument("--event_duration_s", type=float, required=True)
    parser.add_argument("--onset_shift_volumes", type=int, required=True)
    parser.add_argument("--output_manifest", required=True)
    parser.add_argument("--output_stimulus_manifest", required=True)
    parser.add_argument("--output_excluded_stimuli", required=True)
    parser.add_argument("--output_run_length_qc", required=True)
    parser.add_argument("--output_metadata", required=True)
    arguments = parser.parse_args()

    dataset_directory = Path(arguments.dataset_dir)

    if len(set(arguments.subjects)) != len(arguments.subjects):
        raise ValueError("Duplicate subject identifiers were provided")

    if any(subject < 1 for subject in arguments.subjects):
        raise ValueError("Subject identifiers must be positive integers")

    if arguments.tr <= 0:
        raise ValueError("TR must be positive")

    if arguments.event_duration_s <= 0:
        raise ValueError("Event duration must be positive")

    number_of_volumes_per_repetition = int(math.ceil(arguments.event_duration_s / arguments.tr))

    occurrences_by_subject = {}
    run_quality_control_rows = []

    for subject in arguments.subjects:
        occurrences_by_stimulus = defaultdict(list)

        for session, run, design_file, bold_file in discover_subject_runs(dataset_directory, subject):
            design_values = np.asarray(np.loadtxt(design_file, dtype=np.int64, ndmin=1)).reshape(-1)
            bold_image = nib.load(str(bold_file))

            if bold_image.ndim != 4:
                raise ValueError(f"Expected a 4D BOLD image, got shape {bold_image.shape}: {bold_file}")

            number_of_extra_bold_volumes = bold_image.shape[3] - len(design_values)

            if number_of_extra_bold_volumes not in {0, 1}:
                raise ValueError(f"Unexpected design/BOLD lengths for {bold_file}: {len(design_values)} design rows and {bold_image.shape[3]} BOLD volumes")

            stimulus_onset_indices = np.flatnonzero(design_values > 0)

            for onset_volume in stimulus_onset_indices:
                nsd_image_identifier = int(design_values[onset_volume])
                start_volume = int(onset_volume) + arguments.onset_shift_volumes
                end_volume = start_volume + number_of_volumes_per_repetition

                if start_volume < 0 or end_volume > bold_image.shape[3]:
                    raise ValueError(f"Crop [{start_volume}:{end_volume}] is outside {bold_file} with {bold_image.shape[3]} volumes")

                occurrences_by_stimulus[nsd_image_identifier].append(
                    {
                        "subject": subject,
                        "session": session,
                        "run": run,
                        "nsd_73k_id": nsd_image_identifier,
                        "stimulus_id": nsd_stimulus_identifier(nsd_image_identifier),
                        "onset_vol": int(onset_volume),
                        "start_vol": start_volume,
                        "end_vol": end_volume,
                        "n_vols": number_of_volumes_per_repetition,
                        "source_design": str(design_file),
                        "source_bold": str(bold_file),
                    }
                )

            run_quality_control_rows.append(
                {
                    "subject": subject,
                    "session": session,
                    "run": run,
                    "n_design_volumes": len(design_values),
                    "n_bold_volumes": bold_image.shape[3],
                    "n_extra_bold_volumes": number_of_extra_bold_volumes,
                    "n_stimulus_onsets": len(stimulus_onset_indices),
                }
            )

        for nsd_image_identifier in occurrences_by_stimulus:
            occurrences_by_stimulus[nsd_image_identifier].sort(
                key=lambda occurrence: (
                    occurrence["session"],
                    occurrence["run"],
                    occurrence["onset_vol"],
                )
            )

        occurrences_by_subject[subject] = occurrences_by_stimulus

    # Every presentation enters the image's ISC, but a stimulus is kept only if at least
    # two different subjects saw it (not necessarily equally often), so its ISC is not
    # purely within-subject.
    observation_counts_by_stimulus = defaultdict(int)
    subject_counts_by_stimulus = defaultdict(int)

    for subject in arguments.subjects:
        for nsd_image_identifier, occurrences in occurrences_by_subject[subject].items():
            observation_counts_by_stimulus[nsd_image_identifier] += len(occurrences)
            subject_counts_by_stimulus[nsd_image_identifier] += 1

    retained_nsd_image_identifiers = sorted(
        nsd_image_identifier
        for nsd_image_identifier, subject_count in subject_counts_by_stimulus.items()
        if subject_count >= 2
    )

    excluded_nsd_image_identifiers = sorted(
        nsd_image_identifier
        for nsd_image_identifier, subject_count in subject_counts_by_stimulus.items()
        if subject_count < 2
    )

    if not retained_nsd_image_identifiers:
        raise ValueError("No NSD image was presented to at least two different subjects")

    if excluded_nsd_image_identifiers:
        warnings.warn(
            f"Removing {len(excluded_nsd_image_identifiers)} NSD stimuli presented to fewer than two different subjects (listed in {arguments.output_excluded_stimuli})",
            RuntimeWarning,
        )

    occurrence_manifest_rows = []

    for subject in arguments.subjects:
        for nsd_image_identifier in retained_nsd_image_identifiers:
            subject_occurrences = occurrences_by_subject[subject].get(nsd_image_identifier, [])

            for repetition_number, occurrence in enumerate(subject_occurrences, start=1):
                occurrence_manifest_row = dict(occurrence)
                occurrence_manifest_row["repetition"] = repetition_number
                occurrence_manifest_rows.append(occurrence_manifest_row)

    occurrence_manifest = pd.DataFrame(occurrence_manifest_rows).sort_values(["nsd_73k_id", "subject", "repetition"])

    stimulus_manifest = pd.DataFrame(
        [
            {
                "stimulus_id": nsd_stimulus_identifier(nsd_image_identifier),
                "nsd_73k_id": nsd_image_identifier,
                "hdf5_index": nsd_image_identifier - 1,
                "n_subjects": len(arguments.subjects),
                "n_observations": observation_counts_by_stimulus[nsd_image_identifier],
                "n_subjects_represented": sum(
                    1
                    for subject in arguments.subjects
                    if nsd_image_identifier in occurrences_by_subject[subject]
                ),
                "volumes_per_repetition": number_of_volumes_per_repetition,
            }
            for nsd_image_identifier in retained_nsd_image_identifiers
        ]
    )

    occurrence_manifest_path = Path(arguments.output_manifest)
    stimulus_manifest_path = Path(arguments.output_stimulus_manifest)
    excluded_stimuli_path = Path(arguments.output_excluded_stimuli)
    run_length_quality_control_path = Path(arguments.output_run_length_qc)
    metadata_path = Path(arguments.output_metadata)

    for output_path in [
        occurrence_manifest_path,
        stimulus_manifest_path,
        excluded_stimuli_path,
        run_length_quality_control_path,
        metadata_path,
    ]:
        output_path.parent.mkdir(parents=True, exist_ok=True)

    occurrence_manifest.to_csv(occurrence_manifest_path, sep="\t", index=False)
    stimulus_manifest.to_csv(stimulus_manifest_path, sep="\t", index=False)
    write_lines(
        (nsd_stimulus_identifier(x) for x in excluded_nsd_image_identifiers),
        excluded_stimuli_path,
    )
    pd.DataFrame(run_quality_control_rows).to_csv(run_length_quality_control_path, sep="\t", index=False)

    metadata = {
        "subjects": arguments.subjects,
        "functional_space": NSD_FUNCTIONAL_SPACE_DIRECTORY,
        "tr": arguments.tr,
        "event_duration_s": arguments.event_duration_s,
        "onset_shift_volumes": arguments.onset_shift_volumes,
        "n_volumes_per_repetition": number_of_volumes_per_repetition,
        "n_retained_stimuli": len(retained_nsd_image_identifiers),
        "n_excluded_stimuli": len(excluded_nsd_image_identifiers),
        "n_manifest_rows": len(occurrence_manifest),
    }

    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True))

    print(f"Retained {len(retained_nsd_image_identifiers)} stimuli; wrote {len(occurrence_manifest)} occurrence rows")
    print(f"Excluded {len(excluded_nsd_image_identifiers)} stimuli presented to fewer than two different subjects")

if __name__ == "__main__":
    main()