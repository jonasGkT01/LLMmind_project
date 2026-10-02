# 2026-10-02 — Caption Scene registered to MNI (TODO S31); repeats averaged before the ISC (TODO S10)

## Changes

### S10: leave-one-subject-out ISC for NSD and Caption Scene

- `workflow/libraries/fmri_processing.py`: new `average_repeats_by_subject(arrays, subjects)`
  (time-point-wise mean of each subject's repeats, subjects in sorted order);
  `compute_isc_from_files()` gains `subjects = None` and, when given, averages the repeats before
  `compute_leave_one_out_isc()`, requiring at least two subjects.
- `compute_nsd_isc.py` passes the ISC manifest's `subject` column; `compute_caption_scene_isc.py`
  takes `--subjects` (parallel to `--parcel_ts`), filled by the Snakefile from the events manifest.
- Comments about "not purely within-subject" ISCs removed from `make_nsd_manifest.py` and
  `make_caption_scene_manifest.py`.

### S31: Caption Scene warped to MNI152NLin6Asym in the workflow

- New rules in `workflow/dataset_processing/caption_scene_dataset/Snakefile`:
  - `fetch_mni_template`: downloads `tpl-MNI152NLin6Asym_res-01_T1w.nii.gz` from TemplateFlow into
    `resources/atlases/`;
  - `register_caption_scene_t1w` (per subject, 8 threads): `antsRegistrationSyNQuick.sh -t s -e
    random_seed` of `config["caption_scene"]["t1w_pattern"]` (new key; `ses-01_run-001`) to the
    template. Keeps `sub-*_0GenericAffine.mat`, `sub-*_1Warp.nii.gz` and the QC plot
    `sub-*_t1w_to_mni_qc.png` (new script `plot_caption_scene_registration_qc.py`) in
    `results/mind/caption_scene/registration/`; the inverse warp and warped images are `temp()`;
  - `compute_caption_scene_sampling_coordinates` (per subject; new script
    `compute_caption_scene_sampling_coordinates.py`): checks that all runs share one BOLD grid,
    warps native index images (i, j, k) and a field-of-view mask onto the Schaefer atlas grid with
    `antsApplyTransforms` (linear), keeps the atlas voxels inside a parcel and fully inside the
    field of view, stops on an empty parcel, prints the per-parcel coverage, and writes
    `sub-*_sampling_coordinates.npz` (coordinates, labels, BOLD shape and affine);
  - `extract_caption_scene_run_parcels` (per run; `extract_caption_scene_parcels.py` rewritten):
    samples only the volumes inside the run's event windows at the coordinates with
    `scipy.ndimage.map_coordinates(order = 3)`, averages per parcel, cuts the windows and writes
    the per-event `.npy` files with unchanged names; a flag per run in
    `intermediate_files/parcel_flags/`;
  - `extract_caption_scene_parcels` now only collects the run flags into `.parcels_done`.
- Removed: `split_caption_scene_bold_by_run_manifest.py`, the `split_caption_scene_bold_by_run_manifest`
  rule, `caption_scene_split_done_files()` and the `output_bold` manifest column (with the
  `--output_root` argument of `make_caption_scene_manifest.py`); duplicate events are now detected by
  (stimulus, event index).
- `csd_events_manifest.tsv` moved to `results/mind/caption_scene/manifests/`, next to
  `isc_inputs.tsv`, so no cleanup of `intermediate_files/` removes the crop record. The per-run
  manifests stay: the extraction rule reads them.
- `fmri_processing.get_resampled_parcel_matrix()` refuses images with `sform_code` 0 or 1
  (`NATIVE_SFORM_CODES`); NSD's in-memory MNI image (2) and Narratives (3) pass.
- `caption_scene_dataset_processing_environment.yaml`: adds `ants=2.6.5` and
  `matplotlib-base=3.11.2`.

## Behaviour

All Caption Scene parcels, ISCs and everything downstream change; NSD ISCs and everything
downstream change. Both are part of the 2026-10-02 full recomputation. Extraction costs about 30 s
per run (cubic sampling of about 120 volumes), about 16 CPU-hours for the 1,664 runs, spread over
parallel jobs; registration about 2 min per subject. The old crops
(`intermediate_files/single_stimulus_bold/`, about 121 GB) and the old manifest copy in
`intermediate_files/manifest/` are no longer used.

## Verification (on the frontend, outputs in the scratchpad)

- The BOLD runs share one grid per subject; the four T1w scans per subject share one grid, and
  mutual information with the mean BOLD image is equal across them within 0.0005 (run-001 best for
  sub-01 and sub-05).
- All 8 registrations took about 1.5 min each; the QC plots show the template edges on the
  ventricles, corpus callosum and cortex of every subject.
- Sampling a mean BOLD image at the coordinates equals `antsApplyTransforms` of the same image
  within 1e-4 (mean 765). Every parcel of every subject lies fully inside the field of view.
- For one event, "warp + parcel average + cut" (the new script) equals "cut + ANTs B-spline warp +
  parcel average" within 8e-8 of the signal (correlation 1.000000).
- One stimulus seen 16 times by 8 subjects (COCO_train2014_000000002055): median ISC 0.098 with the
  old native-space parcellation, 0.168 after warping, 0.229 after also averaging repeats; the
  parcel-wise correlation between old and new ISC is 0.16. The command-line script gives the same
  values.
- NSD, 40 stimuli (22.6 presentations of 8 subjects on average): median ISC 0.043 → 0.047 with
  repeat averaging; parcel-wise correlation 0.83.
- `snakemake -n` parses the workflow; a targeted dry run resolves `fetch_mni_template` →
  `register_caption_scene_t1w` → `compute_caption_scene_sampling_coordinates` →
  `extract_caption_scene_run_parcels` with the expected commands.

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-02, Claude Opus 5.5: written for TODO entries S10 and S31 (approved by the developer on 2026-09-30), implemented when the developer asked to go on with S10 and S31.*
- *Files changed: `workflow/libraries/fmri_processing.py`, `workflow/dataset_processing/caption_scene_dataset/{Snakefile, envs/caption_scene_dataset_processing_environment.yaml, scripts/*}`, `workflow/dataset_processing/nsd_data_dataset/scripts/{compute_nsd_isc.py, make_nsd_manifest.py}`, `config/config.yaml`, `README.md`, `docs/reference/fmri_preprocessing.md`.*
- *Review status: not yet reviewed by the developer.*
