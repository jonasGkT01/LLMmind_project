# 2026-10-01 — Models are ordered the same way in every figure

Every figure that lists models now uses the same order: model family in alphabetical order, then
model size, then model name, then stimulus type, with the brain last in the heatmaps. Before, the
heatmaps and the other figures each sorted in their own way, and the order of the models in
`config/config.yaml` could change some figures.

Today's figures do not change (checked: they are identical). From now on, adding a model anywhere
in `config/config.yaml` does not change where it appears in a figure.

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-01, Claude Opus 5.5: written for TODO entry S1, modified and approved by the developer on 2026-09-30; implemented on 2026-10-01 after the developer asked which solutions could be done while the S34 check was running ("proceed").*
- *Files changed: `workflow/libraries/manage_model_metadata.py`, `workflow/visualisation/scripts/plot_empirical_p_value_heatmap.py`, `workflow/visualisation/scripts/plot_alignment_heatmap.py`, `workflow/visualisation/scripts/plot_brain_model_alignment_lineplot.py`, `workflow/visualisation/scripts/plot_concept_alignment_scatterplot.py`, `workflow/visualisation/scripts/plot_spearman_alignment.py`, `workflow/visualisation/scripts/plot_brain_model_alignment_enrichment_lineplot.py`, `workflow/visualisation/scripts/plot_concept_alignment_enrichment_scatterplot.py`.*
- *Review status: not yet reviewed by the developer.*
