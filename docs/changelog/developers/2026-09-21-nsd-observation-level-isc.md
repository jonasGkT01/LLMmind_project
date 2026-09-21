# 2026-09-21 — NSD: drop dataset-specific repetition constraint, compute ISC from all available observations

## Summary

The NSD dataset-processing pipeline previously imposed an NSD-specific
inclusion rule that does not exist for any other dataset in the project: a
stimulus was retained only if **every** subject had seen it at least
`min_repetitions_per_subject` (3) times, and only the first
`repetitions_to_use` (3) repetitions per subject were used, concatenated
into one continuous BOLD time series per (subject, stimulus). This reduced
the ~1,000 images nominally shared across all 8 NSD subjects down to 515
retained stimuli, and the concatenation treated temporally distinct
presentations of the same image as if they were one continuous scan.

This change removes that constraint and brings NSD in line with the
`caption_scene` dataset's existing principle: a stimulus is usable whenever
there are at least two independent fMRI observations to compute ISC from
(`caption_scene_parcel_paths()` in
`workflow/dataset_processing/caption_scene_dataset/Snakefile` enforces
exactly this — `len(parcel_paths) < 2` is the only exclusion criterion).
For NSD, each presentation (occurrence) of an image, by any subject, is now
treated as one independent fMRI observation. A stimulus is excluded only
when it has fewer than two such observations in total, regardless of how
those observations are distributed across subjects.

## Changes

### `config/config.yaml`

- Removed `nsd_data.min_repetitions_per_subject` and
  `nsd_data.repetitions_to_use`. No replacement config key was added — the
  only remaining constraint (≥2 observations) is not a tunable parameter,
  it is the mathematical minimum for computing a leave-one-out correlation.

### `workflow/dataset_processing/nsd_data_dataset/scripts/make_nsd_manifest.py`

- Removed the `--min_repetitions_per_subject` / `--repetitions_to_use` CLI
  arguments and their validation.
- Replaced the per-subject eligibility intersection
  (`eligible_stimuli_per_subject` / `set.intersection(*...)`, which required
  *every* subject to individually clear the repetition floor) with a single
  pooled `observation_counts_by_stimulus` count summed across all subjects.
  A stimulus is retained iff `observation_counts_by_stimulus[id] >= 2`; this
  mirrors `make_caption_scene_manifest.py`'s
  `stimulus_counts = out.groupby("stimulus_id").size(); valid_stimuli =
  stimulus_counts[stimulus_counts >= 2].index` pattern exactly.
  Stimuli that fail this (i.e. exactly 0 or 1 observation across all
  subjects) are collected into `excluded_nsd_image_identifiers` and reported
  via `warnings.warn`, matching Caption Scene's `singleton_stimuli` warning.
- `--output_excluded_stimuli` now actually gets populated
  (`write_lines(...)`, a helper copied from Caption Scene's
  `make_caption_scene_manifest.py`) instead of always being written as an
  empty file.
- Manifest construction no longer slices `[:repetitions_to_use]` or asserts
  an exact repetition count per subject. For each retained stimulus, **all**
  of a subject's occurrences are used (a subject may contribute 0, 1, 2, or
  more), each assigned a sequential `repetition` number local to that
  subject/stimulus pair, and each written to its own `output_bold` path
  (`sub-{ss}_task-{stim}_rep-{NN}_bold.nii.gz`) instead of one shared path
  per (subject, stimulus) covering the concatenated repetitions.
- `stimulus_manifest` columns `repetitions_per_subject` and
  `volumes_per_subject_stimulus` (both assumed a fixed, uniform repetition
  count) were replaced with `n_observations` (total pooled observations for
  that stimulus) and `n_subjects_represented` (how many of the subjects
  contributed at least one observation) — both now genuinely variable
  per stimulus.
- `manifest_metadata.json` no longer contains
  `min_repetitions_per_subject` / `repetitions_to_use`; added
  `n_excluded_stimuli`.

### `workflow/dataset_processing/nsd_data_dataset/scripts/assemble_nsd_bold.py`

- **Behavioral change, not a refactor.** Previously grouped occurrences by
  `(subject, stimulus_id)`, asserted a single shared `output_bold` and a
  contiguous `1..N` repetition sequence, cropped each repetition, then
  `np.concatenate(cropped_bold_arrays, axis=3)`'d them into one array before
  a single `NSDmapdata.fit()` call per (subject, stimulus) mapped the
  concatenated array to MNI space.
- Now groups occurrences by `(subject, source_bold)` purely to avoid
  reloading the same run file from disk repeatedly. Each occurrence is
  cropped and passed through its own `NSDmapdata.fit()` call independently,
  writing directly to that occurrence's own `output_bold` path. There is no
  concatenation and no cross-occurrence array; the `reference_bold_image`
  geometry-consistency check across repetitions was removed because there
  is no longer a group of repetitions to check consistency across — each
  occurrence stands on its own.
- Cost implication: this increases the number of `NSDmapdata.fit()` calls
  (previously one per (subject, stimulus) covering all its repetitions in
  one call; now one per occurrence). This is the direct, expected cost of
  no longer requiring/relying on a fixed repetition count to produce
  equal-length concatenated series.

### `workflow/dataset_processing/nsd_data_dataset/Snakefile`

- `nsd_parcel_time_series_output(subject, stimulus_identifier)` →
  `nsd_parcel_time_series_output(subject, stimulus_identifier, repetition)`;
  output path now includes `rep-{NN}` so multiple observations from the
  same subject no longer collide on one file.
- `write_nsd_parcel_manifest()`: the uniqueness invariant it enforces moved
  from "at most one `output_bold` per `(subject, stimulus_id)`" (true under
  the old concatenate-then-map design) to "at most one `output_bold` per
  `(subject, stimulus_id, repetition)`" (true under the new
  one-file-per-occurrence design). Added `repetition` as a required/emitted
  column throughout.
- `write_nsd_isc_manifest()`: added `repetition` as an emitted column
  (informational; not required for the ISC computation itself) and sorts by
  `(subject, repetition)` instead of `subject` alone.
- `make_nsd_manifest` rule: dropped the `min_repetitions_per_subject` /
  `repetitions_to_use` params and the corresponding `--min_repetitions_per_subject`
  / `--repetitions_to_use` shell arguments.

### `workflow/dataset_processing/nsd_data_dataset/scripts/compute_nsd_isc.py`

- Removed the `stimulus_manifest["subject"].duplicated().any()` guard that
  rejected an ISC manifest containing more than one row for the same
  subject under a given stimulus. Under the new occurrence-level model this
  is expected and correct: a subject who saw a stimulus 3 times now
  contributes 3 independent rows/observations, exactly as `compute_caption_scene_isc.py`
  never restricted itself to one observation per subject either.
- `len(parcel_time_series_files) < 2` (unchanged) is now the *only*
  exclusion check at this stage — the same role it plays in
  `compute_caption_scene_isc.py`'s `compute_isc()`. It remains as a
  belt-and-suspenders check; the primary filter happens earlier in
  `make_nsd_manifest.py`.
- Log message wording changed from "N subjects" to "N observations" to
  reflect that the leave-one-out axis is now observations, not subjects.

### `workflow/dataset_processing/nsd_data_dataset/scripts/extract_nsd_parcels.py`

- No changes. It is already generic over whatever rows
  `write_nsd_parcel_manifest()` hands it (`bold_file` → `parcel_time_series`);
  the extra `repetition` column is simply ignored.

## Compatibility note

This changes both the *set* of retained NSD stimuli (more stimuli retained
— every stimulus with ≥2 total observations, rather than only ~515
stimuli meeting the old all-subjects-≥3-reps rule) and how each stimulus's
brain representation is derived (leave-one-out ISC over all raw
observations, rather than over one subject-level series built by
concatenating exactly 3 repetitions). `results/mind/nsd_data/` (occurrence
manifest, stimulus manifest, parcel time series, `single_stimulus_bold_mni/`,
ISC outputs) and `resources/datasets/nsd_data_dataset/excluded_stimuli.txt`
/ `.stimuli_ready` should all be regenerated from scratch — there is no
compatible partial-regeneration path given both the file-naming scheme
(`rep-{NN}` suffix) and the stimulus set changed.

Downstream consumers (`isc_nearest_neighbours`, `llm_mind_alignment`, etc.)
are unaffected at the interface level: they only depend on one
`task-{stimulus_id}_isc_mean.{npy,nii.gz}` file per retained stimulus and
one exported image per stimulus, both of which are still produced with the
same naming scheme.

## Verification

- `ast.parse()` on all four modified Python scripts — no syntax errors.
- `python3 -c "import yaml; yaml.safe_load(...)"` on `config/config.yaml` —
  parses cleanly after removing the two keys.
- Parsed the Snakefile's Python preamble (helper functions, before the
  first `rule`) with `ast.parse()` — no syntax errors. (The `rule` blocks
  themselves are Snakemake DSL, not plain Python, and were reviewed by
  inspection instead.)
- `grep -rn` across `*.py`, `*.yaml`, `Snakefile`, `*.md` for
  `min_repetitions_per_subject`, `repetitions_to_use`,
  `repetitions_per_subject`, `volumes_per_subject_stimulus` — no remaining
  references anywhere in the repo.
- Confirmed no code outside `dataset_processing/nsd_data_dataset/` reaches
  into NSD-specific manifest fields (`workflow/Snakefile` only does
  `include: "dataset_processing/nsd_data_dataset/Snakefile"`; the
  nearest-neighbour/alignment workflows were grepped for `nsd` and found to
  contain no dataset-specific branching).
- **Not run**: the pipeline was not executed end-to-end against real NSD
  data (requires the downloaded NSD dataset and is computationally
  expensive — one `NSDmapdata.fit()` call per occurrence). This should be
  smoke-tested against real data before relying on the outputs.

## Files touched

- `config/config.yaml`
- `workflow/dataset_processing/nsd_data_dataset/Snakefile`
- `workflow/dataset_processing/nsd_data_dataset/scripts/make_nsd_manifest.py`
- `workflow/dataset_processing/nsd_data_dataset/scripts/assemble_nsd_bold.py`
- `workflow/dataset_processing/nsd_data_dataset/scripts/compute_nsd_isc.py`
