# 2026-09-24 — Minimum number of subjects per stimulus moved to `config.yaml`

## Summary

The rule "a stimulus is kept only if at least two different subjects saw
it" (see `2026-09-23-require-two-subjects-per-stimulus.md`) had `2`
hardcoded in three places. It is now read from a new top-level key in
`config/config.yaml`, placed next to `number_of_relabellings` and
`random_seed`:

```yaml
minimum_subjects_per_stimulus: 2
```

The default keeps the previous behaviour.

## Changes

- `workflow/Snakefile`: `MINIMUM_SUBJECTS_PER_STIMULUS = config["minimum_subjects_per_stimulus"]`.
- `dataset_processing/caption_scene_dataset/`
  - The `make_caption_scene_manifest` checkpoint passes it as a param.
  - `scripts/make_caption_scene_manifest.py` takes a new required
    `--minimum_subjects_per_stimulus`. It uses the value in the filter and
    in its warning and error messages.
- `dataset_processing/nsd_data_dataset/`
  - `make_nsd_manifest` passes it as a param.
  - `scripts/make_nsd_manifest.py` takes a new required
    `--minimum_subjects_per_stimulus`. It uses the value in the filter and
    the messages, and records it in the manifest metadata JSON.
- `dataset_processing/narratives_dataset/Snakefile`: the
  `NARRATIVES_TASK_GROUPS` filter uses `MINIMUM_SUBJECTS_PER_STIMULUS`.
- Nature Stories: unchanged. It already requires every subject for every
  story, which is stricter for any value up to its subject count (11).
- `README.md`: the two places describing the rule now name the key.

## Rerunning

The two manifest rules have new params, so Snakemake's params trigger
reruns them, and everything downstream follows. In the dry run for this
change they were already scheduled for a software-environment change.
With the default of `2` the outputs are identical.

## Verification

- `python3 -m py_compile` on both modified scripts.
- `snakemake -n --cores 8`: the DAG resolves.

---
*AI disclosure: this changelog entry, together with the code changes it
describes and the related README edits, was written by an AI coding
assistant.*

- *Tool: Claude Code (Anthropic), VS Code extension.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`, 1M-token context).*
- *Date: 2026-09-24.*
- *Basis: explicit instructions from the developer (Jonas Salvalaggio) in
  the same session. The developer chose the config key's location (next to
  `number_of_relabellings` and `random_seed`).*
- *Verification: limited to the checks listed under "Verification".*
- *Review status: not yet reviewed by the developer at the time of writing.
  Review it before committing.*
