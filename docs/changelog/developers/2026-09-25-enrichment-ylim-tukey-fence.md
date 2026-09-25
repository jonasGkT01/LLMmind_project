# 2026-09-25 — Enrichment plots: shared y-limit capped at the boxplot whiskers

## Summary

A few extreme concept-level enrichment values used to set the shared y-axis
top of both enrichment plots. The model-level line plot and most concept boxes
then sat flat on the x-axis. `enrichment_ylim()` now caps the top at the
highest per-model upper whisker (Tukey's fence), not at the highest concept
value. Concepts above it are left outside the axes, and the scatterplot's
legend states how many.

## Changes

### `workflow/libraries/compute_alignment_enrichment.py`

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

### `workflow/visualisation/scripts/plot_concept_alignment_enrichment_scatterplot.py`

- The result of `enrichment_ylim()` is kept in `ylim`. The script counts
  concept points with `enrichment > ylim[1]`. If there are any, it appends a
  marker-less `Line2D` legend handle:
  `"<n> of <N> concept points above the axis (not shown)"`.
- Imports `matplotlib.lines.Line2D`.

### Unchanged

- `plot_brain_model_alignment_enrichment_lineplot.py` (net diff empty).
- All statistics. Hidden points still count in the boxplot quartiles and
  medians, in the model-level enrichment, and in every p-/q-value. Only the
  drawn range changed.

## Design notes

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

## Verification

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

## Related: Snakemake does not rerun plots after script edits

The session also covered why editing a plotting script does not trigger a
rebuild. The rules call the scripts from `shell:`. The `code` rerun trigger
only sees the command string, and neither the scripts nor their `libraries/*`
imports are declared inputs. The README already documents the `--forcerun`
workaround. The permanent fix was proposed but **not implemented**: declare
`script=` and the imported `libraries/*.py` under each rule's `input:` and
call `python3 {input.script:q}`. The trade-off: any edit to
`visualisation_utils.py` would then rebuild every plot.

---
*AI disclosure: the code change, this changelog entry and the related README
edits were written by an AI coding assistant, at the developer's request and
following their design decisions (shared y-scale, outliers allowed off-canvas).*

- *Tool: Claude Code (Anthropic), VS Code extension; Snakemake 9.21.0 in the
  project conda env.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Date: 2026-09-25.*
- *Basis: the developer (Jonas Salvalaggio) said that most points in some
  enrichment plots were pressed against the x-axis. The assistant read the
  plotting code, looked at the rendered PNGs, changed the code and
  regenerated the plots.*
- *Verification: limited to the checks listed under "Verification".*
- *Review status: not yet reviewed by the developer at the time of writing.
  The code change is uncommitted. Review it before committing.*
