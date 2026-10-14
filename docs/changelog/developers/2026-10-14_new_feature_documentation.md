# 2026-10-14 — developer changelog

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../../AI_USAGE.md).*

Changes made on this day, in order:

- `docs/AI_USAGE.md` no longer lists the TODO and SUGGESTIONS files (documentation)
- Leftover outputs found and deleted; guide's leftover list extended (documentation)
- Brain-model analyses on a language and a visual brain region (new_feature, documentation)

---

## 12:13 — `docs/AI_USAGE.md` no longer lists the TODO and SUGGESTIONS files

Kind: documentation

The table in `docs/AI_USAGE.md` listed `../.claude/TODO/LLMmind_project.md` and
`../.claude/SUGGESTIONS/LLMmind_project.md`, which live in `LLMmind/.claude/`, outside the
project folder. Both rows and the sentence introducing them were removed; the table now lists only
files inside `LLMmind_project/`. The TODO and SUGGESTIONS files keep a one-line AI note under their
title, now without a link to `docs/AI_USAGE.md`. The rule in `LLMmind/.claude/CLAUDE.md`
(sections 1, 3 and 6) was changed to match.

### Context

- Request: the developer noted that `AI_USAGE.md` tracked files in `.claude/`, which is outside the
  project, and asked to stop doing so and remove those rows.
- Files changed: `docs/AI_USAGE.md`. Outside the project: `LLMmind/.claude/CLAUDE.md`,
  `LLMmind/.claude/TODO/LLMmind_project.md`, `LLMmind/.claude/TODO/public_datasets.md` (old
  end-of-file attribution block replaced by the one-line note),
  `LLMmind/.claude/SUGGESTIONS/LLMmind_project.md`.
- Verified: `grep` finds no reference to `.claude/`, `TODO/` or `SUGGESTIONS/` in any
  `AI_USAGE.md`.

---

## 15:15 — Leftover outputs found and deleted; guide's leftover list extended

Kind: documentation

No code changed. Files that the current workflow neither writes nor reads were found and deleted
from the working copy (113,075 files):

- `results/mind/nsd_data/parcels/task-*/sub-<NN>_task-*_parcel_ts.npy` (4,120 files, old naming
  without `_rep-<NN>`; the NSD Snakefile only builds `sub-<NN>_rep-<NN>_...` paths);
- `results/mind/*/isc_reliability.tsv`, `results/mind/all_isc_reliability.tsv` and
  `results/mind/caption_scene/manifests/isc_manifest.tsv` (ISC reliability and
  `write_caption_scene_isc_manifest` removed on 2026-10-08);
- `results/mind/narratives/qc/task-*_length_check.json` (18 files, no longer written since
  2026-10-01) and the emptied `qc/` folder;
- 108,882 `.snakemake/metadata/` records and 31 `.snakemake/incomplete/` markers whose decoded
  path does not exist (metadata 810 MB → 286 MB), and the stray `.snakemake/shell_tmp.zo22n4sq/`
  of a killed run;
- `workflow/libraries/__pycache__/*.cpython-312.pyc` and `*.cpython-313.pyc` (all environments
  run Python 3.14).

Kept after checking: all seven `.snakemake/conda/` environments (all listed by
`--list-conda-envs`), all 38 model folders (all in `config.yaml`), all atlas files, and
`.snakemake/log/`. `snakemake --list-untracked` also reported about 60,000 Caption Scene and NSD
files (parcels, ISC, registration, `by_run`, `parcel_flags`) because it does not follow the
checkpoint rules; each pattern was matched to a current rule and kept.

`docs/guides/running_and_troubleshooting.md`, "Leftover outputs from older versions", now lists
these file kinds.

### Context

- Request: find the files the project no longer needs or produces, list them in a temporary
  file and delete them with it.
- Files changed: `docs/guides/running_and_troubleshooting.md`; data files deleted as listed above.
- Verified: candidates from `snakemake --nolock --list-untracked` and from base64-decoding the
  `.snakemake/` records, each checked with `grep` against the Snakefiles and scripts and against
  the changelogs; every listed path was a regular file and none remained after `rm`; the
  developer's dry run afterwards planned no job.

---

## 15:35 — Brain-model analyses on a language and a visual brain region

Kind: new_feature, documentation

Every brain-model analysis (alignment scores, relabelling null, empirical and hypergeometric
p-values, Spearman alignment, summary TSVs, the brain-model plots) now also runs on the region of
the model's modality, next to the whole cortex. Whole-cortex results are unchanged and not rerun.

- `config/config.yaml`: new `atlas: regions:` with two lists of 1-based Schaefer label IDs keyed by
  stimulus type: `vision` (29 parcels of the 7-network `Vis` network, labels 1–14 and 101–115) and
  `language` (17 parcels of the Kong 2022 `Language` and `Aud` networks, matched to our parcels by
  vertex identity on fsaverage). Each ID carries its parcel name as a comment.
- New rule `extract_region_isc_dataframe` (`workflow/isc_nearest_neighbours/Snakefile`) and new
  script `workflow/isc_nearest_neighbours/scripts/extract_region_isc_dataframe.py`: reads
  `results/mind/{dataset}/isc_dataframe.parquet`, keeps columns `ID - 1` of
  `config["atlas"]["regions"][stimuli_type]` (the stimulus type of the output path), and writes
  `results/{stimuli_type}_mind/{dataset}/isc_dataframe.parquet` with the same index and layout.
  Validates the vector length (`--n_rois`) and the IDs. The values are copied, not recomputed.
- `compute_isc_nearest_neighbours`: paths `results/mind/` → `results/{mind}/`, so it also writes
  the region neighbours. `create_isc_dataframe` is unchanged.
- `workflow/Snakefile`: `REGION_SUFFIXES` (`""`, `_vision`, `_language`), global
  `wildcard_constraints` for `region_suffix` (may be empty) and `mind`, and three helpers:
  `in_region()`, `pairings_in()` and `mind_dir()`. `mind_dir()` returns `results/mind` for the
  empty suffix, `results/{stimuli_type}_mind` when the suffix matches the job's `stimuli_type`,
  and raises a `ValueError` otherwise. `rule all` loops the brain-model targets over
  `REGION_SUFFIXES`.
- `llm_mind_alignment/Snakefile`, `spearman_alignment/Snakefile`: brain inputs built with
  `mind_dir()`; `{region_suffix}` appended to `alignment_scores`, `spearman_alignment_scores` and
  the two summary TSV names; aggregation inputs and `all_*` targets through `pairings_in()`. The
  duplicate `SPEARMAN_PAIRINGS` in `spearman_alignment/Snakefile` (identical to the one in
  `workflow/Snakefile`) was removed.
- `visualisation/Snakefile`: the eight brain-model plot rules read and write
  `{region_suffix}`-suffixed paths (plot folders `results/pictures/<folder>{region_suffix}/`);
  `plot_alignment_heatmap` and `plot_empirical_p_value_heatmap` are unchanged and whole-cortex
  only, because `model_level_significance()` needs a brain p-value for every model of the
  model-model results.
- No existing script and no `shell:` command changed; for whole-cortex jobs the resolved paths,
  params and commands are those of before.
- Documentation: new `docs/reference/brain_regions.md`; `docs/reference/statistics.md` section 5
  (region families); `docs/guides/running_and_troubleshooting.md` section 3 (`atlas: regions`);
  README (index, `isc_nearest_neighbours/` module, outputs).

### Context

- Request: SUGGESTIONS I12/IS12 (developer's idea of 2026-10-13, design refined with the
  developer and approved on 2026-10-14), implemented on request the same day.
- Files changed: `config/config.yaml`, `workflow/Snakefile`,
  `workflow/isc_nearest_neighbours/Snakefile`,
  `workflow/isc_nearest_neighbours/scripts/extract_region_isc_dataframe.py` (new),
  `workflow/llm_mind_alignment/Snakefile`, `workflow/spearman_alignment/Snakefile`,
  `workflow/visualisation/Snakefile`, `README.md`, `docs/reference/brain_regions.md` (new),
  `docs/reference/statistics.md`, `docs/guides/running_and_troubleshooting.md`, `docs/AI_USAGE.md`.
- Verified:
  - the Kong-to-Schaefer mapping on fsaverage (every 7-network parcel 100% inside one Kong parcel;
    annotation order equal to the label order of
    `Schaefer2018_200Parcels_7Networks_order.txt`);
  - all four `isc_dataframe.parquet` are 200-value float32 vectors without NaN;
  - the script on Caption Scene (language): 1000 × 17, same index, values equal to the
    whole-cortex columns `ID - 1`; duplicate IDs refused;
  - `compute_isc_nearest_neighbours.py` in its own environment on the Narratives language ISC:
    three neighbour files of 18 × 5 rows;
  - `snakemake --use-conda -n`: 2625 jobs, all writing region paths only (0 whole-cortex outputs):
    5 extractions, 5 neighbour jobs, 612 score jobs (360 language, 252 vision), 612 + 612 p-value
    jobs, 300 relabelling, 300 Spearman, 2 + 2 aggregations, 155 plots;
  - a hand-requested mismatched target
    (`results/alignment_scores_language/dataset-caption_scene_model-clip_b-vision_brain_...`)
    fails with `ValueError: Results with suffix '_language' cannot use vision models`;
  - an explicitly constrained empty wildcard works in Snakemake 9.27 (scratch test).
