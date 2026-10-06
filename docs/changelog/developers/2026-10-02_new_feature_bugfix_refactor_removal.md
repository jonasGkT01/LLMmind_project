# 2026-10-02 — developer changelog

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../../AI_USAGE.md).*

Changes made on this day, in order:

- Alignment-score parquets: fixed row order, percentage column dropped (refactor, removal)
- One filename parser, shared plotting helpers, null intervals, separate BH families (refactor)
- Two unused leftovers removed (removal)
- One random stream for all relabelling permutations (TODO S17) (refactor)
- Project-wide layout pass (TODO S35) (refactor)
- Caption Scene registered to MNI (TODO S31); repeats averaged before the ISC (TODO S10) (new_feature, bugfix)
- Narratives: average a subject's repeated runs before the ISC (new_feature)
- Split-half reliability of the ISC vectors (TODO S30); Caption Scene parcel names fixed (new_feature, bugfix)
- Narratives: excluded tasks derived from the two reason lists (refactor)

---

## 08:27 — Alignment-score parquets: fixed row order, percentage column dropped

Kind: `refactor`, `removal`

### Changes

- `workflow/libraries/compute_alignment.py::compute_alignment_scores()`:
  - iterates over `sorted(nearest_neighbours_dict_1)` instead of `set(nearest_neighbours_dict_1)`
    (the local `concepts` is gone). A `set` of strings iterates in an order that depends on
    Python's per-process hash randomisation, so every run wrote the same rows in a different
    order. Rows are now always in concept order, and the parquets are byte-reproducible (TODO S38).
  - no longer writes `alignment_score_percentage` (`alignment_score × 100`), which nothing read
    (TODO S29 item 2). Output columns: `concept`, `common_neighbours`, `alignment_score`.

Affects the observed outputs of `compute_llm_mind_alignment_score` and
`compute_llm_llm_alignment_score`. No shell command changed, so nothing reruns; existing files keep
their old order and column until they are regenerated. No reader of these files depends on row
order or on the dropped column.

### Verification

One `compute_llm_mind_alignment_score` job (Caption Scene, `bloom_1b1`, cosine, k = 25) was run
twice in the scratchpad with the project's conda environment: the two parquets are byte-identical,
their concepts are sorted, and their content equals the current file once that is sorted by concept
and stripped of `alignment_score_percentage` (1000 rows).

### Context

- Request: Written for TODO entries S38 (approved by the developer on 2026-10-02) and S29 item 2 (approved on 2026-09-30), implemented together at the developer's request.
- Files changed: `workflow/libraries/compute_alignment.py`.

---

## 09:27 — One filename parser, shared plotting helpers, null intervals, separate BH families

Kind: `refactor`

### Changes

#### One filename parser (TODO S3)

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

#### Shared plotting helpers (TODO S2)

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

#### Null intervals instead of null-SD error bars (TODO S4, option a)

- The model-level enrichment line plot and the model-level Spearman plot draw the observed points
  without error bars, and at each model a grey interval reference ± null SD
  (`add_null_interval()`, legend "Null ± 1 SD") on the reference line (enrichment = 1, ρ = 0).
  Their y-labels lose "± null SD".
- `compute_model_alignment_enrichment()` no longer computes the per-concept
  `null_standard_deviation`; its docstring explains the interval. `enrichment_ylim()` fits
  1 + null SD instead of enrichment + null SD.
- `plot_spearman_alignment.py` no longer requires the null-SD column in the concept-level TSVs.

#### Heatmap validation and diagonal (TODO S13)

- `plot_alignment_heatmap.py` reads every LLM-brain and LLM-LLM file through
  `read_alignment_scores()`, so dataset, similarity and k are checked against the arguments.
  Self-cells stay NaN and are drawn blank (before: 1.0).

#### Separate Benjamini-Hochberg families in the p-value heatmap (TODO S15)

- `plot_empirical_p_value_heatmap.py` corrects the brain-model cells with
  `model_level_significance()` (the family of the four brain-model plots) and the model-model
  cells as their own family; before, both were corrected together. `read_llm_brain_records()` was
  deleted.

#### Documentation (TODO S16, S20, S15 item 3)

- New `docs/reference/statistics.md`; README updated (outputs, plot conventions,
  enrichment and Spearman paragraphs, redraw command now includes the two heatmap rules,
  documentation list).

### Behaviour

No shell command or Snakefile changed, so Snakemake reruns nothing by itself. Only figures change:
the two model-level plots with null intervals, the heatmap diagonals, tighter heatmap margins, and
q-value asterisks in the p-value heatmap where the separate families differ. Redraw them with the
README's `--forcerun` command.

### Verification

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

### Context

- Request: Written for TODO entries S2, S3, S4, S13, S15, S16 and S20 (approved by the developer on 2026-09-30), implemented after the developer asked to do the TODO tasks that need no rerun.
- Files changed: `workflow/libraries/{path_metadata,compute_alignment,compute_alignment_enrichment,compute_statistics,manage_model_metadata,visualisation_utils,aggregate_alignment_scores}.py`, the seven scripts in `workflow/visualisation/scripts/`, `workflow/llm_mind_alignment/scripts/aggregate_all_p_value_outputs.py`, `workflow/llm_llm_alignment/scripts/aggregate_all_llm_llm_p_value_outputs.py`, `workflow/isc_nearest_neighbours/scripts/create_isc_{manifest,dataframe}.py`, `README.md`, `docs/reference/statistics.md`.

---

## 09:31 — Two unused leftovers removed

Kind: `removal`

### Changes

- `workflow/libraries/compute_alignment.py`: deleted `compute_mean_alignment_score()`, which had
  no caller. `compute_common_neighbours()`, which it wrapped, stays: the relabelling
  (`compute_relabelled_alignment.py`) uses it.
- `workflow/libraries/compute_alignment_enrichment.py`: `compute_model_alignment_enrichment()`
  no longer puts `expected_alignment_score` in its per-model summary, which nothing read. The
  value is still computed and used as the enrichment denominator.

No output, figure or shell command changes; nothing reruns.

### Verification

`py_compile` passes on both files, and `plot_brain_model_alignment_enrichment_lineplot.py` runs on
Caption Scene, cosine, k = 25 (output in the scratchpad).

### Context

- Request: Written after the developer approved removing the two unused leftovers found during the S2/S3 refactor.
- Files changed: `workflow/libraries/compute_alignment.py`, `workflow/libraries/compute_alignment_enrichment.py`.

---

## 09:50 — One random stream for all relabelling permutations (TODO S17)

Kind: `refactor`

### Changes

- `workflow/libraries/compute_relabelled_alignment.py::compute_relabelled_common_neighbours_for_all_k()`:
  creates `rng = np.random.default_rng(random_seed)` once before the shuffle loop and draws every
  shuffle's permutation from it. Before, shuffle *i* used `default_rng(random_seed + i)`, so a
  replication run with a nearby seed reused almost all shuffles (seed 37 shuffle 1 was seed 38
  shuffle 0), and the alignment tests used different permutations from the Spearman null.
- `workflow/libraries/compute_statistics.py`: deleted `create_relabelling_rng()`, which had no
  other caller.
- `docs/reference/statistics.md`, section 2: describes the single stream.

### Behaviour

Every LLM-brain and LLM-LLM relabelling null changes, so all alignment p-values, the model-level
empirical p-values, the summary TSVs and the enrichment values change slightly. The Spearman
results do not change. The relabelling rules' shell commands are unchanged, so this change alone
would not trigger a rerun. It is merged together with S22, whose environment change reruns every
job, so the full recomputation picks it up.

Since every test draws only `permutation(number_of_concepts)` from `default_rng(random_seed)`, the
alignment and Spearman tests of a dataset now use exactly the same permutations.

### Verification

On synthetic neighbour arrays (40 concepts, k = 3 and 6, 25 shuffles, seed 37), the function's
common-neighbour counts equal those computed from permutations drawn in sequence from one
`default_rng(37)` stream.

### Context

- Request: Written for TODO entry S17 (approved by the developer on 2026-09-30), implemented when the developer asked to include S17 in the full recomputation.
- Files changed: `workflow/libraries/compute_relabelled_alignment.py`, `workflow/libraries/compute_statistics.py`, `docs/reference/statistics.md`.

---

## 10:21 — Project-wide layout pass (TODO S35)

Kind: `refactor`

### Changes

Every tracked code file (the 60 `.py` files under `workflow/`, the 11 Snakefiles,
`config/config.yaml`, `parquet2tsv.sh`) brought into line with section 4 of
`LLMmind/.claude/CLAUDE.md`. Layout and comments only; no name, logic, argument or output changed.

- **Python:** spaces around `=` (keyword arguments, defaults, assignments), `+`, `-` and
  comparisons; none around `*`, `/`, `**`; one space after every comma, including a comma that
  ends a line; no trailing whitespace otherwise. One blank line between top-level definitions, no
  blank line after a block header, blank lines around `if … raise` blocks and before a `return`
  that follows a multi-line block. Every code line ≤ 88 characters: hanging-indent calls (one
  argument per line), long strings split into adjacent literals, long signatures and
  `from … import` lines one name per line, conditions and right-hand sides wrapped in
  parentheses, docstrings reflowed. `argparse` calls in the 4d layout. Block comments in
  lowercase with no final full stop (proper names and acronyms kept). Imports in three groups;
  the separate third-party "domain" group of 9 scripts was merged into the third-party group.
- **Snakefiles:** the same spacing rules; every input and output named (all `rule all*` targets,
  `mark_*_isc_done`, `finish_caption_scene_isc`, `extract_*_parcels`, `assemble_nsd_bold`,
  `rename_narratives_stimuli_transcipts`, `write_narratives_problematic_stimuli`,
  `verify_nature_stories_stimuli`, `create_isc_dataframe` (`{input.isc_npys}`), `get_embeddings`
  (`{output.embeddings}`)); `threads: 4` split onto its own line; the one non-raw `shell:` block
  (`rename_narratives_stimuli_transcipts`, no backslashes) made `r"""`; `from itertools import
  combinations` moved to the top of `workflow/Snakefile`. The main Snakefile keeps its helpers
  before the `include:` lines (the included Snakefiles use them), so it cannot follow the strict
  configfile → include → rule all order of 4g.
- **`config/config.yaml`:** comments added above the keys that are not self-explanatory; values
  unchanged. `schema_subtasks` and `notthefall_variants` are documented as not read by the
  workflow.
- **`parquet2tsv.sh`:** `[[ … ]]` tests, quoted assignment, AI header.
- AI attribution header added to or updated in every file.
- `README.md`, "Code conventions": rewritten to summarise the CLAUDE.md rules (three import
  groups instead of the four documented before).

### Behaviour

Snakemake reruns the rules whose `shell:` text changed and the two `run:` rules whose code
changed (`write_narratives_problematic_stimuli`, `write_nature_stories_excluded_stimuli`; they
rewrite the same excluded-stimuli lists). This is merged before the full recomputation of
2026-10-02, which reruns every job anyway, so it costs nothing extra.

### Verification

- The Python AST of every `.py` file, with docstrings blanked, is identical to `main` before the
  pass (`ast.dump` comparison).
- No tabs, no trailing whitespace except after a line-ending comma, no two consecutive blank
  lines except before a section banner, no `.py` code line over 88 characters outside comments
  and `argparse` calls; `py_compile` passes on every file.
- `snakemake -n -p` (9.27.0) before and after: the same 40,957 jobs with the same outputs and, after
  normalising whitespace and line continuations, identical shell commands; the only additions
  are the two `run:` jobs above. `yaml.safe_load` of `config/config.yaml` is identical before and
  after. `bash -n parquet2tsv.sh` passes.

### Context

- Request: Written for TODO entry S35 (approved by the developer on 2026-10-01), done before the full recomputation at the developer's request.
- Files changed: every `.py` file under `workflow/`, every Snakefile, `config/config.yaml`, `parquet2tsv.sh`, `README.md`.

---

## 10:58 — Caption Scene registered to MNI (TODO S31); repeats averaged before the ISC (TODO S10)

Kind: `new_feature`, `bugfix`

### Changes

#### S10: leave-one-subject-out ISC for NSD and Caption Scene

- `workflow/libraries/fmri_processing.py`: new `average_repeats_by_subject(arrays, subjects)`
  (time-point-wise mean of each subject's repeats, subjects in sorted order);
  `compute_isc_from_files()` gains `subjects = None` and, when given, averages the repeats before
  `compute_leave_one_out_isc()`, requiring at least two subjects.
- `compute_nsd_isc.py` passes the ISC manifest's `subject` column; `compute_caption_scene_isc.py`
  takes `--subjects` (parallel to `--parcel_ts`), filled by the Snakefile from the events manifest.
- Comments about "not purely within-subject" ISCs removed from `make_nsd_manifest.py` and
  `make_caption_scene_manifest.py`.

#### S31: Caption Scene warped to MNI152NLin6Asym in the workflow

- New rules in `workflow/dataset_processing/caption_scene_dataset/Snakefile`:
  - `fetch_mni_template`: downloads `tpl-MNI152NLin6Asym_res-01_T1w.nii.gz` from TemplateFlow into
    `resources/atlases/`;
  - `register_caption_scene_t1w` (per subject, 8 threads): `antsRegistrationSyNQuick.sh -t s -e
    random_seed` of `config["caption_scene"]["t1w_pattern"]` (new key; `ses-01_run-001`) to the
    template. Keeps `sub-*_0GenericAffine.mat`, `sub-*_1Warp.nii.gz` and the QC plot
    `sub-*_t1w_to_mni_qc.png` (new script `plot_caption_scene_registration_qc.py`) in
    `results/mind/caption_scene/registration/`; the inverse warp and warped images are `temp()`;
  - `compute_caption_scene_sampling_coordinates` (per subject; new script
    `compute_caption_scene_sampling_coordinates.py`): checks that all runs share one BOLD grid,
    warps native index images (i, j, k) and a field-of-view mask onto the Schaefer atlas grid with
    `antsApplyTransforms` (linear), keeps the atlas voxels inside a parcel and fully inside the
    field of view, stops on an empty parcel, prints the per-parcel coverage, and writes
    `sub-*_sampling_coordinates.npz` (coordinates, labels, BOLD shape and affine);
  - `extract_caption_scene_run_parcels` (per run; `extract_caption_scene_parcels.py` rewritten):
    samples only the volumes inside the run's event windows at the coordinates with
    `scipy.ndimage.map_coordinates(order = 3)`, averages per parcel, cuts the windows and writes
    the per-event `.npy` files with unchanged names; a flag per run in
    `intermediate_files/parcel_flags/`;
  - `extract_caption_scene_parcels` now only collects the run flags into `.parcels_done`.
- Removed: `split_caption_scene_bold_by_run_manifest.py`, the `split_caption_scene_bold_by_run_manifest`
  rule, `caption_scene_split_done_files()` and the `output_bold` manifest column (with the
  `--output_root` argument of `make_caption_scene_manifest.py`); duplicate events are now detected by
  (stimulus, event index).
- `csd_events_manifest.tsv` moved to `results/mind/caption_scene/manifests/`, next to
  `isc_inputs.tsv`, so no cleanup of `intermediate_files/` removes the crop record. The per-run
  manifests stay: the extraction rule reads them.
- `fmri_processing.get_resampled_parcel_matrix()` refuses images with `sform_code` 0 or 1
  (`NATIVE_SFORM_CODES`); NSD's in-memory MNI image (2) and Narratives (3) pass.
- `caption_scene_dataset_processing_environment.yaml`: adds `ants=2.6.5` and
  `matplotlib-base=3.11.2`.

### Behaviour

All Caption Scene parcels, ISCs and everything downstream change; NSD ISCs and everything
downstream change. Both are part of the 2026-10-02 full recomputation. Extraction costs about 30 s
per run (cubic sampling of about 120 volumes), about 16 CPU-hours for the 1,664 runs, spread over
parallel jobs; registration about 2 min per subject. The old crops
(`intermediate_files/single_stimulus_bold/`, about 121 GB) and the old manifest copy in
`intermediate_files/manifest/` are no longer used.

### Verification (on the frontend, outputs in the scratchpad)

- The BOLD runs share one grid per subject; the four T1w scans per subject share one grid, and
  mutual information with the mean BOLD image is equal across them within 0.0005 (run-001 best for
  sub-01 and sub-05).
- All 8 registrations took about 1.5 min each; the QC plots show the template edges on the
  ventricles, corpus callosum and cortex of every subject.
- Sampling a mean BOLD image at the coordinates equals `antsApplyTransforms` of the same image
  within 1e-4 (mean 765). Every parcel of every subject lies fully inside the field of view.
- For one event, "warp + parcel average + cut" (the new script) equals "cut + ANTs B-spline warp +
  parcel average" within 8e-8 of the signal (correlation 1.000000).
- One stimulus seen 16 times by 8 subjects (COCO_train2014_000000002055): median ISC 0.098 with the
  old native-space parcellation, 0.168 after warping, 0.229 after also averaging repeats; the
  parcel-wise correlation between old and new ISC is 0.16. The command-line script gives the same
  values.
- NSD, 40 stimuli (22.6 presentations of 8 subjects on average): median ISC 0.043 → 0.047 with
  repeat averaging; parcel-wise correlation 0.83.
- `snakemake -n` parses the workflow; a targeted dry run resolves `fetch_mni_template` →
  `register_caption_scene_t1w` → `compute_caption_scene_sampling_coordinates` →
  `extract_caption_scene_run_parcels` with the expected commands.

### Context

- Request: Written for TODO entries S10 and S31 (approved by the developer on 2026-09-30), implemented when the developer asked to go on with S10 and S31.
- Files changed: `workflow/libraries/fmri_processing.py`, `workflow/dataset_processing/caption_scene_dataset/{Snakefile, envs/caption_scene_dataset_processing_environment.yaml, scripts/*}`, `workflow/dataset_processing/nsd_data_dataset/scripts/{compute_nsd_isc.py, make_nsd_manifest.py}`, `config/config.yaml`, `README.md`, `docs/reference/fmri_preprocessing.md`.

---

## 11:16 — Narratives: average a subject's repeated runs before the ISC

Kind: `new_feature`

### Changes

- `workflow/dataset_processing/narratives_dataset/Snakefile`: `write_narratives_isc_manifest()`
  writes a `subject` column (`task | subject | parcel_ts | isc_npy`), looping over the scans of
  `NARRATIVES_TASK_GROUPS`; `parcel_outputs_for_task()`, its only user, is deleted. The comment on
  the task filter no longer says that every scan is its own observation.
- `compute_narratives_isc.py`: requires the `subject` column and passes it to
  `compute_isc_from_files(..., subjects = ..., truncate_to_shortest = True)`, so the runs are first
  truncated to the shortest one and then averaged per subject (the S10 helper).

Only `pieman` has repeats: 11 of its 75 subjects contribute two runs (86 scans). Before, each run
counted as a separate subject in the leave-one-out ISC.

### Behaviour

The `pieman` ISC and everything downstream of the Narratives ISC change; part of the 2026-10-02
full recomputation.

### Verification

On the existing parcel files, the old call reproduces the stored `pieman` ISC exactly; with
averaging the median ISC goes from 0.1246 to 0.1334 and the parcel-wise correlation with the old
ISC is 0.9989. The other 17 stories have one scan per subject and are unchanged.

### Context

- Request: Written after the developer asked to add the Narratives pieman repeats, found while implementing S10, to the batch.
- Files changed: `workflow/dataset_processing/narratives_dataset/Snakefile`, `workflow/dataset_processing/narratives_dataset/scripts/compute_narratives_isc.py`, `docs/reference/fmri_preprocessing.md`.

---

## 11:37 — Split-half reliability of the ISC vectors (TODO S30); Caption Scene parcel names fixed

Kind: `new_feature`, `bugfix`

### Changes

#### ISC reliability (S30)

- New `workflow/libraries/compute_isc.py`: the ISC functions moved out of `fmri_processing.py`
  (`CONSTANT_SIGNAL_RTOL`, `is_constant_signal()`, `compute_leave_one_out_isc()`,
  `average_repeats_by_subject()`, `compute_isc_from_files()`, `single_value()`), so they can run in
  the ISC environment, which has no nibabel/nilearn. `fmri_processing.py` keeps the parcel
  extraction. New: `load_isc_inputs()` (loading, truncation and repeat averaging, split out of
  `compute_isc_from_files()`, which now wraps it) and `compute_split_half_isc_reliability(data,
  number_of_splits, rng)` (mean Pearson r between the leave-one-out ISC vectors of two random
  halves of the subjects; NaN below 4 subjects). The four `compute_*_isc.py` scripts import from
  `compute_isc`.
- New scripts in `workflow/isc_nearest_neighbours/scripts/`: `compute_isc_reliability.py` (one row
  per stimulus: subjects, time points, split-half r, Spearman-Brown r; one
  `default_rng(random_seed)` stream over the stimuli in sorted order) and
  `aggregate_isc_reliability.py` (one row per dataset: number of stimuli with and without a value,
  median time points, median and quartiles of both reliabilities, median |ISC| and share of
  |ISC| ≥ 0.9 from `isc_dataframe.parquet`).
- `workflow/isc_nearest_neighbours/Snakefile`: `ISC_MANIFEST_LAYOUT` (stimulus and parcel columns,
  truncation, per dataset), rules `compute_isc_reliability` (wildcard `dataset`, input
  `{processing_output_dir}/manifests/isc_manifest.tsv` and the ISC flag) and
  `aggregate_isc_reliability` (`results/mind/all_isc_reliability.tsv`, added to `rule all` and
  `all_isc_nearest_neighbours`).
- Caption Scene Snakefile: new rule `write_caption_scene_isc_manifest` (`run:`) writes
  `manifests/isc_manifest.tsv` (`stimulus_id | subject | parcel_ts`), like the other datasets;
  `caption_scene_parcel_path(row)` factored out of `caption_scene_parcel_paths()`.
- `config/config.yaml`: `isc_reliability_number_of_splits: 100`.

#### Caption Scene parcel file names (fix to the S31 code of the same day)

`read_manifest()` in the Caption Scene Snakefile read `subject`, `session` and `run` as integers
and turned them back into unpadded strings (`sub-1_ses-13_run-50`), while the rewritten
`extract_caption_scene_parcels.py` reads them as text and writes zero-padded names
(`sub-01_ses-13_run-050`). Every `compute_caption_scene_isc` job would have looked for missing
files. `read_manifest()` now reads those columns (and `event_index`, `stimulus_id`) as text
(`CAPTION_SCENE_TEXT_COLUMNS`), and the extraction script reads `event_index` as text too; for all
15,900 events the Snakefile and the script now build identical paths.

### Behaviour

Adds four per-dataset TSVs and one summary TSV; no existing result changes because of S30.

### Verification

- With the ISC environment (no nibabel): reliability computed on the existing parcel files of all
  four datasets (NSD 1000, Caption Scene 1000, Narratives 18, Nature Stories 11 stimuli; about 6
  minutes in parallel): median Spearman-Brown r 0.966 (Narratives), 0.864 (Nature Stories), 0.025
  (NSD), 0.011 (Caption Scene, old misregistered parcels); the summary table was written.
- `snakemake -n results/mind/all_isc_reliability.tsv` plans `write_caption_scene_isc_manifest`, four
  `compute_isc_reliability` jobs and `aggregate_isc_reliability` with the expected inputs.
- Parcel paths: Snakefile (`read_manifest()` + `caption_scene_parcel_path()`) and
  `extract_caption_scene_parcels.parcel_output_path()` agree for all 15,900 events.

### Context

- Request: Written for TODO entry S30 (approved by the developer on 2026-09-30), implemented when the developer asked to proceed with S30; the parcel-name fix was found by the S30 test.
- Files changed: `workflow/libraries/{compute_isc,fmri_processing}.py`, `workflow/isc_nearest_neighbours/{Snakefile, scripts/compute_isc_reliability.py, scripts/aggregate_isc_reliability.py}`, `workflow/dataset_processing/*/scripts/compute_*_isc.py`, `workflow/dataset_processing/caption_scene_dataset/{Snakefile, scripts/extract_caption_scene_parcels.py}`, `workflow/Snakefile`, `config/config.yaml`, `README.md`, `docs/reference/fmri_preprocessing.md`.

---

## 11:59 — Narratives: excluded tasks derived from the two reason lists

Kind: `refactor`

### Changes

- `config/config.yaml`: `problematic_subtasks` removed. It repeated, by hand, the union of
  `schema_subtasks` and `notthefall_variants`, which had no reader since the parse-time JSON writer
  was removed on 2026-10-01 (TODO S28/S32). The two reason lists stay, each with its own comment.
- `workflow/dataset_processing/narratives_dataset/Snakefile`: new
  `NARRATIVES_PROBLEMATIC_SUBTASKS = schema_subtasks + notthefall_variants`, used by
  `narratives_task_is_excluded()` and by `write_narratives_problematic_stimuli`
  (`params.problematic_stimuli`).
- `docs/reference/fmri_preprocessing.md`, step 1: names the two keys.

### Behaviour

The excluded tasks are the same 10, in the same order, so `VALID_NARRATIVES_TASKS` and the rule's
params are unchanged; the list can no longer drift out of sync with its reasons.

### Verification

`schema_subtasks + notthefall_variants` equals the old `problematic_subtasks` element by element.
`snakemake -n resources/datasets/narratives_dataset/excluded_stimuli.txt` parses the workflow; the
rule's rerun reason is only the code change of the 2026-10-02 layout pass, and its entry in
`--list-params-changes` is the same with and without this change.

### Context

- Request: Written after the developer chose to keep the two reason lists separate and derive the exclusion list from them.
- Files changed: `config/config.yaml`, `workflow/dataset_processing/narratives_dataset/Snakefile`, `docs/reference/fmri_preprocessing.md`.
