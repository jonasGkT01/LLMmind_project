# 2026-10-02 — Unused code removed

Two pieces of code that nothing used were deleted: a function that computed a mean alignment
score in a way the pipeline no longer uses, and an extra value kept by the enrichment
calculation but never shown. Nothing changes when you run the pipeline: no result, table or
figure changes, and nothing reruns.

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-02, Claude Opus 5.5: written after the developer approved removing the two unused leftovers found during the S2/S3 refactor.*
- *Files changed: `workflow/libraries/compute_alignment.py`, `workflow/libraries/compute_alignment_enrichment.py`.*
- *Review status: not yet reviewed by the developer.*
