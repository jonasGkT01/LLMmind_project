# 2026-09-21 — Mark degenerate (zero-spread) boxplots; remove per-run diagnostic logging

## Summary

Investigated a report of boxplots in `plot_concept_alignment_enrichment.py`
and `plot_spearman_alignment.py` output appearing to be "missing" for some
models. Root cause: `matplotlib`'s `ax.boxplot()` renders a box whose
quartiles collapse onto each other (`Q1 == Q3`, or the median coinciding with
`Q1` or `Q3`) as a flat, sub-pixel line — visually indistinguishable from no
data at all — rather than raising a warning. This happens legitimately
whenever the underlying per-concept scores are coarsely discretized (small
`number_of_neighbours` relative to the population) and/or the concept count
is small (e.g. the `narratives`/`nature_stories` datasets), causing quartiles
to coincide exactly. Confirmed via a live reproduction against real pipeline
output (`results/alignment_scores/dataset-caption_scene_model-*_brain_cosine-
alignment_score_50NN.parquet`): models with `Q1 == Q3 == 0` in the
diagnostics rendered no box at all, while models with only `median == Q1`
still rendered a visible (but asymmetric) box.

This is a plotting/legibility fix, not a statistics fix — no alignment
scores, p-values, or other computed values change.

## Changes

### `workflow/libraries/visualisation_utils.py`

- Added `mark_degenerate_boxplot_statistics(ax, boxplot_values, marker="D", color="red", markersize=5, zorder=4)`.
  For each label's value array, computes `Q1`/`median`/`Q3` and, if any pair
  is equal (`np.isclose`), draws a red diamond at `(position, median)` on top
  of the boxplot (`zorder=4`, above the box at `zorder=3` and the scatter at
  `zorder=1`). Adds a single `"Degenerate box (zero-width quartile range)"`
  legend entry (only once, regardless of how many boxes are degenerate).
- Removed `log_boxplot_summary_statistics(labels, boxplot_values)` (added in
  the `2026-09-21-boxplot-stats-and-signature-formatting` changelog entry).
  It printed `n`/`unique`/`min`/`Q1`/`median`/`Q3`/`max`/`IQR` per label to
  stdout on every plotting run; this was diagnostic instrumentation used to
  investigate the issue above and is no longer needed now that degenerate
  boxes are self-documenting in the plot itself. The relevant per-model
  statistics that explained the different box shapes will be described in
  the manuscript instead of logged at runtime.

### `workflow/visualisation/scripts/plot_concept_alignment_enrichment.py`
### `workflow/visualisation/scripts/plot_spearman_alignment.py`

- Removed the `log_boxplot_summary_statistics(labels, boxplot_values)` call
  and its now-unused import.
- Added `mark_degenerate_boxplot_statistics(ax, boxplot_values)` immediately
  after each script's `ax.boxplot(...)` call, before `ax.legend()`.

## Verification

- Reproduced the degenerate-box rendering behavior directly against
  `matplotlib` with synthetic arrays (empty, all-NaN, all-identical,
  single-value) to confirm the exact failure mode before writing the fix.
- Ran both `plot_concept_alignment_enrichment.py` and
  `plot_spearman_alignment.py` end-to-end against real pipeline output
  (`dataset=caption_scene`, `similarity=cosine`, `neighbours=50`, and
  `dataset=narratives`, `similarity=cosine` respectively) in a scratch
  output directory. Confirmed: models with fully collapsed quartiles now
  show only the red diamond (previously nothing); models with a
  partially-visible box show both the box and the diamond; the
  `narratives` Spearman plot (continuous, non-discretized data, no
  collapsed quartiles) renders unchanged with no diamonds, confirming no
  false positives.

## Files touched

- `workflow/libraries/visualisation_utils.py`
- `workflow/visualisation/scripts/plot_concept_alignment_enrichment.py`
- `workflow/visualisation/scripts/plot_spearman_alignment.py`
