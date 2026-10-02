# 2026-10-02 — Alignment-score files: rows in a fixed order, one unused column removed

The per-model alignment-score files (`results/alignment_scores/…NN.parquet`) now list their
concepts in alphabetical order. Before, the order changed randomly on every run. The scores
themselves are unchanged. Two runs now give exactly the same file, so old and new results can be
compared directly, and the files are easier to read when you open them with `parquet2tsv.sh`.

The `alignment_score_percentage` column (the alignment score times 100) is no longer written,
because nothing used it. Use `alignment_score` instead.

Nothing reruns because of this change. Existing files keep their old row order and column until
they are regenerated.

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-02, Claude Opus 5.5: written for TODO entries S38 (approved by the developer on 2026-10-02) and S29 item 2 (approved on 2026-09-30), implemented together at the developer's request.*
- *Files changed: `workflow/libraries/compute_alignment.py`.*
- *Review status: not yet reviewed by the developer.*
