# 2026-10-02 — Clearer null display in the plots, consistent significance stars, statistics page

**What changes in the figures** (after you redraw them):

- **Model-level enrichment plot and model-level Spearman plot:** the points no longer carry error
  bars. Instead, each model gets a grey interval on the dashed reference line (enrichment = 1, or
  ρ = 0), labelled "Null ± 1 SD". It shows how much that model's score varies by chance. A point
  far above its grey interval is well above chance; the asterisks still say whether it is
  significant.
- **Heatmaps:** the diagonal (a model, or the brain, with itself) is now blank instead of 1.0,
  since it is not a computed score. The white margins around the heatmaps are trimmed.
- **p-value heatmap:** the stars of the brain row and column now match the stars of the
  brain-model line plots exactly. The model-model cells are corrected among themselves. Before,
  both groups were corrected together, so a brain-model cell could get more stars in the heatmap
  than in the line plots.

**New documentation:** `docs/reference/2026-10-02_0925_statistics.md` explains how the alignment
scores, the shuffled (null) scores, the p-values, the enrichment and the multiple-testing
correction are computed, and what every point, bar and grey interval in the figures means. It is
meant as the source for the methods section. It also says clearly that the averaged per-concept
p-values in the summary tables are descriptions, not tests.

**Nothing else changes:** no result file, table or number changes, and nothing reruns by itself.
To redraw all figures, run the "redraw every plot" command in the README's "Running the pipeline"
section; it now includes the two heatmap rules.

Behind the scenes, the code that reads result filenames and the plotting code were merged into
shared functions, so future changes to file names or figure style are made in one place.

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-02, Claude Opus 5.5: written for TODO entries S2, S3, S4, S13, S15, S16 and S20 (approved by the developer on 2026-09-30), implemented after the developer asked to do the TODO tasks that need no rerun.*
- *Files changed: see the developer changelog entry of the same name.*
- *Review status: not yet reviewed by the developer.*
