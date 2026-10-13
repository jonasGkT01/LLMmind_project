# 2026-10-13 — changes for users

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../../AI_USAGE.md).*

Changes made on this day, in order:

- The Spearman line plot now shows each model's null distribution (new_feature, documentation)
- Spearman error bars back on the points (new_feature, documentation)

---

## 17:50 — The Spearman line plot now shows each model's null distribution

Kind: new_feature, documentation

In the model-level Spearman line plots (`results/pictures/spearman_alignment_lineplots/`), each
model now has a grey dash at the average of its shuffled-label (null) correlations, with the
null's standard deviation as its bar. The coloured point is the observed correlation, now without
a bar. The dashed line at ρ = 0 stays: it is the exact average of the null, not an assumption, and
the grey dashes show it (they all sit at about 0). The
[statistics reference](../../reference/statistics.md#6-spearman-alignment) explains why.

To redraw the plots, run the pipeline with `--forcerun plot_spearman_alignment` (see the
[guide](../../guides/running_and_troubleshooting.md#2-when-snakemake-reruns-a-job)). Only the
Spearman plots are redrawn; no result is recomputed.

---

## 18:21 — Spearman error bars back on the points

Kind: new_feature, documentation

In the model-level Spearman line plots, the error bar (the null's standard deviation) is again
drawn around each model's point, as before 17:50. Each model keeps a small grey dash at the
average of its null, which sits on the dashed line at ρ = 0. To redraw the plots, run the
pipeline with `--forcerun plot_spearman_alignment`.
