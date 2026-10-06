# 2026-09-25 — developer changelog

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../../AI_USAGE.md).*

Changes made on this day, in order:

- What rebuilds when `minimum_subjects_per_stimulus` changes (documentation)
- Flattened Spearman output paths, in-plot legends, no per-concept null SD (new_feature, refactor)
- Enrichment plots: shared y-limit capped at the boxplot whiskers (new_feature)
- Enrichment plots: symlog y-axis replaces the Tukey-fence cap (new_feature)
- All plot outputs moved under `results/pictures/` (refactor)
- LLM–LLM pairings: compare a multimodal model with itself across stimuli types (new_feature)

---

## What rebuilds when `minimum_subjects_per_stimulus` changes

Kind: `documentation`

### Summary

No code changes. This entry records an audit of how Snakemake's rerun
triggers propagate a change of `minimum_subjects_per_stimulus` (introduced in
`2026-09-24_new_feature.md`), with the valid
range of the key and one gap found in Narratives. The README has been updated
to match.

### How the value reaches each dataset

| Dataset | Where the value is used | Rerun trigger |
|---|---|---|
| `caption_scene` | `params.minimum_subjects_per_stimulus` of the `make_caption_scene_manifest` checkpoint | params |
| `nsd_data` | `params.minimum_subjects_per_stimulus` of `make_nsd_manifest` | params |
| `narratives` | Parse-time filter on `NARRATIVES_TASK_GROUPS` (`narratives_dataset/Snakefile`, lines 149-155) | Only through `params.retained_tasks` of `write_narratives_problematic_stimuli`, when the retained task set actually changes |
| `nature_stories` | Not used (every subject is required for every story) | — |

#### Caption Scene and NSD

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

#### Narratives — known gap

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

### Valid range

- **Lower bound 2.** ISC needs ≥ 2 observations:
  `caption_scene_parcel_paths()` (`caption_scene_dataset/Snakefile`) and
  `compute_nsd_isc.py` raise with fewer.
- **Practical upper bound 8** for Caption Scene and NSD (8 subjects each).
  Above that, both manifest scripts raise on an empty stimulus set.

### Verification

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

### Context

- Basis: a question from the developer (Jonas Salvalaggio) in the same session: does changing `minimum_subjects_per_stimulus` rerun the project? The first answer in the session wrongly said Narratives doesn't use the key. This entry corrects that.
- Verification: limited to the checks listed under "Verification".

---

## Flattened Spearman output paths, in-plot legends, no per-concept null SD

Kind: `new_feature`, `refactor`

### Summary

- The Spearman outputs no longer live under `results/spearman_alignment/`.
  They sit at the top level of `results/`, next to the other alignment
  outputs, with names that follow the kNN alignment files. The 248 existing
  files were moved, not recomputed.
- Every plot that has a legend draws it **inside the axes** (top left). The
  top 25% of the y-range is kept empty for it. Concept names are **never**
  listed; concepts are only colour-coded.
- The model-level significance asterisks moved from above the points (or
  from the top band on concept-level plots) to **two rows just below the
  x-axis**, above each model name.
- The concept-level enrichment and concept-level Spearman plots no longer
  draw a **per-concept null-SD bar**. The model-level error bars are
  unchanged.

### Output paths

`D` = dataset, `M` = model, `S` = stimuli type, `SIM` = similarity type.

| Old | New |
|---|---|
| `results/spearman_alignment/model_level/dataset-D_model-M-S_brain_SIM-similarity_spearman_alignment_empirical.p_value.tsv` | `results/spearman_alignment_scores/dataset-D_model-M-S_brain_empirical_SIM-spearman_alignment_model_level.p_value.tsv` |
| `results/spearman_alignment/concept_level/…` (same basename as above) | `results/spearman_alignment_scores/dataset-D_model-M-S_brain_empirical_SIM-spearman_alignment_concept_level.p_value.tsv` |
| `results/spearman_alignment/model_level_plots/dataset-D_SIM-brain_model_spearman.png` | `results/spearman_alignment_lineplots/dataset-D_SIM-brain_model_spearman_alignment.png` |
| `results/spearman_alignment/concept_level_plots/dataset-D_SIM-concept_spearman_coefficients.png` | `results/concept_spearman_alignment_scatterplots/dataset-D_SIM-concept_spearman_alignment.png` |
| `results/all_spearman_alignment_scores.tsv` | unchanged |

- The TSV names mirror the kNN p-value files
  (`…_brain_empirical_SIM-alignment_score_<k>NN.p_value.tsv`): `empirical`
  moves before the similarity type, the redundant `-similarity_` is
  dropped, and `_model_level` / `_concept_level` take the place of
  `<k>NN`. The level has to be in the filename now, because both levels
  share one directory.
- The plot directories mirror `alignment_lineplots/` and
  `concept_alignment_scatterplots/`, which draw the same kinds of plot.
- Changed: the path strings in `workflow/Snakefile` (`rule all`),
  `workflow/spearman_alignment/Snakefile` (`all_spearman_alignment`,
  `compute_spearman_alignmentwith_empirical_p_value`,
  `aggregate_all_spearman_alignment_scores`) and
  `workflow/visualisation/Snakefile` (`all_visualisation`,
  `plot_spearman_alignment`). Rule names, wildcards and script arguments
  are unchanged. The scripts take their paths as arguments and create
  parent directories themselves.

#### Migration of existing outputs

- A one-off Python script moved 232 TSVs and 16 PNGs with `os.rename`, so
  the mtimes were kept. It asserted a regex match on every source name, no
  duplicate targets and no existing targets before moving anything. After
  the move, `results/spearman_alignment/` was removed; it was empty.
- `snakemake -n --cores 1 --rerun-triggers mtime` reports "Nothing to be
  done". The moved files have no Snakemake provenance metadata, which
  shows up as "missing provenance/metadata" for
  `compute_spearman_alignmentwith_empirical_p_value` and
  `plot_spearman_alignment`. That is harmless: those files cannot trigger
  reruns themselves.
- A plain `snakemake -n` (default rerun triggers) wants about 8,100 jobs.
  That comes from issues that were there before this session: changed
  software-env definitions on upstream rules (`download_pretrained_llm`,
  `make_nsd_manifest`, …) and a missing
  `write_nature_stories_excluded_stimuli` output. It is not caused by the
  move.

### Legend inside the axes

In `libraries/visualisation_utils.py`:

- `add_legend` now calls `ax.legend(loc="upper left", fontsize=8,
  framealpha=0.9)`. The previous version placed the legend outside the
  axes (`bbox_to_anchor=(1.01, 1.0)`).
- New `LEGEND_HEADROOM_FRACTION = 0.25` and
  `legend_headroom_top(bottom, data_top)`, which returns
  `bottom + (data_top - bottom)/(1 - LEGEND_HEADROOM_FRACTION)`. Callers use
  it as the upper y-limit, so the data stays in the lower 75% of the axes.
  This was needed because `loc="best"` still put the legend on top of data
  in the dense Caption Scene box-scatterplots (about 1,000 points per model).
- Where it is applied:
  - `plot_brain_model_alignment_lineplot.py` and
    `plot_concept_alignment_scatterplot.py`: `ylim = (0,
    legend_headroom_top(0, 1))`, about 1.33. The ticks are pinned to
    `np.linspace(0, 1, 6)`, so no tick above 1 is shown. The two plots still
    share one y-range.
  - `compute_alignment_enrichment.enrichment_ylim`: the top it computed
    before is passed through `legend_headroom_top`. Both enrichment plots
    still share one y-range. The module now imports
    `libraries.visualisation_utils`, and so matplotlib. Only the two
    enrichment plotting scripts use it.
  - `plot_spearman_alignment.spearman_ylim`: returns `(-limit,
    legend_headroom_top(-limit, limit))`. The range is no longer symmetric.
- Removed `concept_legend_handles`. Every caller now passes only
  `significance_legend_handles()`. `CONCEPT_LEGEND_MAX_CONCEPTS` was
  renamed `DENSE_CONCEPT_THRESHOLD`; it now only switches
  `concept_point_alpha` between 0.85 and 0.30.

### Significance asterisks below the axis

- `annotate_significance(ax, x_positions, p_values, q_values)` replaces
  both the old `annotate_significance(ax, x_positions, y_positions, …)` and
  `annotate_significance_band`. **Its signature changed**: the
  `y_positions` argument is gone.
- It anchors each annotation at `(x, 0)` in `ax.get_xaxis_transform()`,
  with offsets of −5 pt (p-value row, black) and −15 pt (q-value row, red),
  `va="top"` and `annotation_clip=False`.
- It calls `ax.tick_params(axis="x", pad=SIGNIFICANCE_TICK_LABEL_PAD_POINTS)`
  (29 pt) to push the model names below the two rows. The pad is kept in
  `_major_tick_kw`, so it survives the later `set_xticks` /
  `style_model_x_axis` calls that follow `boxplot()`.
- Row order changed: the black p-value row is now **above** the red
  q-value row. Before, red was above black.
- Callers updated: all four kNN brain-model plot scripts and both Spearman
  plots. The heatmaps are untouched.

### No per-concept null SD

- `plot_concept_alignment_enrichment_scatterplot.py`: removed the `vlines`
  call and the `null_standard_deviation` read. The y label is now
  `y_axis_label(ALIGNMENT_ENRICHMENT_LABEL)`, without "± null SD".
- `plot_spearman_alignment.py`, concept-level figure: removed the `vlines`
  call and `concept_errors`. The y-limits come from the coefficients only,
  and the label has no "± null SD".
- `enrichment_ylim` now takes the concept-level maximum from `enrichment`
  alone. The model-level values still include their SD.
- The concept-level `empirical_null_standard_deviation_spearman_coefficient`
  column is still written and still required by
  `plot_spearman_alignment.py`'s input validation, which is shared by both
  levels.

### Rerunning

- The plot scripts run from `shell:` rules, so Snakemake's code trigger
  does not see these changes. To redraw the plots:
  ```bash
  snakemake --use-conda --cores <N> --rerun-triggers mtime \
      --forcerun plot_brain_model_alignment_lineplot plot_concept_alignment_scatterplot \
                 plot_brain_model_alignment_enrichment_lineplot \
                 plot_concept_alignment_enrichment_scatterplot plot_spearman_alignment
  ```
- **Not yet done:** the 80 Spearman TSVs for `narratives` and
  `nature_stories` (40 compute jobs) still predate the null-SD column added
  on 2026-09-24. `plot_spearman_alignment` fails for those two datasets
  until they are rebuilt, which also means the narratives and nature_stories
  Spearman PNGs in `results/` are still the pre-2026-09-24 ones, with no
  concept colours. Add
  `compute_spearman_alignmentwith_empirical_p_value` to `--forcerun`. That
  reruns all 116 compute jobs; to rerun only the stale ones, target their
  files instead.
- At the time of writing, none of the plots in `results/` had been
  regenerated with the new code.

### Verification

- Syntax check of every modified file, plus an AST-based check for unused
  imports. pyflakes is not installed in either env.
- `snakemake -n --cores 1 --rerun-triggers mtime` after the move: nothing
  to do. A `grep` confirmed that no reference to the old paths is left in
  `workflow/`.
- Rendered one plot of each of the six affected types into a scratch
  directory, with the visualisation conda env and the exact commands from
  `snakemake -n -p`: narratives cosine k=5 for the four kNN plots,
  caption_scene cosine for both Spearman plots. Checked by eye: legend
  inside and clear of data, asterisks between axis and model names, no
  concept bars.
- Rendered the narratives concept-level Spearman plot from scratch copies
  of the old-format TSVs with a zero-filled null-SD column, to check the
  concept colours on an 18-concept dataset.
- No automated tests exist for the plots.

### Follow-ups

- With 11–20 concepts (Narratives: 18), `concept_colours` uses tab20, whose
  colours come in dark/light pairs of the same hue. At `s=10` some pairs
  are hard to tell apart. Suggested fix (proposed to the developer, not
  applied): a palette without the paired pastels, and larger markers.
- If `spearman_ylim` hits its cap of 1, the headroom pushes the top to
  about 1.67, and tick labels above 1 are shown. Pin the ticks as in the
  alignment-score plots if that ever happens; on current data the limits
  are about ±0.2 (Caption Scene) and ±0.75 (Narratives).
- This resolves the 2026-09-24 follow-up about the top asterisk band
  overlapping points on the fixed-range concept plots.
- The rule name `compute_spearman_alignmentwith_empirical_p_value`
  (missing underscore) was left as it is, to avoid changing CLI commands
  that are already documented.

### Context

- Basis: explicit instructions from the developer (Jonas Salvalaggio) in the same session. The developer asked for the Spearman outputs to sit at the top level of `results/` and approved the proposed names before any change was made. The developer also asked for legends inside the plot, no listed concept names, asterisks near the model names if needed, no per-concept relabelling SD, and the same rules for the Spearman plots. The assistant chose the legend headroom (25%), the exact asterisk placement and row order, keeping the model-level error bars, and applying the asterisk move to every brain-model plot.
- Verification: limited to the checks listed under "Verification". The plots in `results/` were not regenerated.

---

## Enrichment plots: shared y-limit capped at the boxplot whiskers

Kind: `new_feature`

### Summary

A few extreme concept-level enrichment values used to set the shared y-axis
top of both enrichment plots. The model-level line plot and most concept boxes
then sat flat on the x-axis. `enrichment_ylim()` now caps the top at the
highest per-model upper whisker (Tukey's fence), not at the highest concept
value. Concepts above it are left outside the axes, and the scatterplot's
legend states how many.

### Changes

#### `workflow/libraries/compute_alignment_enrichment.py`

- New `upper_whisker(values, whisker=1.5)`. It returns the highest non-NaN
  value ≤ Q3 + 1.5·IQR, where the quartiles come from `np.percentile` (linear
  interpolation). This matches the whisker end matplotlib's `boxplot()` draws
  by default, so the excluded points are the boxplot's own fliers. The
  scatterplot already hides fliers with `showfliers=False`.
- `enrichment_ylim(concept_df, model_df, padding=0.15)`. The signature is
  unchanged and the limit is still shared by both scripts.
  - The data top is now
    `max(1.0, max over labels of upper_whisker(concept enrichment), max(model enrichment + null SD))`.
  - Before, it was `max(1.0, max(all concept enrichment, model enrichment + null SD))`.
  - Padding, `bottom = 0` and `legend_headroom_top()` are unchanged.

#### `workflow/visualisation/scripts/plot_concept_alignment_enrichment_scatterplot.py`

- The result of `enrichment_ylim()` is kept in `ylim`. The script counts
  concept points with `enrichment > ylim[1]`. If there are any, it appends a
  marker-less `Line2D` legend handle:
  `"<n> of <N> concept points above the axis (not shown)"`.
- Imports `matplotlib.lines.Line2D`.

#### Unchanged

- `plot_brain_model_alignment_enrichment_lineplot.py` (net diff empty).
- All statistics. Hidden points still count in the boxplot quartiles and
  medians, in the model-level enrichment, and in every p-/q-value. Only the
  drawn range changed.

### Design notes

- **Why the shared limit stays.** The developer wants the model- and
  concept-level plots of one (dataset, similarity, k) to stay comparable.
  During the session, a separate limit for the line plot, fitted to model
  values ± SD, was tried and then reverted.
- **Why Tukey's fence and not a percentile.** It adapts to each model's
  spread. Its cut-off matches the whiskers the reader already sees. It is
  a standard, citable rule with no tuning knob.
- **Known limitation: degenerate distributions.** When IQR = 0, the fence
  collapses to Q3, so every point that differs from Q3 is excluded. An
  example is nsd_data / pearson / 5NN, where almost every concept is 0 and a
  few are ≈ 40. The plot is then honest but uninformative.
- **Known limitation: the line plot can still sit low.** The concept
  whiskers can legitimately reach well above the model means. For
  caption_scene / cosine / 25NN, concept enrichment is quantised to
  {0, 1.6, 3.2, 4.8}, so the whiskers reach 3.2 while model means are
  ≈ 1.1. Discussed but not implemented: a `symlog` y-axis on both plots
  (linear on [0, 1], log above), or drawing the model-level line over the
  concept scatter.

### Verification

- All 40 enrichment plots were regenerated from the project root. No errors;
  41/41 steps:

  ```bash
  snakemake -s workflow/Snakefile --use-conda --cores 4 \
      --forcerun plot_brain_model_alignment_enrichment_lineplot plot_concept_alignment_enrichment_scatterplot \
      --allowed-rules plot_brain_model_alignment_enrichment_lineplot plot_concept_alignment_enrichment_scatterplot
  ```

- Checked by eye:
  - caption_scene / cosine / 25NN (line plot and scatter): 113 of 24,000
    points hidden, y-top ≈ 12 → ≈ 5.
  - nsd_data / pearson / 5NN (scatter): 314 of 14,000 points hidden.
- Not checked: the other 37 plots individually, and any unit test. The
  project has no tests for the plotting helpers.

### Related: Snakemake does not rerun plots after script edits

The session also covered why editing a plotting script does not trigger a
rebuild. The rules call the scripts from `shell:`. The `code` rerun trigger
only sees the command string, and neither the scripts nor their `libraries/*`
imports are declared inputs. The README already documents the `--forcerun`
workaround. The permanent fix was proposed but **not implemented**: declare
`script=` and the imported `libraries/*.py` under each rule's `input:` and
call `python3 {input.script:q}`. The trade-off: any edit to
`visualisation_utils.py` would then rebuild every plot.

### Context

- Request: made following the developer's design decisions (shared y-scale, outliers allowed off-canvas).
- Basis: the developer (Jonas Salvalaggio) said that most points in some enrichment plots were pressed against the x-axis. The assistant read the plotting code, looked at the rendered PNGs, changed the code and regenerated the plots.
- Verification: limited to the checks listed under "Verification".

---

## Enrichment plots: symlog y-axis replaces the Tukey-fence cap

Kind: `new_feature`

### Summary

This replaces the approach in `2026-09-25_new_feature_refactor_documentation.md`
(commit `b5988d6`). That change capped the shared y-limit at the per-model
boxplot whiskers and left extreme concepts off-canvas. The developer now wants
every point drawn. Both enrichment plots therefore use a y-axis that is
linear on [0, 1] and log10 above 1. The shared limit again fits every concept
value.

### Changes

#### `workflow/libraries/compute_alignment_enrichment.py`

- Removed `upper_whisker()`.
- New module constants:
  - `ENRICHMENT_Y_SCALE = {"linthresh": 1.0, "linscale": 0.9, "base": 10}`.
    matplotlib's `SymmetricalLogTransform` scales the linear part by
    `linscale / (1 - 1/base)`, which is 1 here. The axis position is
    therefore `u = y` for `y ≤ 1` and `u = 1 + log10(y)` above. The range
    [0, 1] gets the same height as one decade, and the transform is
    continuous at 1.
  - `ENRICHMENT_Y_TICKS`: 0, 0.25, 0.5, 0.75, then 1-2-5 steps up to
    5·10⁵. `FixedLocator` drops ticks outside the limits.
- New helpers:
  - `enrichment_axis_position(value)` and `enrichment_axis_value(position)`:
    the forward and inverse of the transform above, as scalar functions.
  - `set_enrichment_y_scale(ax)`: sets `symlog` with the constants above, a
    `FixedLocator(ENRICHMENT_Y_TICKS)`, and a `FuncFormatter` that prints
    `f"{value:g}"` instead of symlog's default `10^n` labels.
- `enrichment_ylim(concept_df, model_df, padding=0.15)`:
  - The data top is back to
    `max(1, max(concept enrichment), max(model enrichment + null SD))`.
  - The padding and `legend_headroom_top()` now act in axis-position space
    (`u`), then the result is mapped back with `enrichment_axis_value()`. Both
    are fractions of the axis height, and on a log axis a fraction applied to
    data values would not give the same height.
  - The bottom stays at 0.

#### Plot scripts

- `plot_brain_model_alignment_enrichment_lineplot.py` and
  `plot_concept_alignment_enrichment_scatterplot.py` call
  `set_enrichment_y_scale(ax)` just before `ax.set_ylim(*enrichment_ylim(...))`.
- The scatter script no longer counts hidden points and no longer imports
  `Line2D`.

### Design notes

- The y-scale is still shared between the model- and concept-level plots of
  one (dataset, similarity, k).
- **Why `symlog` and not `log`:** concept enrichment can be exactly 0
  (observed score 0), which a pure log axis cannot show.
- **Known limitation:** model means are usually 1.0–1.2, a small part of the
  1–10 decade. The line plot is still fairly flat whenever the shared axis
  must reach much higher concept values.

### Verification

- All 40 enrichment plots were regenerated with
  `--forcerun`/`--allowed-rules` on the two enrichment rules (41/41 steps, no
  errors).
- Checked by eye:
  - nsd_data / pearson / 5NN scatter: both clusters (0 and ≈ 40) are visible.
  - caption_scene / cosine / 25NN scatter and line plot: ticks and legend
    headroom are correct.
- Not checked: the other plots individually. There are no unit tests.

### Context

- Request: "plot all the points, but use log10 scale on the y-axis for y > 1".
- Session note: the first regeneration left the scatter on a linear axis. `git checkout` had restored the committed Tukey version of the scatter script, so the replacement targeted the wrong line. This was caught by looking at the PNGs and fixed before this entry was written.
- Verification: limited to the checks listed under "Verification".

---

## All plot outputs moved under `results/pictures/`

Kind: `refactor`

### Summary

The 8 plot and heatmap output directories moved from `results/<dir>/` to
`results/pictures/<dir>/`. Subfolder names and filenames are unchanged. The
existing PNGs were moved with `mv`, not regenerated.

### Changes

| Old | New |
|---|---|
| `results/alignment_heatmaps/` | `results/pictures/alignment_heatmaps/` |
| `results/alignment_p_value_heatmaps/` | `results/pictures/alignment_p_value_heatmaps/` |
| `results/alignment_lineplots/` | `results/pictures/alignment_lineplots/` |
| `results/concept_alignment_scatterplots/` | `results/pictures/concept_alignment_scatterplots/` |
| `results/alignment_enrichment_lineplots/` | `results/pictures/alignment_enrichment_lineplots/` |
| `results/concept_alignment_enrichment_scatterplots/` | `results/pictures/concept_alignment_enrichment_scatterplots/` |
| `results/spearman_alignment_lineplots/` | `results/pictures/spearman_alignment_lineplots/` |
| `results/concept_spearman_alignment_scatterplots/` | `results/pictures/concept_spearman_alignment_scatterplots/` |

- `workflow/visualisation/Snakefile`: 16 paths. These are the 8 in the
  module's own target list and the `output:` of `plot_alignment_heatmap`,
  `plot_empirical_p_value_heatmap`, `plot_concept_alignment_scatterplot`,
  `plot_brain_model_alignment_lineplot`,
  `plot_concept_alignment_enrichment_scatterplot`,
  `plot_brain_model_alignment_enrichment_lineplot` and
  `plot_spearman_alignment` (2 outputs).
- `workflow/Snakefile`: the 8 plot paths in `rule all`.
- No script changes. Every plotting script already calls
  `Path(...).parent.mkdir(parents=True, exist_ok=True)`.
- **Not moved:**
  - NSD stimulus PNGs from `export_nsd_stimuli.py`. They are pipeline inputs,
    not plots.
  - The separate `pca_plot` project.

### Snakemake state

- `snakemake -n --rerun-triggers mtime`: "Nothing to be done". `mv` keeps
  mtimes, so the moved files are accepted as up to date.
- `.snakemake/metadata` is keyed by output path. The moved PNGs therefore have
  no provenance record, which Snakemake reports as "missing
  provenance/metadata" for the plot rules. Until each plot is rebuilt once,
  the `code`/`params`/`software-env` triggers can't fire for them. This
  doesn't matter much here: plot-script edits never fired those triggers
  anyway (see the README's `--forcerun` note).
- A dry run with the default triggers schedules 8,141 jobs. The move is not
  the cause. The causes already existed: changed conda environment
  definitions, and the uncommitted LLM–LLM pairing change in
  `workflow/Snakefile`. The plot jobs appear only as downstream "input files
  updated by another job".

### Migration for other checkouts

A checkout that already has the old directories should move them once to
avoid redrawing every plot:

```bash
mkdir -p results/pictures
for d in alignment_heatmaps alignment_p_value_heatmaps alignment_lineplots \
         concept_alignment_scatterplots alignment_enrichment_lineplots \
         concept_alignment_enrichment_scatterplots spearman_alignment_lineplots \
         concept_spearman_alignment_scatterplots; do
    [ -d "results/$d" ] && mv "results/$d" results/pictures/
done
```

Without this, Snakemake draws the plots again at the new paths and leaves the
old directories in place.

### Commit note

The `rule all` edits in `workflow/Snakefile` sit next to uncommitted work by
someone else (LLM–LLM self-pairs across stimuli types). Stage the hunks
separately (`git add -p workflow/Snakefile`) if the two are meant to go into
different commits.

### Context

- Decision made by the assistant: placing `pictures/` under `results/` rather than at the project root. The request only named the directory.
- Verification: grep for leftover old paths in Snakefiles and scripts (none), and the two dry runs above. No real run after the move.

---

## LLM–LLM pairings: compare a multimodal model with itself across stimuli types

Kind: `new_feature`

> **Update 2026-09-29:** multimodal model support has been
> removed, so the multimodal parts of this entry no longer apply. Gemma 3n and
> Gemma 4 now run as language models. See
> `2026-09-29_new_feature_removal.md`. *(Note added by Claude Code,
> Claude Opus 5.5, `claude-opus-5-5`.)*

### Summary

`llm_llm_pairings()` in `workflow/Snakefile` now also pairs a multimodal
model's language representation with its own vision representation, for
example `gemma3n_e4b-language` vs `gemma3n_e4b-vision` on `caption_scene`.
Every pairing produced before is still produced, with the same filenames.

### Changes

#### `workflow/Snakefile`

- `llm_llm_pairings()` now builds a list of **representations**, one
  `(model, stimuli_type)` per stimuli type the dataset offers and the model
  can embed (`modality` equals the type, or is `"multimodal"`). It then takes
  `itertools.combinations(representations, 2)`.
  - Before, it took `combinations(compatible_models, 2)` and then
    `product(available_modalities, repeat=2)`. A model was never paired with
    itself.
- Why this is exact:
  - `combinations` never pairs a representation with itself, so there is no
    `X-language` vs `X-language` job.
  - A self-pair appears once (`language` → `vision`), never in both orders.
  - For distinct models, both `(A-language, B-vision)` and
    `(A-vision, B-language)` are still emitted, as before.
  - The representations are model-major in `MODEL_KEYS` order, so `model_1`
    still precedes `model_2` and existing output paths are unchanged.
- Removed the now-unused `product` import.

No rule changes were needed: `compute_llm_llm_alignment_score` and
`compute_llm_llm_empirical_p_value` take `stimuli_type_1`/`stimuli_type_2`
from wildcards, so the two inputs of a self-pair are different files.

### Known limitation (not fixed): heatmaps label cells by model only

> **Update 2026-09-29:** fixed. Both heatmaps now label by
> `model_key(model, stimuli_type)`; see
> `2026-09-29_new_feature_removal.md`.

`plot_alignment_heatmap.py` and `plot_empirical_p_value_heatmap.py` use
`model` alone as the row/column label, not `model-stimuli_type`. Once a
multimodal model is enabled on `caption_scene`:

- **Alignment heatmap:** the self-pair lands on the diagonal, which is
  hard-coded to 1.0, so its score is not shown. The model's language and
  vision scores against other models also overwrite each other.
- **Empirical p-value heatmap:** the script raises
  `The empirical p-value for X and Y was provided more than once`, because
  `(A-language, B)` and `(A-vision, B)` both map to `(A, B)`. This already
  happened before this change for any multimodal model. The self-pair only
  adds another case.

The fix is to label by `f"{model}-{stimuli_type}"` in both scripts. It is not
implemented yet.

### Verification

- The old and new function bodies were compared in a standalone script
  (`itertools` + `yaml`, run in the project env).
  - Current config (24 models, no multimodal): old 3,116 pairings, new 3,116,
    identical sets.
  - Config with every commented-out Gemma model enabled (39 models): old
    11,104, new 11,160, no duplicates, old ⊂ new. The 56 extra pairings are
    all self-pairs across stimuli types: 7 multimodal models ×
    4 `caption_scene` k values × 2 similarity types.
- `snakemake -n --cores 1` on the current config parses and builds the DAG.
- Not run: any actual LLM–LLM job for a multimodal model.

### Context

- Basis: the developer (Jonas Salvalaggio) asked to compare the same model across different stimulus types.
- Verification: limited to the checks listed under "Verification".
