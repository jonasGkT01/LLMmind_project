# 2026-10-14 — developer changelog

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../../AI_USAGE.md).*

Changes made on this day, in order:

- `docs/AI_USAGE.md` no longer lists the TODO and SUGGESTIONS files (documentation)
- Leftover outputs found and deleted; guide's leftover list extended (documentation)
- Brain-model analyses on a language and a visual brain region (new_feature, documentation)
- Summary tables moved to `results/tsv_summaries/` (new_feature, documentation)
- Unused `estimate_batch_size.py` and `valid_voxel_counts.tsv` removed (removal, documentation)
- More ticks and gridlines on narrow enrichment y-axes (bugfix, documentation)

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

---

## 17:45 — Summary tables moved to `results/tsv_summaries/`

Kind: new_feature, documentation

The seven summary TSVs (`all_model_brain_alignment_scores{,_language,_vision}.tsv`,
`all_model_model_alignment_scores.tsv`, `all_spearman_alignment_scores{,_language,_vision}.tsv`)
are now written to `results/tsv_summaries/`, named by the new constant
`TSV_SUMMARIES_DIR = "results/tsv_summaries"` in `workflow/Snakefile`.

- Outputs of `aggregate_all_p_value_outputs`, `aggregate_all_llm_llm_p_value_outputs` and
  `aggregate_all_spearman_alignment_scores`, the summary inputs of
  `plot_empirical_p_value_heatmap`, `plot_concept_alignment_scatterplot`,
  `plot_brain_model_alignment_lineplot`, `plot_concept_alignment_enrichment_scatterplot` and
  `plot_brain_model_alignment_enrichment_lineplot`, and the targets of `rule all`,
  `all_llm_mind_alignment`, `all_llm_llm_alignment` and `all_spearman_alignment` use
  `TSV_SUMMARIES_DIR`. No script changed (they take the paths as arguments); one comment in
  `libraries/compute_statistics.py` was updated.
- The existing seven files were moved with `mv` (content and modification times kept), so the
  aggregations do not rerun. The five plot rules above rerun once on the next run (252 jobs),
  through the `input` rerun trigger, because their recorded input path changed (developer's
  choice, instead of skipping the trigger).
- Documentation: README (outputs), `docs/guides/running_and_troubleshooting.md`,
  `docs/reference/statistics.md`, `docs/reference/brain_regions.md`.

### Context

- Request: save all TSV summaries in a folder `tsv_summaries/` and move the existing ones there.
- Files changed: `workflow/Snakefile`, `workflow/llm_mind_alignment/Snakefile`,
  `workflow/llm_llm_alignment/Snakefile`, `workflow/spearman_alignment/Snakefile`,
  `workflow/visualisation/Snakefile`, `workflow/libraries/compute_statistics.py` (comment),
  `README.md`, `docs/guides/running_and_troubleshooting.md`, `docs/reference/statistics.md`,
  `docs/reference/brain_regions.md`, `docs/AI_USAGE.md`; data: the seven TSVs moved.
- Verified: no Snakemake lock and no job of the user on node5 before the move; `grep` finds no
  `results/all_` left in the Snakefiles; `snakemake --use-conda -n` plans 252 plot jobs (the five
  rules above, reason "set of input files has changed") and nothing else.

---

## 18:20 — Unused `estimate_batch_size.py` and `valid_voxel_counts.tsv` removed

Kind: removal, documentation

- `workflow/libraries/estimate_batch_size.py` (`suggest_batch_size()`) deleted. It was added on
  2026-09-22 for a batched embedding loop that was never built: no script or Snakefile imports
  it and no config key or rule uses a `batch_size`.
- `extract_nature_stories_parcels.py` (`main`): the block writing `voxel_qc` to
  `valid_voxel_counts.tsv` next to `common_fsaverage_support.npy` was removed. The file was not a
  declared output of `extract_nature_stories_parcels` and nothing read it. The table is still
  printed (`Native-voxel QC:`); `compute_common_support()` is unchanged. The existing
  `results/mind/nature_stories/qc/valid_voxel_counts.tsv` was deleted.
- No job reruns: the rule calls the script from `shell:` and has no `code_version()` param, and
  no output changed.
- Documentation: `docs/guides/running_and_troubleshooting.md` lists `valid_voxel_counts.tsv`
  under "Leftover outputs from older versions"; `docs/AI_USAGE.md` row of
  `estimate_batch_size.py` removed.

### Context

- Request: TODO P1/S1 and P2/S2; the developer confirmed that neither file is still useful and
  asked to remove both.
- Files changed: `workflow/dataset_processing/nature_stories_dataset/scripts/extract_nature_stories_parcels.py`,
  `docs/guides/running_and_troubleshooting.md`, `docs/AI_USAGE.md`; deleted
  `workflow/libraries/estimate_batch_size.py` and
  `results/mind/nature_stories/qc/valid_voxel_counts.tsv`.
- Verified: `grep` finds no reference to `estimate_batch_size`, `suggest_batch_size`,
  `valid_voxel_counts` or `voxel_qc_output` left in `workflow/`; the edited script passes
  `python -m py_compile`.

---

## 18:50 — More ticks and gridlines on narrow enrichment y-axes

Kind: bugfix, documentation

- `libraries/compute_alignment_enrichment.py`: `set_enrichment_y_scale()` now sets the new
  `EnrichmentLocator` (a `matplotlib.ticker.Locator`) as the major locator instead of
  `FixedLocator(ENRICHMENT_Y_TICKS)`. At draw time it returns the `ENRICHMENT_Y_TICKS` inside the
  view interval when there are at least `ENRICHMENT_MIN_FIXED_TICKS = 4` of them, and otherwise
  `MaxNLocator(steps = [1, 2, 2.5, 5, 10]).tick_values(bottom, top)`. The steps exclude
  matplotlib's default 1.5 (and 3, 4, 6, 8), whose multiples can skip 1: a first test drew
  0.975, 0.99, 1.005, … with no label at the null value. Import `FixedLocator` replaced by `Locator`,
  `MaxNLocator`.
- Why: the gridlines (`style_model_axes()`, `ax.grid(axis = "y")`) sit on the major ticks. The
  model-level similarity-comparison enrichment plots fit their y-range to the data
  (`data_fitted_ylim()`), e.g. 0.97–1.05 on Caption Scene 125NN, where only the tick at 1 was in
  view and its gridline lay under the null line, so the scale could not be read.
- Plots whose range starts at 0 (concept- and model-level enrichment plots) contain at least
  0, 0.25, 0.5, 0.75 and 1, so their ticks are unchanged.
- Rerun: plot rules have no `code_version()` param, so nothing reruns by itself. Only
  `plot_similarity_comparison_enrichment_lineplot` draws differently; redraw it with
  `--forcerun plot_similarity_comparison_enrichment_lineplot`. Nothing upstream.
- Documentation: `docs/reference/statistics.md` (shared y-axes).

### Context

- Request: the developer found plots with only the reference line and at most one other
  horizontal line, unreadable in scale, and approved the proposed locator.
- Files changed: `workflow/libraries/compute_alignment_enrichment.py`,
  `docs/reference/statistics.md`, `docs/AI_USAGE.md`.
- Verified: tick labels drawn on test axes (0.962–1.07 → 0.98, 1, …, 1.06; 0.8–1.3 → 0.05
  steps; 0–1.6, 0.5–3, 1–30 and 0–300 → the fixed ticks as before); the Caption Scene 125NN
  language similarity-comparison enrichment plot redrawn into a scratch folder and inspected
  (five labelled gridlines instead of one). Steps below 1 are drawn about 2.3 times taller than
  above 1, which comes from the symlog scale and was already the case.
