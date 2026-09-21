# 2026-09-21 — Boxes with no visible spread are now marked on alignment plots

## What changed

On the concept-level enrichment plot and the concept-level Spearman plot,
some models could appear to have no box at all, as if their data were
missing. That box is now marked with a small red diamond whenever this
happens.

## What this means for you

- **A missing-looking box is not missing data.** It means that model's
  result had essentially no spread across concepts — most or all concepts
  landed on the same value, so the box collapsed to a flat line and was
  easy to miss. The red diamond makes this visible instead of it silently
  blending into the axis.
- **No numbers have changed.** Alignment scores, p-values, and every other
  computed value are exactly the same as before — this only changes how a
  specific kind of result is drawn.
- The per-run console printout of summary statistics (min/median/max/etc.
  for each model) that appeared when generating these two plots has been
  removed, since it was added specifically to investigate this issue and is
  no longer needed.

## Action needed

None. Regenerate the two affected plots (concept-level enrichment,
concept-level Spearman) to see the new markers on any results that have
this zero-spread pattern.
