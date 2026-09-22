# 2026-09-22 — Concept-level plot now shows raw alignment, not enrichment

## What changed

The concept-level LLM-brain plot used to show each concept's alignment
score as a ratio against chance level ("enrichment"). It now shows the raw
alignment score instead, matching the model-level plot, which has always
shown raw alignment scores.

## What this means for you

- The plot's file name and location changed:
  `results/alignment_enrichment_plots/dataset-{dataset}_{similarity}-concept_alignment_enrichment_{k}NN.png`
  is now
  `results/concept_alignment_scatterplots/dataset-{dataset}_{similarity}-concept_alignment_{k}NN.png`
  (the directory name now makes clear this is a scatterplot).
- The y-axis now shows "Alignment score" (the same [0, 1] score used
  elsewhere) instead of a ratio. The dashed reference line still marks the
  hypergeometric chance level, just in raw-score units instead of as a
  ratio fixed at 1.0.
- Boxes/points that previously sat above or below the `1.0` reference line
  will now sit above or below the reference line at its raw-score value;
  the relative ordering of models and the degenerate-box markers are
  unaffected.

## Action needed

Re-run the pipeline (or just the `plot_concept_alignment_scatterplot` rule)
to regenerate this plot under its new path. Update any dashboards,
notebooks, or scripts that reference the old
`results/alignment_enrichment_plots/...concept_alignment_enrichment...`
path.
