# 2026-10-02 — Two unused leftovers removed

## Changes

- `workflow/libraries/compute_alignment.py`: deleted `compute_mean_alignment_score()`, which had
  no caller. `compute_common_neighbours()`, which it wrapped, stays: the relabelling
  (`compute_relabelled_alignment.py`) uses it.
- `workflow/libraries/compute_alignment_enrichment.py`: `compute_model_alignment_enrichment()`
  no longer puts `expected_alignment_score` in its per-model summary, which nothing read. The
  value is still computed and used as the enrichment denominator.

No output, figure or shell command changes; nothing reruns.

## Verification

`py_compile` passes on both files, and `plot_brain_model_alignment_enrichment_lineplot.py` runs on
Caption Scene, cosine, k = 25 (output in the scratchpad).

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-02, Claude Opus 5.5: written after the developer approved removing the two unused leftovers found during the S2/S3 refactor.*
- *Files changed: `workflow/libraries/compute_alignment.py`, `workflow/libraries/compute_alignment_enrichment.py`.*
- *Review status: not yet reviewed by the developer.*
