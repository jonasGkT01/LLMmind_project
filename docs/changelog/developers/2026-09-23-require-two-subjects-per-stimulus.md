# 2026-09-23 — Require ≥2 distinct subjects per stimulus; NSD parcels extracted in memory; excluded-stimuli file drives both brain and model sides

## Summary

Before this change, a stimulus was retained whenever it had ≥2 fMRI
observations in total (see `2026-09-21-nsd-observation-level-isc.md`). As a
result, most NSD and Caption Scene "ISC" values were within-subject
test-retest correlations:

- NSD: 65,216 of 66,216 retained stimuli came from a single subject.
- Caption Scene: 7,920 of 8,920 retained stimuli came from a single subject.

A stimulus is now retained only if it was presented to **≥2 distinct
subjects**. Every presentation is still its own observation in the
leave-one-out ISC, including repeats by the same subject; that part is
unchanged.

Expected retained counts, from the current manifests:

| Dataset | Retained | Previously | Subjects per retained stimulus |
|---|---|---|---|
| NSD | 1,000 | 66,216 | 907 × 8, 23 × 6, 70 × 4 |
| NSD presentations | 21,118 | 208,650 | — |
| Caption Scene | 1,000 | 8,920 | all 8 subjects |

## Changes

### Filters

- `nsd_data_dataset/scripts/make_nsd_manifest.py`
  - Retention now counts distinct subjects (`subject_counts_by_stimulus`)
    instead of total observations.
  - `excluded_stimuli.txt` lists every presented-but-not-retained image.
  - Removed the `output_bold` column and the `--output_root` argument; both
    existed only to name the MNI NIfTIs, which are no longer written.
  - The warning now reports a count rather than printing all 65k IDs.
- `caption_scene_dataset/scripts/make_caption_scene_manifest.py`
  - Retention uses `groupby("stimulus_id")["subject"].nunique() >= 2`.
  - The existing `excluded_stimuli` computation (All_images_480 minus
    retained) and the run manifests already derive from the filtered
    manifest. Dropped stimuli are therefore never split, parcellated or
    ISC'd.
- `narratives_dataset/Snakefile`
  - `NARRATIVES_TASK_GROUPS` keeps only tasks whose scans come from ≥2
    distinct subjects. All 18 current tasks pass.
  - `parcel_outputs_for_task` uses `.get(task, [])`, so a dropped task no
    longer raises `KeyError` at parse time.
  - `write_narratives_problematic_stimuli` now writes
    `problematic_subtasks ∪ (transcript stems − retained tasks)`. It depends
    on the renamed-transcripts dir (`NARRATIVES_STIMULI_READY`) and has the
    retained task list as a param, so it reruns whenever that set changes.
- Nature Stories: unchanged. `compute_nature_stories_isc.py` already
  requires all `expected_subjects` for every story.

### NSD: `assemble_nsd_bold` now writes parcel time series

- `scripts/assemble_nsd_bold.py`
  - Each occurrence is mapped func1pt8→MNI exactly as before.
  - It is then reduced to Schaefer parcels in memory, via
    `libraries.fmri_processing.get_resampled_parcel_matrix` with the atlas
    resampled onto the nsdcode MNI grid (`nsd_mni_affine()` reproduces the
    affine `nsd_write_vol` used to write).
  - Only the `(n_vols, n_rois)` float32 arrays are written, at the existing
    `parcel_time_series` paths.
  - Previous output size: about 117–237 MB per occurrence, roughly 24 TB for
    the old manifest. New output: 2.4 KB per occurrence.
  - Mapping now happens in float32 instead of float64. The old path wrote
    float64 NIfTIs that `extract_parcels` read back as float32 anyway.
- `scripts/extract_nsd_parcels.py` and rule `extract_nsd_parcels`: removed.
- `Snakefile`
  - `write_nsd_parcel_manifest` now carries
    `source_bold/start_vol/end_vol/n_vols` instead of `bold_file`.
  - `assemble_nsd_bold` takes the parcel manifest, adds the atlas params and
    outputs `.parcels_done`.
  - `NSD_BOLD_DONE` is removed.
- Verified on `sub-03_task-nsd-00001_rep-01`:
  - the new in-memory parcels vs `extract_parcels` on the old MNI NIfTI give
    a maximum absolute difference of `0.0`;
  - the affine matches the old file's.

### Excluded-stimuli file as the single source of truth

- `get_embeddings.py` already skipped every stem listed in
  `config[dataset]["excluded_stimuli"]`, and `get_embeddings` already
  declared that file as an input. Neither was changed.
- `isc_nearest_neighbours/scripts/create_isc_manifest.py` (and its
  checkpoint) now takes `--excluded_stimuli` and drops ISC files for listed
  stimuli.
  - Without this, stale per-stimulus ISC files from earlier runs would be
    globbed back in. Caption Scene's `compute_caption_scene_isc` outputs are
    per-file, so Snakemake never deletes them.
  - Those stale files would then clash with the embeddings
    (`compute_alignment_scores` raises on differing concept sets).

## Follow-ups

- `results/mind/nsd_data/single_stimulus_bold_mni/` (1.8 TB) is orphaned
  and safe to delete. Stale per-stimulus files under
  `results/mind/{nsd_data,caption_scene}/parcels/` and
  `results/mind/caption_scene/isc/` are no longer read. The same is true of
  the dropped stimuli's files under
  `results/mind/caption_scene/intermediate_files/single_stimulus_bold/`.
- `number_of_neighbours` must be ≤ N−1 (about 999) for NSD and Caption
  Scene.

## Rerunning

The changed filters live in Python scripts that are called from `shell:`
rules. Snakemake's code-change trigger does not look at those scripts, so it
will not rerun the manifest steps by itself. Force them:

```bash
snakemake --use-conda --cores <N> --forcerun make_nsd_manifest make_caption_scene_manifest
```

Everything downstream is then rebuilt from the new manifests.

## Verification performed

- `python -m py_compile` on every modified script.
- A `snakemake -n` dry run: the DAG resolves with the new NSD rule chain
  `make_nsd_manifest → write_nsd_parcel_manifest → assemble_nsd_bold →
  write_nsd_isc_manifest → compute_nsd_isc`, with no `extract_nsd_parcels`.
  The unchanged Narratives ISC outputs are not rescheduled, which confirms
  all 18 tasks pass the filter.
- A numerical check of the new in-memory NSD parcel extraction against the
  old NIfTI-based path on one existing presentation (see above).
- `create_isc_manifest.py` run on the real 8,920-file Caption Scene ISC
  directory with a 3-stimulus exclusion list: 8,917 rows were written and
  none of the excluded stimuli appeared.
- Retained-stimulus counts were computed from the manifests already on disk
  (from before this change).

**Not verified:** no pipeline stage was actually executed with the new code.
In particular, `make_nsd_manifest`, `make_caption_scene_manifest` and a full
`assemble_nsd_bold` run have not been run yet.

---

*AI disclosure: this changelog entry, together with the code changes it
describes and the related README edits, was written by an AI coding
assistant.*

- *Tool: Claude Code (Anthropic), VS Code extension.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`, 1M-token context).*
- *Date: 2026-09-23.*
- *Basis: a review of the whole repository earlier in the same session, then
  explicit instructions from the developer (Jonas Salvalaggio) on which
  changes to make.*
- *Verification: limited to the checks listed under "Verification
  performed".*
- *Review status: not yet reviewed by the developer at the time of writing.
  Review it before committing.*
