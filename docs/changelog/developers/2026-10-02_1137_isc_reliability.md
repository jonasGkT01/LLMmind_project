# 2026-10-02 — Split-half reliability of the ISC vectors (TODO S30); Caption Scene parcel names fixed

## Changes

### ISC reliability (S30)

- New `workflow/libraries/compute_isc.py`: the ISC functions moved out of `fmri_processing.py`
  (`CONSTANT_SIGNAL_RTOL`, `is_constant_signal()`, `compute_leave_one_out_isc()`,
  `average_repeats_by_subject()`, `compute_isc_from_files()`, `single_value()`), so they can run in
  the ISC environment, which has no nibabel/nilearn. `fmri_processing.py` keeps the parcel
  extraction. New: `load_isc_inputs()` (loading, truncation and repeat averaging, split out of
  `compute_isc_from_files()`, which now wraps it) and `compute_split_half_isc_reliability(data,
  number_of_splits, rng)` (mean Pearson r between the leave-one-out ISC vectors of two random
  halves of the subjects; NaN below 4 subjects). The four `compute_*_isc.py` scripts import from
  `compute_isc`.
- New scripts in `workflow/isc_nearest_neighbours/scripts/`: `compute_isc_reliability.py` (one row
  per stimulus: subjects, time points, split-half r, Spearman-Brown r; one
  `default_rng(random_seed)` stream over the stimuli in sorted order) and
  `aggregate_isc_reliability.py` (one row per dataset: number of stimuli with and without a value,
  median time points, median and quartiles of both reliabilities, median |ISC| and share of
  |ISC| ≥ 0.9 from `isc_dataframe.parquet`).
- `workflow/isc_nearest_neighbours/Snakefile`: `ISC_MANIFEST_LAYOUT` (stimulus and parcel columns,
  truncation, per dataset), rules `compute_isc_reliability` (wildcard `dataset`, input
  `{processing_output_dir}/manifests/isc_manifest.tsv` and the ISC flag) and
  `aggregate_isc_reliability` (`results/mind/all_isc_reliability.tsv`, added to `rule all` and
  `all_isc_nearest_neighbours`).
- Caption Scene Snakefile: new rule `write_caption_scene_isc_manifest` (`run:`) writes
  `manifests/isc_manifest.tsv` (`stimulus_id | subject | parcel_ts`), like the other datasets;
  `caption_scene_parcel_path(row)` factored out of `caption_scene_parcel_paths()`.
- `config/config.yaml`: `isc_reliability_number_of_splits: 100`.

### Caption Scene parcel file names (fix to the S31 code of the same day)

`read_manifest()` in the Caption Scene Snakefile read `subject`, `session` and `run` as integers
and turned them back into unpadded strings (`sub-1_ses-13_run-50`), while the rewritten
`extract_caption_scene_parcels.py` reads them as text and writes zero-padded names
(`sub-01_ses-13_run-050`). Every `compute_caption_scene_isc` job would have looked for missing
files. `read_manifest()` now reads those columns (and `event_index`, `stimulus_id`) as text
(`CAPTION_SCENE_TEXT_COLUMNS`), and the extraction script reads `event_index` as text too; for all
15,900 events the Snakefile and the script now build identical paths.

## Behaviour

Adds four per-dataset TSVs and one summary TSV; no existing result changes because of S30.

## Verification

- With the ISC environment (no nibabel): reliability computed on the existing parcel files of all
  four datasets (NSD 1000, Caption Scene 1000, Narratives 18, Nature Stories 11 stimuli; about 6
  minutes in parallel): median Spearman-Brown r 0.966 (Narratives), 0.864 (Nature Stories), 0.025
  (NSD), 0.011 (Caption Scene, old misregistered parcels); the summary table was written.
- `snakemake -n results/mind/all_isc_reliability.tsv` plans `write_caption_scene_isc_manifest`, four
  `compute_isc_reliability` jobs and `aggregate_isc_reliability` with the expected inputs.
- Parcel paths: Snakefile (`read_manifest()` + `caption_scene_parcel_path()`) and
  `extract_caption_scene_parcels.parcel_output_path()` agree for all 15,900 events.

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-02, Claude Opus 5.5: written for TODO entry S30 (approved by the developer on 2026-09-30), implemented when the developer asked to proceed with S30; the parcel-name fix was found by the S30 test.*
- *Files changed: `workflow/libraries/{compute_isc,fmri_processing}.py`, `workflow/isc_nearest_neighbours/{Snakefile, scripts/compute_isc_reliability.py, scripts/aggregate_isc_reliability.py}`, `workflow/dataset_processing/*/scripts/compute_*_isc.py`, `workflow/dataset_processing/caption_scene_dataset/{Snakefile, scripts/extract_caption_scene_parcels.py}`, `workflow/Snakefile`, `config/config.yaml`, `README.md`, `docs/reference/fmri_preprocessing.md`.*
- *Review status: not yet reviewed by the developer.*
