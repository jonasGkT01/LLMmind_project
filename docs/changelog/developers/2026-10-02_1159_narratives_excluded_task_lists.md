# 2026-10-02 — Narratives: excluded tasks derived from the two reason lists

## Changes

- `config/config.yaml`: `problematic_subtasks` removed. It repeated, by hand, the union of
  `schema_subtasks` and `notthefall_variants`, which had no reader since the parse-time JSON writer
  was removed on 2026-10-01 (TODO S28/S32). The two reason lists stay, each with its own comment.
- `workflow/dataset_processing/narratives_dataset/Snakefile`: new
  `NARRATIVES_PROBLEMATIC_SUBTASKS = schema_subtasks + notthefall_variants`, used by
  `narratives_task_is_excluded()` and by `write_narratives_problematic_stimuli`
  (`params.problematic_stimuli`).
- `docs/reference/fmri_preprocessing.md`, step 1: names the two keys.

## Behaviour

The excluded tasks are the same 10, in the same order, so `VALID_NARRATIVES_TASKS` and the rule's
params are unchanged; the list can no longer drift out of sync with its reasons.

## Verification

`schema_subtasks + notthefall_variants` equals the old `problematic_subtasks` element by element.
`snakemake -n resources/datasets/narratives_dataset/excluded_stimuli.txt` parses the workflow; the
rule's rerun reason is only the code change of the 2026-10-02 layout pass, and its entry in
`--list-params-changes` is the same with and without this change.

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-02, Claude Opus 5.5: written after the developer chose to keep the two reason lists separate and derive the exclusion list from them.*
- *Files changed: `config/config.yaml`, `workflow/dataset_processing/narratives_dataset/Snakefile`, `docs/reference/fmri_preprocessing.md`.*
- *Review status: not yet reviewed by the developer.*
