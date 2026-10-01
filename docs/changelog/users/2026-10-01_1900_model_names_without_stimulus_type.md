# 2026-10-01 — Shorter model names in the plots

The plots now label each model with its name only, for example `clip_b` instead of
`clip_b-vision`. Whether a model ran on text or on images is still shown by the colour of its
name (orange for language, green for vision) and by the legend. File names do not change.

**What to do:** existing figures keep the old labels until they are redrawn. To redraw them now,
run once:

```bash
snakemake --use-conda --cores 4 --rerun-triggers mtime --forcerun plot_alignment_heatmap plot_empirical_p_value_heatmap plot_concept_alignment_scatterplot plot_brain_model_alignment_lineplot plot_concept_alignment_enrichment_scatterplot plot_brain_model_alignment_enrichment_lineplot plot_spearman_alignment
```

This redraws only the plots (193 jobs). Keep `--rerun-triggers mtime`: without it, Snakemake would
also rerun almost the whole pipeline (about 41,000 jobs), because it sees older conda environment
definitions recorded for the upstream steps. Otherwise the figures are redrawn with the next full
run.

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-01, Claude Opus 5.5: written for TODO entry S36, raised and approved by the developer on 2026-10-01.*
- *Files changed: `workflow/visualisation/scripts/plot_alignment_heatmap.py`, `workflow/visualisation/scripts/plot_empirical_p_value_heatmap.py`, `workflow/visualisation/scripts/plot_brain_model_alignment_lineplot.py`, `workflow/visualisation/scripts/plot_concept_alignment_scatterplot.py`, `workflow/visualisation/scripts/plot_brain_model_alignment_enrichment_lineplot.py`, `workflow/visualisation/scripts/plot_concept_alignment_enrichment_scatterplot.py`, `workflow/visualisation/scripts/plot_spearman_alignment.py`, `README.md`.*
- *Review status: not yet reviewed by the developer.*
