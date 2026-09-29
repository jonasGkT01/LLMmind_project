# 2026-09-29 — Model-level alignment plot now shows the "chance" line

## What changed

- **The model-level alignment plots** in
  `results/pictures/alignment_lineplots/` now have a grey dashed line. It
  shows the score a model would get **by pure chance**, meaning if its
  nearest neighbours were picked at random. The legend calls it
  "Null expectation (hypergeometric)".
- **The concept-level plots** in
  `results/pictures/concept_alignment_scatterplots/` already had this line.
  They have not changed.
- Every alignment plot now has a reference line:
  - raw scores: the chance level
  - enrichment: 1
  - Spearman: 0

## How to read it

- The chance level is *number of neighbours ÷ (number of concepts − 1)*.
  For example, 25 neighbours among 1000 concepts gives 25/999 ≈ 0.025.
- A model point **above** the line agrees with the brain data more than
  chance would. Whether the difference is significant is shown by the
  asterisks under each model.
- With few neighbours, the chance level is close to 0, and the model
  points usually sit just above it. On the 0–1 axis the gap can be hard to
  see. The **enrichment plots** (`alignment_enrichment_lineplots/`) show
  the same comparison on a clearer scale.

## What this means for you

- **Redraw the plots once to see the line.** Snakemake does not notice
  changes to plotting code by itself, so use the "redraw every plot"
  command in the README. No other step needs to rerun, and no numbers
  change.

---
*AI disclosure: this note was written by an AI coding assistant.*

- *Tool: Claude Code (Anthropic), VS Code extension.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Date: 2026-09-29.*
- *Basis: the change made in the same session at the developer's request,
  checked by drawing one real plot (caption_scene, cosine, 25 neighbours).*
- *Review status: not yet reviewed by the developer at the time of writing.*

*The developer changelog entry of the same name has the technical details.*
