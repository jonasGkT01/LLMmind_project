# 2026-10-02 — One filename parser, shared plotting helpers, null intervals, separate BH families

## Changes

### One filename parser (TODO S3)

- `workflow/libraries/path_metadata.py`: new `ALIGNMENT_PATH_PATTERN` and `parse_alignment_path()`
  parse every alignment filename (observed score `.parquet`, per-concept `.p_value.tsv`, all-k
  `-relabelled_common_neighbours.parquet`; LLM-brain and LLM-LLM). It returns `dataset`,
  `similarity_type`, `kind` (`"score"`, `"p_value"`, `"relabelled"`), `number_of_neighbours`
  (int; absent for relabelled files), `method` (p-value files only), and
  `model`/`stimuli_type` (LLM-brain) or `model_1`/`stimuli_type_1`/`model_2`/`stimuli_type_2`
  (LLM-LLM). One regex covers all three kinds (S3 proposed a second regex for the relabelled name;
  an alternation in the same regex is shorter). New `parse_isc_task_path()` with
  `ISC_TASK_PATTERN` (`fullmatch`). `relabelled_name_for_observed_path()` and `RELABELLED_SUFFIX`
  moved here from `compute_alignment_enrichment.py`.
- Deleted: `parse_llm_brain_alignment_score_path()`/`LLM_BRAIN_ALIGNMENT_SCORE_PATTERN`,
  `parse_llm_llm_path()` (`plot_alignment_heatmap.py`), both `parse_p_value_path()` and both
  `parse_relabelled_common_neighbours_path()` (the two aggregation scripts),
  `infer_task_from_isc_path()` (`create_isc_manifest.py`), `extract_task_from_filename()` and
  `TASK_PATTERN` (`create_isc_dataframe.py`).
- `workflow/libraries/aggregate_alignment_scores.py`: `collect_paths_by_key(paths, key_columns,
  file_description, kind, method = None)` parses with `parse_alignment_path()` and checks `kind`
  and `method`; `aggregate_all_p_value_outputs()` loses its `parse_p_value_path` and
  `parse_relabelled_common_neighbours_path` arguments. `validate_canonical_pair_order()` in
  `aggregate_all_llm_llm_p_value_outputs.py` uses `parse_alignment_path()`.

### Shared plotting helpers (TODO S2)

- `workflow/libraries/compute_alignment.py`: new `read_alignment_scores(path, dataset,
  similarity_type, number_of_neighbours)` parses and checks the filename (kind `"score"`, dataset,
  similarity, k), reads `concept`/`alignment_score`, rejects duplicated concepts and scores
  outside [0, 1], and returns `(df, metadata, k/(n - 1))`. It replaces
  `read_alignment_score_summary()` (lineplot), `read_model_alignment_scores()` (concept
  scatterplot), `read_alignment_score()` (alignment heatmap) and
  `read_validated_alignment_scores()` (`compute_alignment_enrichment.py`). New
  `common_hypergeometric_expectation()` replaces the three copies of the "one expectation across
  files" check.
- `workflow/libraries/compute_statistics.py`: new `model_level_significance(labels,
  statistics_path, dataset, similarity_type, number_of_neighbours)` returns `(p_values, q_values)`
  in label order. It now requires the plotted models to equal the models with p-values in the
  TSV for that configuration (before, only missing models were an error), so a Benjamini-Hochberg
  family can no longer be computed over an incomplete model set.
- `workflow/libraries/manage_model_metadata.py`: new `sort_models(df, parameters_by_model)` and
  `sorted_pairwise_labels(model_metadata, parameters_by_model)` replace the per-script sorting.
- `workflow/libraries/visualisation_utils.py`:
  - new `create_model_figure()`, `style_model_axes()` (ticks, x-limits, grid, tick colours,
    family annotations, significance asterisks, labels, title with `TITLE_PAD`, legend),
    `save_figure(fig, output_path, model_figure = True)` (`FIGURE_DPI`, `MODEL_FIGURE_MARGINS`,
    `bbox_inches = "tight"` for every figure), `add_null_line()` (`NULL_LINE_STYLE`),
    `add_null_interval()`, `plot_concept_distributions()` (`CONCEPT_POINT_SIZE`, `JITTER_WIDTH`,
    `BOX_WIDTH`, `BOXPLOT_LINE_STYLE`), `set_alignment_score_y_axis()` and
    `plot_pairwise_heatmap()`;
  - deleted `style_model_x_axis()`, `save_model_figure()`, `model_figure_width()` and
    `NULL_STANDARD_DEVIATION`;
  - `deterministic_jitter()` lost `width`, `mark_degenerate_boxplot_statistics()` lost `marker`,
    `color`, `markersize` and `zorder`, `plot_model_points()` lost `x` and accepts
    `errors = None`.
- `spearman_ylim()` and `enrichment_ylim()` lost their never-changed parameters; they are now the
  constants `SPEARMAN_Y_PADDING`, `SPEARMAN_Y_MINIMUM_LIMIT`, `SPEARMAN_Y_STEP` and
  `ENRICHMENT_Y_PADDING`.
- The seven scripts in `workflow/visualisation/scripts/` were rewritten on these helpers. The
  eight `output_path.parent.mkdir(...)` calls are gone (Snakemake creates output directories).
  Model-figure x-limits are now set on every model figure (before, only on the scatterplots and
  enrichment line plot).

### Null intervals instead of null-SD error bars (TODO S4, option a)

- The model-level enrichment line plot and the model-level Spearman plot draw the observed points
  without error bars, and at each model a grey interval reference ± null SD
  (`add_null_interval()`, legend "Null ± 1 SD") on the reference line (enrichment = 1, ρ = 0).
  Their y-labels lose "± null SD".
- `compute_model_alignment_enrichment()` no longer computes the per-concept
  `null_standard_deviation`; its docstring explains the interval. `enrichment_ylim()` fits
  1 + null SD instead of enrichment + null SD.
- `plot_spearman_alignment.py` no longer requires the null-SD column in the concept-level TSVs.

### Heatmap validation and diagonal (TODO S13)

- `plot_alignment_heatmap.py` reads every LLM-brain and LLM-LLM file through
  `read_alignment_scores()`, so dataset, similarity and k are checked against the arguments.
  Self-cells stay NaN and are drawn blank (before: 1.0).

### Separate Benjamini-Hochberg families in the p-value heatmap (TODO S15)

- `plot_empirical_p_value_heatmap.py` corrects the brain-model cells with
  `model_level_significance()` (the family of the four brain-model plots) and the model-model
  cells as their own family; before, both were corrected together. `read_llm_brain_records()` was
  deleted.

### Documentation (TODO S16, S20, S15 item 3)

- New `docs/reference/2026-10-02_0925_statistics.md`; README updated (outputs, plot conventions,
  enrichment and Spearman paragraphs, redraw command now includes the two heatmap rules,
  documentation list).

## Behaviour

No shell command or Snakefile changed, so Snakemake reruns nothing by itself. Only figures change:
the two model-level plots with null intervals, the heatmap diagonals, tighter heatmap margins, and
q-value asterisks in the p-value heatmap where the separate families differ. Redraw them with the
README's `--forcerun` command.

## Verification

- `parse_alignment_path()` and `parse_isc_task_path()` parse every existing filename under
  `results/` (26,796 alignment files, 2,029 ISC files) exactly like the old parsers.
- `collect_paths_by_key()` builds the same key → path mappings as before for every input of both
  aggregations (768 + 768 + 300 LLM-brain, 11,184 + 11,184 + 4,038 LLM-LLM files), and the
  LLM-LLM pair-order check passes.
- `aggregate_all_p_value_outputs.py` rerun on all inputs: `all_model_brain_alignment_scores.tsv`
  is byte-identical to the current file. The LLM-LLM aggregation (51 min on node5) was not rerun;
  its only change is the parser, covered by the mapping check above.
- All 192 plot jobs (`snakemake -n -p --forcerun` commands, outputs redirected to the scratchpad)
  ran without errors and wrote all 204 PNGs. Every type was compared with the current figure.
  The brain-model q-value asterisks of the p-value heatmap were checked numerically against the
  brain-model plots' family.
- `py_compile` passes on every changed file; `create_isc_manifest.py`,
  `create_isc_dataframe.py` (run on 50 ISC files) and the LLM-LLM aggregation script start
  correctly.

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-02, Claude Opus 5.5: written for TODO entries S2, S3, S4, S13, S15, S16 and S20 (approved by the developer on 2026-09-30), implemented after the developer asked to do the TODO tasks that need no rerun.*
- *Files changed: `workflow/libraries/{path_metadata,compute_alignment,compute_alignment_enrichment,compute_statistics,manage_model_metadata,visualisation_utils,aggregate_alignment_scores}.py`, the seven scripts in `workflow/visualisation/scripts/`, `workflow/llm_mind_alignment/scripts/aggregate_all_p_value_outputs.py`, `workflow/llm_llm_alignment/scripts/aggregate_all_llm_llm_p_value_outputs.py`, `workflow/isc_nearest_neighbours/scripts/create_isc_{manifest,dataframe}.py`, `README.md`, `docs/reference/2026-10-02_0925_statistics.md`.*
- *Review status: not yet reviewed by the developer.*
