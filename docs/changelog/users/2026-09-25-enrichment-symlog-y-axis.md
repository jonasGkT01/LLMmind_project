# 2026-09-25 — Enrichment plots now show every point, with a log scale above 1

## What changed

- **All points are back on the enrichment plots.** The earlier change the
  same day hid a few very high concepts to keep the plots readable. That is
  undone, and nothing is hidden any more.
- **New vertical axis.** From 0 to 1 the axis is ordinary (evenly spaced).
  Above 1 it is logarithmic: 1 to 10 takes the same height as 10 to 100, and
  the same height as 0 to 1. Very high values therefore fit without
  squeezing everything else against the bottom.
- **Clear tick labels:** 0, 0.25, 0.5, 0.75, 1, 2, 5, 10, 20, 50 and so on.
- **The two enrichment plots still share their vertical axis:**
  - `alignment_enrichment_lineplots/` (one point per model);
  - `concept_alignment_enrichment_scatterplots/` (one point per concept).
- The note "N concept points above the axis (not shown)" is gone from the
  legend, because no points are hidden now.

## What this means for you

- **Read the axis carefully above 1.** Equal distances mean equal *ratios*
  there, not equal differences. For example, going from 2 to 4 looks as big
  as going from 20 to 40.
- **The model-level line can still look flat.** Model averages are usually
  between 1.0 and 1.2. When some concepts reach much higher values, that
  range takes up only a small part of the plot.
- **Redraw once** with the "redraw every plot" command in the README.

---
*AI disclosure: this note was written by an AI coding assistant.*

- *Tool: Claude Code (Anthropic), VS Code extension.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Date: 2026-09-25.*
- *Basis: the change made in the same session at the developer's request,
  checked by regenerating all enrichment plots.*
- *Review status: not yet reviewed by the developer at the time of writing.*

*The developer changelog entry of the same name has the technical details.*
