# 2026-10-13 — developer changelog

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../../AI_USAGE.md).*

Changes made on this day, in order:

- Model-level Spearman line plot draws the computed relabelling null (new_feature, documentation)
- Spearman error bars back on the observed ρ (new_feature, documentation)

---

## 17:50 — Model-level Spearman line plot draws the computed relabelling null

Kind: new_feature, documentation

The dashed reference line of the Spearman plots was a constant (`add_null_line(ax, 0.0, ...)`),
not read from the null computed by
`compute_spearman_alignment_with_empirical_p_value.py`. The constant itself is right: since
`rank_and_normalize()` centres the ranks, the expectation of the relabelling null is exactly 0 at
model and concept level, and the stored `empirical_null_mean_spearman_coefficient` values agree
within the Monte Carlo error (|null mean| ≤ 3.7e-3 over all 300 runs, null SD up to about 0.18).

- `libraries/spearman_scores.py`: new constant `NULL_MEAN_COLUMN`; `read_spearman_scores()`
  requires it at model level and raises `ValueError` if a value is missing, non-numeric or
  |value| > 1.
- `libraries/visualisation_utils.py`: new `plot_null_distributions(ax, null_means,
  null_standard_deviations)`, a grey `errorbar` with a `_` marker at each model's null mean and
  the null SD as `yerr`, legend label `NULL_DISTRIBUTION_LABEL` ("Relabelling null (mean ± SD)").
- `visualisation/scripts/plot_spearman_alignment.py`, model-level plot: draws
  `plot_null_distributions()` and the observed ρ via `plot_model_points(..., None, ...)` (no error
  bar); y-label without "± null SD" (`NULL_STANDARD_DEVIATION` and `y_axis_label` no longer
  imported); y-limits from the observed ρ and |null mean| + null SD. The dashed line at 0 and the
  concept-level plot are unchanged.
- Not changed: `plot_similarity_comparison_lineplot.py` (Spearman version still draws the null SD
  around the observed ρ and a line at 0) and the compute script (so no Spearman job reruns).
- `docs/reference/statistics.md`: section 6 gives the derivation of the zero null mean and the
  measured null means; section 7 describes the new model-level Spearman plot.

Rerun: nothing reruns by itself. The plot rules are not covered by `code_version()`, and no
covered rule imports `spearman_scores.py` or `visualisation_utils.py` (checked), so the summary
tables are untouched. Redraw with `--forcerun plot_spearman_alignment`.

### Context

- Request: the developer asked how the Spearman reference line is computed, finding it strange
  that the null average is exactly zero; the problem was recorded as P1 in the TODO file and the
  developer chose solution B (computed null drawn per model, plus documentation).
- Files: `workflow/libraries/spearman_scores.py`, `workflow/libraries/visualisation_utils.py`,
  `workflow/visualisation/scripts/plot_spearman_alignment.py`, `docs/reference/statistics.md`.
- Verification: the script was run with the visualisation conda environment on the existing
  cosine Spearman TSVs of Narratives and NSD, writing to the scratchpad; both plots were inspected
  (grey null bands centred on about 0, observed ρ unchanged, legend and limits correct).

---

## 18:21 — Spearman error bars back on the observed ρ

Kind: new_feature, documentation

The 17:50 change moved the null-SD error bar from the observed ρ to the null mean. On seeing the
plots, the developer asked to put it back on the observed ρ and keep everything else.

- `libraries/visualisation_utils.py`: `plot_null_distributions()` replaced by
  `plot_null_means(ax, null_means)`, a grey `_` marker at each null mean with no error bar;
  `NULL_DISTRIBUTION_LABEL` replaced by `NULL_MEAN_LABEL` ("Relabelling null mean").
- `visualisation/scripts/plot_spearman_alignment.py`, model-level plot: `plot_model_points()`
  again gets `null_standard_deviations` as error bars; y-label back to
  `y_axis_label(SPEARMAN_COEFFICIENT_LABEL, NULL_STANDARD_DEVIATION)`; y-limits from
  |ρ| + null SD and the null means. `read_spearman_scores()` (null mean column) is unchanged.
- `docs/reference/statistics.md`: section 7 (table row and error-bar conventions) and its Changes
  section.

Rerun: `--forcerun plot_spearman_alignment` (12 plot jobs).

### Context

- Request: the developer found the error bar on the reference line instead of on the points and
  asked to move it back, keeping the rest ("just move the error bar back where it was").
- Files: `workflow/libraries/visualisation_utils.py`,
  `workflow/visualisation/scripts/plot_spearman_alignment.py`, `docs/reference/statistics.md`.
- Verification: the script was run on the cosine Spearman TSVs of all four datasets in the
  scratchpad; the Caption Scene plot was inspected (bars on the points, grey dashes on the line at
  0, y-label "± null SD").
