# 2026-09-22 — Plot raw concept-level alignment scores instead of enrichment ratios

## Summary

The model-level plot (`plot_brain_model_alignment_lineplot.py`) plots the
raw mean `alignment_score`. The concept-level boxplot
(`plot_concept_alignment_enrichment.py`) instead plotted a derived
`enrichment` ratio (`alignment_score / hypergeometric_expected_alignment_score`),
so the two plots were not showing the same underlying quantity. Changed the
concept-level plot to show the raw `alignment_score` per concept, matching
the model-level plot, and renamed the script and its output accordingly
(including making explicit that it is a scatter/boxplot, not a lineplot).

## Changes

### `workflow/visualisation/scripts/plot_concept_alignment_enrichment.py` → `workflow/visualisation/scripts/plot_concept_alignment_scatterplot.py`

- Renamed the script.
- `read_model_enrichments()` → `read_model_alignment_scores()`: still
  validates path metadata, required columns, duplicated concepts, score
  range, and `number_of_neighbours <= population_size`, and still computes
  the hypergeometric `expected_alignment_score` for the file (`k /
  (number_of_concepts - 1)`), but now returns the raw `alignment_score`
  column instead of dividing by `expected_alignment_score` to produce an
  `enrichment` column. Also returns `expected_alignment_score` to the
  caller instead of embedding it in the ratio.
- `main()`: collects `expected_alignment_score` across all input files and
  raises `ValueError` if they are inconsistent (they are expected to be
  equal within one plot, since all models in a plot share the same
  concept set and `k`). The boxplot/scatter now plot `alignment_score`
  directly; the `ax.axhline(...)` reference line is now drawn at the
  (raw-score) `expected_alignment_score` value instead of a fixed `1.0`,
  since `1.0` was only meaningful for the enrichment ratio.
- Updated plot title (`"Concept-level LLM-brain alignment"`) and y-axis
  label (`"Alignment score"`, was `"Observed alignment / hypergeometric
  expected alignment"`).

### `workflow/visualisation/Snakefile`, `workflow/Snakefile`

- Renamed rule `plot_concept_alignment_enrichment` → `plot_concept_alignment_scatterplot`.
- Renamed its output directory `results/alignment_enrichment_plots/` →
  `results/concept_alignment_scatterplots/`, and the output filename
  fragment `concept_alignment_enrichment` → `concept_alignment`.
- Updated the `shell:` invocation to call the renamed script.

### `README.md`

- Updated the `Outputs` and `visualisation/` sections to reference
  `results/concept_alignment_scatterplots/` and "per-concept alignment
  scatterplots" instead of the enrichment naming.

## Verification

- `python3 -m py_compile workflow/visualisation/scripts/plot_concept_alignment_scatterplot.py`.
- Grepped the repository (excluding `results/` and historical changelog
  entries) for `concept_alignment_enrichment`, `alignment_enrichment_plots`,
  `read_model_enrichments`, and the intermediate `plot_concept_alignment.py`
  name — no remaining references.

## Files touched

- `workflow/visualisation/scripts/plot_concept_alignment_enrichment.py` (deleted)
- `workflow/visualisation/scripts/plot_concept_alignment_scatterplot.py` (added)
- `workflow/visualisation/Snakefile`
- `workflow/Snakefile`
- `README.md`
