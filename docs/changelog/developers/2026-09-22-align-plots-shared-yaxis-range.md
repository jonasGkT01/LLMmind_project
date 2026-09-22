# 2026-09-22 — Pin model-level and concept-level alignment plots to a shared [0, 1] y-axis

## Summary

`plot_brain_model_alignment_lineplot.py` (model-level line plot) and
`plot_concept_alignment_scatterplot.py` (concept-level scatter/boxplot) are
meant to be viewed side by side for the same `(dataset, similarity_type,
number_of_neighbours)` combination — they are listed adjacently in `rule
all_visualisation` and plot the same underlying `[0, 1]`-bounded
`alignment_score` quantity (see
`2026-09-22-concept-alignment-plot-raw-scores.md`). Both scripts previously
called `ax.set_ylim(bottom=0)` with no explicit top, leaving matplotlib to
autoscale the top independently for each plot. Because the line plot's data
is a small number of per-model means (low variance, small vertical spread)
while the scatter plot's data is every individual concept's raw score
(much higher variance), the two plots' autoscaled tops diverged
substantially: the line plot's points/errorbars ended up crowded near the
top of its own canvas even though both plots represent values in the same
`[0, 1]` range. There is no shared-figure/report code that composites the
two plots (each is an independent script/rule producing its own PNG), so
the fix is a fixed, hardcoded y-limit rather than a computed shared bound.

Both scripts already validate that `alignment_score` lies in `[0, 1]`
before plotting (`((alignment_scores < 0) | (alignment_scores >
1)).any()` checks), so `(0, 1)` is a safe, always-correct bound for both.

## Changes

### `workflow/visualisation/scripts/plot_brain_model_alignment_lineplot.py`

- `ax.set_ylim(bottom=0)` → `ax.set_ylim(0, 1)` (was line 205). `figsize`
  was already `(fig_width, 7)`, matching the concept-level script, so plot
  height was not changed.

### `workflow/visualisation/scripts/plot_concept_alignment_scatterplot.py`

- `ax.set_ylim(bottom=0,)` → `ax.set_ylim(0, 1,)` (was line 165).

## Verification

- `python3 -m py_compile` on both scripts.
- Not re-run against pipeline output in this session (no runtime dependency
  changed; the edit only replaces an autoscaled top bound with a fixed one
  already within the scripts' own validated data range).

## Files touched

- `workflow/visualisation/scripts/plot_brain_model_alignment_lineplot.py`
- `workflow/visualisation/scripts/plot_concept_alignment_scatterplot.py`
- `README.md`
- `docs/changelog/developers/2026-09-22-align-plots-shared-yaxis-range.md` (this file)
- `docs/changelog/users/2026-09-22-align-plots-shared-yaxis-range.md`

---
*This changelog entry was drafted by an AI coding assistant (Claude Code,
model Claude Sonnet 5, `claude-sonnet-5`) based on the session's code
changes, and reviewed by the developer before being committed.*
