# 2026-09-25 — What rebuilds when `minimum_subjects_per_stimulus` changes

## Summary

No code changes. This entry records an audit of how Snakemake's rerun
triggers propagate a change of `minimum_subjects_per_stimulus` (introduced in
`2026-09-24-configurable-minimum-subjects-per-stimulus.md`), with the valid
range of the key and one gap found in Narratives. The README has been updated
to match.

## How the value reaches each dataset

| Dataset | Where the value is used | Rerun trigger |
|---|---|---|
| `caption_scene` | `params.minimum_subjects_per_stimulus` of the `make_caption_scene_manifest` checkpoint | params |
| `nsd_data` | `params.minimum_subjects_per_stimulus` of `make_nsd_manifest` | params |
| `narratives` | Parse-time filter on `NARRATIVES_TASK_GROUPS` (`narratives_dataset/Snakefile`, lines 149-155) | Only through `params.retained_tasks` of `write_narratives_problematic_stimuli`, when the retained task set actually changes |
| `nature_stories` | Not used (every subject is required for every story) | — |

### Caption Scene and NSD

The params trigger (on by default in Snakemake ≥ 7.8; the project env has
9.21.0) reruns both manifest rules. From there every link is declared as an
input, so mtime propagates:

- `excluded_stimuli` (under `resources/datasets/…`) is an output of both
  manifest rules. It is an input of `get_embeddings` and `create_isc_manifest`.
  So **all model embeddings for these two datasets rerun too** (GPU), along
  with `compute_llm_nearest_neighbours` and all LLM–LLM alignments.
- Caption Scene: `split_*` → `extract_caption_scene_parcels` (re-touches
  `.parcels_done`) → per-stimulus `compute_caption_scene_isc`. These jobs sit
  behind the checkpoint, so they don't show up in a dry run until the new
  manifest exists.
- NSD: `write_nsd_parcel_manifest` → `assemble_nsd_bold` →
  `write_nsd_isc_manifest` → `compute_nsd_isc`. `export_nsd_stimuli` also
  reruns, because the stimulus manifest changed.
- Old ISC files for stimuli that are no longer kept stay in `isc/`.
  `create_isc_manifest.py` builds its list from the eligible stimuli, not by
  globbing, so it ignores them.

### Narratives — known gap

`write_narratives_parcel_manifest` and `write_narratives_isc_manifest` are
`run:` rules with no inputs, no params and unchanged code. Snakemake therefore
does not rebuild them when `NARRATIVES_TASK_GROUPS` changes:

- **Raising** the value so that a task is dropped: the excluded list,
  embeddings and `create_isc_manifest` update correctly. The stale manifests
  still list the dropped task, which costs extra compute but gives correct
  results.
- **Lowering** it again so that a task comes back: `compute_narratives_isc`
  expects an output for the returning task that the stale ISC manifest doesn't
  list. Expect a `MissingOutputException`. Workaround:
  `--forcerun write_narratives_parcel_manifest`.

In practice this only matters at values ≥ 15. The smallest retained task,
`lucy`, has 14 distinct subjects in the current parcel manifest (next are
`milkywaysynonyms` and `slumlordreach` with 17). A possible fix, not
implemented: add
`params: tasks=sorted(NARRATIVES_TASK_GROUPS)` to both manifest rules.

## Valid range

- **Lower bound 2.** ISC needs ≥ 2 observations:
  `caption_scene_parcel_paths()` (`caption_scene_dataset/Snakefile`) and
  `compute_nsd_isc.py` raise with fewer.
- **Practical upper bound 8** for Caption Scene and NSD (8 subjects each).
  Above that, both manifest scripts raise on an empty stimulus set.

## Verification

Dry runs with the project env (`snakemake -n --cores 8 --quiet rules`):

- `--rerun-triggers mtime params input code`, value 2 vs 3: 1,500 vs 7,454
  jobs. The difference is the two manifest rules, `export_nsd_stimuli`,
  `write_caption_scene_stimuli_transcripts`, the NSD manifest/parcel/ISC
  chain, 38 `get_embeddings` and 38 `compute_llm_nearest_neighbours` jobs,
  and 2,936 `compute_llm_llm_*` jobs each. No Narratives or Nature Stories
  rule is added.
- The 1,500 jobs at value 2 were already pending before this audit (for
  example `assemble_nsd_bold`).
- With the default triggers, the dry run also schedules
  `download_pretrained_llm`, `extract_narratives_parcels`,
  `extract_nature_stories_parcels` and `convert_nature_stories_textgrids`,
  because their software environment definitions changed. This is unrelated
  to the threshold.
- Narratives subject counts: distinct `sub-*` per task in
  `results/mind/narratives/manifests/parcel_extraction_manifest.tsv`.
- Not tested: an actual (non-dry) run with a changed value, and the
  Narratives lowering scenario (inferred from the rule definitions).

---
*AI disclosure: this changelog entry and the related README edits were
written by an AI coding assistant, based on its reading of the workflow code
and on the dry runs listed above.*

- *Tool: Claude Code (Anthropic), VS Code extension.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`, 1M-token context).*
- *Date: 2026-09-25.*
- *Basis: a question from the developer (Jonas Salvalaggio) in the same
  session: does changing `minimum_subjects_per_stimulus` rerun the project?
  The first answer in the session wrongly said Narratives doesn't use the
  key. This entry corrects that.*
- *Verification: limited to the checks listed under "Verification".*
- *Review status: not yet reviewed by the developer at the time of writing.
  Review it before committing.*
