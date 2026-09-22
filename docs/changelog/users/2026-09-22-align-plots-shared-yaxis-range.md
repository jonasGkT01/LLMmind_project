# 2026-09-22 — Alignment line plots and concept-level plots now share the same vertical scale

## What changed

The model-level alignment line plots (in `results/alignment_lineplots/`)
sometimes showed their points and lines crowded right up against the top
edge of the plot, even though the same values on the concept-level plot
(in `results/concept_alignment_scatterplots/`) had comfortable headroom.
Both plots now use the same fixed vertical range, `0` to `1`, which is the
full possible range of the alignment score they both show.

## What this means for you

- Line plots and concept-level plots for the same dataset now look
  consistent when placed side by side — same vertical scale, same plot
  height.
- No more misleadingly "maxed out" looking line plots; a point near the
  top of the plot now genuinely means the alignment score is close to 1,
  not just that it was the largest value in that particular plot.
- No action needed — this only changes how existing results are drawn.
  Re-run the relevant `plot_brain_model_alignment_lineplot` and
  `plot_concept_alignment_scatterplot` rules to regenerate the plots with
  the new scale.

---
*This note was drafted by an AI coding assistant (Claude Code, model
Claude Sonnet 5) and reviewed by the developer before being published.*
