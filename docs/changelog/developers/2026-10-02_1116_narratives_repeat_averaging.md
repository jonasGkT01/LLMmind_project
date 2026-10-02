# 2026-10-02 — Narratives: average a subject's repeated runs before the ISC

## Changes

- `workflow/dataset_processing/narratives_dataset/Snakefile`: `write_narratives_isc_manifest()`
  writes a `subject` column (`task | subject | parcel_ts | isc_npy`), looping over the scans of
  `NARRATIVES_TASK_GROUPS`; `parcel_outputs_for_task()`, its only user, is deleted. The comment on
  the task filter no longer says that every scan is its own observation.
- `compute_narratives_isc.py`: requires the `subject` column and passes it to
  `compute_isc_from_files(..., subjects = ..., truncate_to_shortest = True)`, so the runs are first
  truncated to the shortest one and then averaged per subject (the S10 helper).

Only `pieman` has repeats: 11 of its 75 subjects contribute two runs (86 scans). Before, each run
counted as a separate subject in the leave-one-out ISC.

## Behaviour

The `pieman` ISC and everything downstream of the Narratives ISC change; part of the 2026-10-02
full recomputation.

## Verification

On the existing parcel files, the old call reproduces the stored `pieman` ISC exactly; with
averaging the median ISC goes from 0.1246 to 0.1334 and the parcel-wise correlation with the old
ISC is 0.9989. The other 17 stories have one scan per subject and are unchanged.

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-02, Claude Opus 5.5: written after the developer asked to add the Narratives pieman repeats, found while implementing S10, to the batch.*
- *Files changed: `workflow/dataset_processing/narratives_dataset/Snakefile`, `workflow/dataset_processing/narratives_dataset/scripts/compute_narratives_isc.py`, `docs/reference/fmri_preprocessing.md`.*
- *Review status: not yet reviewed by the developer.*
