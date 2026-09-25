# 2026-09-25 — Enrichment plots no longer squashed by a few extreme concepts

## What changed

- **Taller, more readable enrichment plots.** Before, a handful of concepts
  with very high enrichment set the height of the vertical axis. Everything
  else was pressed flat against the bottom of the plot. The axis now stops
  where the boxplot whiskers end, so the boxes and most points are visible.
  This applies to both plots:
  - `results/alignment_enrichment_lineplots/`
  - `results/concept_alignment_enrichment_scatterplots/`
- **The two plots still share their vertical axis**, so you can compare them
  side by side.
- **Nothing is removed from the results.** The extreme concepts are only left
  off the drawing. They still count in the boxes, the model-level values and
  every significance test.
- **You're told what is hidden.** When some concept points fall above the
  axis, the concept-level plot's legend says how many, for example
  "113 of 24000 concept points above the axis (not shown)".

## How the cut-off is chosen

A point is left off the drawing only if the boxplot already treats it as an
outlier. That means it is above the top of the box plus 1.5 times the box's
height (a standard rule known as Tukey's fence). Each model's values and error
bars always stay visible, and so does the dashed "enrichment = 1" line.

## What this means for you

- **Redraw the plots once to see the change.** Snakemake doesn't notice
  changes to plotting code by itself, so use the "redraw every plot" command
  in the README. No other step needs to rerun.
- **Some plots can still look low.** Sometimes most concepts genuinely spread
  much higher than the model averages. In that case the model-level line
  still sits in the lower part of its plot, because it shares the axis with
  the concept plot.
- **Very small neighbourhoods can give almost-empty concept plots.** For
  example, NSD with 5 neighbours: when nearly every concept scores 0, all the
  non-zero concepts count as outliers and are hidden. The legend count tells
  you when this happens.

---
*AI disclosure: this note was written by an AI coding assistant.*

- *Tool: Claude Code (Anthropic), VS Code extension.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Date: 2026-09-25.*
- *Basis: the change made in the same session at the developer's request,
  checked by regenerating all enrichment plots.*
- *Review status: not yet reviewed by the developer at the time of writing.*

*The developer changelog entry of the same name has the technical details.*
