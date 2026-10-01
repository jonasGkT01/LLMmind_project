# 2026-10-01 — The Narratives Snakefile no longer writes files at parse time

## Change

`workflow/dataset_processing/narratives_dataset/Snakefile` ran two blocks at module level, i.e. on
every Snakemake command, dry runs and `--list-rules` included:

- **Length check (TODO S28):** `narratives_write_length_check_json()` wrote
  `results/mind/narratives/qc/task-*_length_check.json` (18 files) for every valid task. No rule
  declared them and nothing read them. Deleted: the function, its module-level call, the
  commented-out variants, and `import numpy as np`, which only it used (`json` and `Path` are still
  used). The useful part, which files are truncated and from which length, is now printed into the
  `compute_narratives_isc` job log by `compute_isc_from_files(..., truncate_to_shortest = True)`
  (see `2026-10-01_1513_shared_isc_input_validation.md`).
- **Excluded-scans JSON (TODO S32):** a loop collected the 44 scans of tasks outside
  `VALID_NARRATIVES_TASKS` with a reason and wrote them to
  `config["narratives"]["excluded_scans_for_task"]`, a file in `resources/`. Nothing read it, and
  its content follows from `config.yaml` (`tasks`, `schema_subtasks`, `notthefall_variants`).
  Deleted: the loop, the write and the `excluded_scans_for_task` key in `config/config.yaml`.
  `excluded_stimuli.txt`, which `get_embeddings.py` reads, is built by its own rule and is unchanged.

The existing files (`results/mind/narratives/qc/`, `resources/datasets/narratives_dataset/excluded_scans_for_task.json`)
are deleted when this change is merged into `main`. No rule changes, so nothing reruns.

`docs/reference/fmri_preprocessing.md`, step 5, now states why truncating Narratives to the shortest
run is safe.

## Verification

A dry run (`snakemake -n --quiet rules`) of the changed workflow parsed without errors, planned no
ISC or relabelling job, and left the modification times of both JSON files unchanged.

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-01, Claude Opus 5.5: written for TODO entries S28 and S32, approved by the developer on 2026-09-30; the implementation plan was approved on 2026-10-01 ("go on with S6, S7, S28, and S32").*
- *Files changed: `workflow/dataset_processing/narratives_dataset/Snakefile`, `config/config.yaml`, `docs/reference/fmri_preprocessing.md`.*
- *Review status: not yet reviewed by the developer.*
