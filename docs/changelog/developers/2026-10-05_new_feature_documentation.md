# 2026-10-05 — developer changelog

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../../AI_USAGE.md).*

Changes made on this day, in order:

- Manifest and summary-table rules rerun when their code changes (new_feature)
- README: ISC description and module references corrected (documentation)

---

## 12:00 — Manifest and summary-table rules rerun when their code changes

Kind: `new_feature`

### Problem

The 2026-10-02 run failed in `compute_narratives_isc` with `Manifest is missing columns:
['subject']`. Commit `c1aabfa` had added the `subject` column to `write_narratives_isc_manifest()`,
but that function is defined outside the rule's `run:` block, and Snakemake's `code` rerun trigger
hashes only the `run:` block (and, for `shell:` rules, the command text, not the script it calls).
The rule's input and params were unchanged, so `isc_manifest.tsv` (dated 2026-06-19) was kept.

### Changes

- New `workflow/libraries/code_version.py`: `code_version(*items)` returns a SHA-256 of
  - each function's code object: `co_code`, `co_consts` (nested code objects recursively,
    frozensets sorted so the result does not depend on `PYTHONHASHSEED`) and `co_names`; line
    numbers and comments are left out, as in Snakemake's own `run:` hash;
  - each script path's bytes plus, recursively, every `workflow/libraries/` module it imports
    (`from libraries.<name> import`).
  `inspect.getsource()` is not used: it fails on functions defined in a Snakefile, because
  Snakemake executes a translated copy whose line numbers differ from the file
  (`OSError: lineno is out of bounds`).
- `workflow/Snakefile`: imports `code_version`; the included Snakefiles share its namespace.
- `params: code = code_version(...)` added to 13 rules:
  - helpers outside `run:`: `write_narratives_parcel_manifest` and `write_narratives_isc_manifest`
    (with `narratives_parcel_output`), `write_nature_stories_parcel_manifest` and
    `write_nature_stories_isc_manifest` (with `nature_stories_parcel_output`),
    `write_nsd_parcel_manifest` (with `nsd_parcel_time_series_output`), `write_nsd_isc_manifest`,
    `write_caption_scene_isc_manifest` (`read_manifest`, `caption_scene_parcel_path`);
  - scripts called from `shell:`: `make_nsd_manifest`, checkpoint `make_caption_scene_manifest`,
    `aggregate_all_spearman_alignment_scores`, `aggregate_all_llm_llm_p_value_outputs`,
    `aggregate_all_p_value_outputs`, `aggregate_isc_reliability`. Each script path is now a
    module-level constant (`MAKE_NSD_MANIFEST_SCRIPT`, `MAKE_CAPTION_SCENE_MANIFEST_SCRIPT`,
    `AGGREGATE_ALL_SPEARMAN_OUTPUTS_SCRIPT`, `AGGREGATE_ALL_LLM_LLM_P_VALUE_OUTPUTS_SCRIPT`,
    `AGGREGATE_ALL_P_VALUE_OUTPUTS_SCRIPT`, `AGGREGATE_ISC_RELIABILITY_SCRIPT`) used by both the
    param and the `shell:` command.

### Behaviour

- A change to the listed functions, scripts or imported libraries changes the `code` param, so the
  `params` trigger reruns the rule and, through the new output mtime, everything downstream.
  Comment-only edits do not.
- Not covered: changes to global data the helpers read (e.g. `NARRATIVES_TASK_GROUPS` built from
  `config.yaml`), helpers not listed in the param, and runs launched with
  `--rerun-triggers mtime`.
- One-time effect: the new param makes the 13 rules rerun once (the dry run reports "Params have
  changed … before: <nothing exclusive>"); this falls inside the S22 full recomputation, which
  already reruns every job.

### Verification

- `code_version()` gives the same hash under `PYTHONHASHSEED=1` and `2`, the same hash after
  adding comments and blank lines, and a different hash after adding a column to a header string.
- The aggregator script hash covers `aggregate_alignment_scores.py`, `compute_alignment.py`,
  `compute_statistics.py`, `manage_model_metadata.py` and `path_metadata.py`.
- `snakemake -n -p --nolock` (Snakemake 9.27.0) parses the workflow, renders the script paths in
  the commands, and schedules `make_nsd_manifest` for changed params.

### Context

- Request: Written after the developer asked why the 2026-10-02 run crashed and then asked that the rules producing manifests or collecting outputs always run; the approved solution reruns them when their code changes instead.
- Files changed: `workflow/libraries/code_version.py` (new), `workflow/Snakefile`, `workflow/dataset_processing/{caption_scene,narratives,nature_stories,nsd_data}_dataset/Snakefile`, `workflow/isc_nearest_neighbours/Snakefile`, `workflow/llm_llm_alignment/Snakefile`, `workflow/llm_mind_alignment/Snakefile`, `workflow/spearman_alignment/Snakefile`, `README.md`.

---

## 14:17 — README: ISC description and module references corrected

Kind: `documentation`

Documentation only; no code or result changes.

- `README.md`, inclusion rule: removed "every presentation (including repeats by the same subject)
  then counts as one fMRI observation in its ISC", outdated since the repeat averaging of
  2026-10-02 (`average_repeats_by_subject()`, called by `load_isc_inputs()` in
  `workflow/libraries/compute_isc.py` when `subjects` is given). The text now says each subject's
  repeats are averaged first. Narratives, NSD and Caption Scene pass `subjects`; Nature Stories does
  not, because `compute_nature_stories_isc.py` rejects duplicate subjects.
- `README.md`, overview: the leave-one-out ISC compares "each subject against the mean of the other
  subjects" (was "each observation").
- `README.md`: `is_constant_signal()` and the `compute_leave_one_out_isc` import of the code-layout
  example now point to `libraries/compute_isc.py` (were `libraries/fmri_processing.py`).

### Context

- Request: Written after the developer approved the README fix of TODO P39/S39 while reviewing the open TODO entries one at a time.
- Files changed: `README.md`.
