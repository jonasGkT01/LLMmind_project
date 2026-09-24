# 2026-09-24 — Alignment-enrichment plots, Spearman null SD, and shared plot conventions

## Summary

- New model- and concept-level **alignment-enrichment** plots. They have
  their own rules and scripts; the existing alignment-score rules and
  scripts are not modified for this.
- The Spearman computation now writes the **SD of its permutation null**,
  and both Spearman plots draw it as error bars.
- Every brain-model plot (not the heatmaps) shows **two rows of
  significance asterisks**: black for the empirical p-value and red for the
  Benjamini-Hochberg q-value.
- Every non-heatmap plot has **model-family separators**.
- Concept-level plots are **coloured by concept**.
- **Titles and axis labels** now follow one pattern across the project.

## Enrichment

`libraries/compute_alignment_enrichment.py` (new) is shared by both new
scripts.

- **Pairing.** Observed files (`…NN.parquet`) are matched one-to-one with
  relabelled files (`…NN_relabelled.parquet`) by filename.
- **Null matrix.** The relabelled scores form a (relabellings × concepts)
  matrix built from the categorical codes (`relabelled_null_matrix`). A
  first version used `DataFrame.pivot`, which had not finished after more
  than 10 minutes on one Caption Scene k=25 input set (24 files of
  8.9M rows).
- **Checks.** The matrix must hold exactly one score per concept per
  relabelling. The concepts must match the observed file. There must be at
  least 2 relabellings.
- **Definitions.** `E` is the model's mean relabelled score over every
  relabelling and concept.
  - Concept level: `observed_c / E`, error `SD_s(relabelled_{s,c}) / E`.
  - Model level: `mean_c(observed_c) / E`, error
    `SD_s(mean_c(relabelled_{s,c})) / E`.
  - SDs use `ddof=1`.
  - Because both levels divide by the same `E`, the model-level enrichment
    equals the mean of the concept-level enrichments.
- **Shared y-axis.** `enrichment_ylim` sets `[0, max(1, max(value + SD)
  over both levels) × 1.15]`. Both scripts compute it from the same inputs,
  so the concept- and model-level plots for one (dataset, similarity, k)
  share their y-limits without writing any intermediate file.

New scripts (structured like `plot_brain_model_alignment_lineplot.py` and
`plot_concept_alignment_scatterplot.py`):

- `visualisation/scripts/plot_brain_model_alignment_enrichment_lineplot.py`
  → `results/alignment_enrichment_lineplots/dataset-{dataset}_{similarity}-brain_model_alignment_enrichment_{k}NN.png`
- `visualisation/scripts/plot_concept_alignment_enrichment_scatterplot.py`
  → `results/concept_alignment_enrichment_scatterplots/dataset-{dataset}_{similarity}-concept_alignment_enrichment_{k}NN.png`

New rules `plot_brain_model_alignment_enrichment_lineplot` and
`plot_concept_alignment_enrichment_scatterplot` are in
`visualisation/Snakefile`. Their targets were added to `rule all` and
`rule all_visualisation`. Inputs are the observed and relabelled parquet
files plus `results/all_alignment_scores.tsv` (for the asterisks).

## Spearman null SD

- `spearman_alignment/scripts/compute_spearman_alignment_with_empirical_p_value.py`
  accumulates the sum of squares of the null coefficients next to the
  existing sum. It writes
  `empirical_null_standard_deviation_spearman_coefficient` (sample SD) to
  both the model- and concept-level TSVs.
  - Checked against `np.std(ddof=1)` on random data.
  - `aggregate_all_spearman_outputs.py` picks the new column up
    automatically; no change was needed there.
- `plot_spearman_alignment.py` requires the column. Error bars use
  `errorbar` at model level and `vlines` at concept level. The symmetric
  y-limits now include the bars.

## Significance asterisks

In `libraries/visualisation_utils.py`:

- `annotate_significance` draws two fixed-height rows above each point:
  the p-value row (`P_VALUE_SIGNIFICANCE_COLOUR = "black"`), then the
  q-value row above it (`Q_VALUE_SIGNIFICANCE_COLOUR = "red"`).
- `annotate_significance_band` draws the same rows in a band along the top
  of the axes, for concept-level plots.
- `significance_legend_handles` adds matching legend entries.

Where they are used:

- Model-level line plot, model-level enrichment plot, model-level Spearman
  plot: above each point.
- Concept-level alignment, enrichment and Spearman plots: the model-level
  p/q values, in the top band. `plot_concept_alignment_scatterplot` gained
  a `--model_level_statistics` argument and rule input for this.

`read_model_level_empirical_p_values` (moved to
`libraries/compute_statistics.py`, which now imports pandas) reads the
p-values from `results/all_alignment_scores.tsv`. It is used by the new
scripts and the concept scatterplot. `plot_brain_model_alignment_lineplot.py`
keeps its own inline copy. The heatmaps are unchanged: the p-value heatmap
still shows only the q-value asterisks, and its title now says so.

## Family separators, concept colours, legends

- `add_model_family_annotations` (already in `visualisation_utils`) is now
  called by the concept-level alignment and Spearman plots and by both new
  scripts.
- `concept_colours` gives each concept one colour for the whole plot,
  assigned in sorted concept order:
  - tab10 up to 10 concepts;
  - tab20 up to 20;
  - beyond 20, golden-ratio hue spacing. Caption Scene and NSD have about
    1,000 concepts, where no palette keeps every colour distinguishable.
- A concept legend is drawn only when there are at most 20 concepts.
- `add_legend` places the legend outside the axes on the right.

## Titles and labels

The title helper `plot_title(level, quantity, dataset, similarity_type[,
number_of_neighbours])` gives `"<level> <quantity>\ndataset: …,
similarity: …[, neighbours: …]"`.

- Levels: `Model-level`, `Concept-level`, `Pairwise` (heatmaps).
- Quantities: `brain-model alignment score`, `brain-model alignment
  enrichment`, `brain-model Spearman alignment`, `model-model and
  brain-model alignment score`, `model-model and brain-model alignment
  empirical p-value`.

The label helper `y_axis_label(quantity[, error])` gives `"<quantity> ±
<error>"`. The x axis is always `Model`, or `Model / brain` on heatmaps.
Reference lines are labelled `Null expectation (…)` and drawn in grey.

## Rerunning

- The Spearman TSVs on disk lack the new column, and `plot_spearman_alignment`
  will raise until they are rebuilt. The script is called from a `shell:`
  rule, so Snakemake's code trigger does not see the change. Force it:
  `snakemake --use-conda --cores <N> --forcerun compute_spearman_alignmentwith_empirical_p_value`.
- The plot rules rerun on their own (code or input change).
- The concept-level enrichment plot reads every relabelled file for a
  (dataset, similarity, k). On the old 8,920-concept Caption Scene outputs
  that took about 4 minutes per plot. The model-level plot takes the same
  time, because it reads the same inputs to share the y-axis.

## Verification

- `python3 -m py_compile` on every modified or new script and library.
- `snakemake -n --cores 8`: the DAG resolves, with 20 jobs for each new
  rule.
- Ran against existing results:
  - the new and updated alignment scripts on `nature_stories` (k=3) and
    `caption_scene` (k=25, cosine);
  - both heatmaps on `nature_stories`;
  - the Spearman plot on fresh `nature_stories` Spearman TSVs (10 models,
    200 relabellings, written to a scratch directory).
- Asterisk placement checked on a synthetic plot, since none of the test
  data reached significance.

## Housekeeping

- Deleted `workflow/spearman_alignment/scripts/__pycache__/` and
  `workflow/visualisation/scripts/__pycache__/`. They held bytecode left by
  this session's test runs, and neither is tracked or ignored in git.
  `workflow/libraries/__pycache__/` (already in `.gitignore`) was kept.

## Follow-ups

- On Caption Scene the concept-level enrichment reaches about 47 (a few
  concepts sharing many neighbours), so the shared y-axis squashes the
  model-level enrichment plot near 1. This follows from requiring the
  shared axis. A log scale is not an option, because many concepts have
  enrichment 0.
- On the fixed-range concept-level plots (alignment score `[0, 1]`,
  Spearman `[-1, 1]`), the top asterisk band can overlap points that sit
  at the very top.

---
*AI disclosure: this changelog entry, together with the code changes it
describes and the related README edits, was written by an AI coding
assistant.*

- *Tool: Claude Code (Anthropic), VS Code extension.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`, 1M-token context).*
- *Date: 2026-09-24.*
- *Basis: explicit instructions from the developer (Jonas Salvalaggio) in
  the same session. The developer chose the null SD as the error bar for
  both the enrichment and the Spearman plots, black/red for p-value/q-value
  asterisks, and asterisks on every brain-model plot except the heatmaps;
  the enrichment definition (dividing both levels by the model-wide mean
  relabelled score) and the title/label wording were the assistant's
  choices.*
- *Verification: limited to the checks listed under "Verification".*
- *Review status: not yet reviewed by the developer at the time of writing.
  Review it before committing.*
