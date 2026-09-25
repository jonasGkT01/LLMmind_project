# 2026-09-25 — Enrichment plots: symlog y-axis replaces the Tukey-fence cap

## Summary

This replaces the approach in `2026-09-25-enrichment-ylim-tukey-fence.md`
(commit `b5988d6`). That change capped the shared y-limit at the per-model
boxplot whiskers and left extreme concepts off-canvas. The developer now wants
every point drawn. Both enrichment plots therefore use a y-axis that is
linear on [0, 1] and log10 above 1. The shared limit again fits every concept
value.

## Changes

### `workflow/libraries/compute_alignment_enrichment.py`

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

### Plot scripts

- `plot_brain_model_alignment_enrichment_lineplot.py` and
  `plot_concept_alignment_enrichment_scatterplot.py` call
  `set_enrichment_y_scale(ax)` just before `ax.set_ylim(*enrichment_ylim(...))`.
- The scatter script no longer counts hidden points and no longer imports
  `Line2D`.

## Design notes

- The y-scale is still shared between the model- and concept-level plots of
  one (dataset, similarity, k).
- **Why `symlog` and not `log`:** concept enrichment can be exactly 0
  (observed score 0), which a pure log axis cannot show.
- **Known limitation:** model means are usually 1.0–1.2, a small part of the
  1–10 decade. The line plot is still fairly flat whenever the shared axis
  must reach much higher concept values.

## Verification

- All 40 enrichment plots were regenerated with
  `--forcerun`/`--allowed-rules` on the two enrichment rules (41/41 steps, no
  errors).
- Checked by eye:
  - nsd_data / pearson / 5NN scatter: both clusters (0 and ≈ 40) are visible.
  - caption_scene / cosine / 25NN scatter and line plot: ticks and legend
    headroom are correct.
- Not checked: the other plots individually. There are no unit tests.

---
*AI disclosure: the code change, this changelog entry and the related README
edits were written by an AI coding assistant, at the developer's request
("plot all the points, but use log10 scale on the y-axis for y > 1").*

- *Tool: Claude Code (Anthropic), VS Code extension; Snakemake 9.21.0 in the
  project env; matplotlib 3.11.1 in the plotting env.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Date: 2026-09-25.*
- *Session note: the first regeneration left the scatter on a linear axis.
  `git checkout` had restored the committed Tukey version of the scatter
  script, so the replacement targeted the wrong line. This was caught by
  looking at the PNGs and fixed before this entry was written.*
- *Verification: limited to the checks listed under "Verification".*
- *Review status: not yet reviewed by the developer at the time of writing.
  The change is uncommitted.*
