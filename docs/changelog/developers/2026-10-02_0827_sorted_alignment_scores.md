# 2026-10-02 — Alignment-score parquets: fixed row order, percentage column dropped

## Changes

- `workflow/libraries/compute_alignment.py::compute_alignment_scores()`:
  - iterates over `sorted(nearest_neighbours_dict_1)` instead of `set(nearest_neighbours_dict_1)`
    (the local `concepts` is gone). A `set` of strings iterates in an order that depends on
    Python's per-process hash randomisation, so every run wrote the same rows in a different
    order. Rows are now always in concept order, and the parquets are byte-reproducible (TODO S38).
  - no longer writes `alignment_score_percentage` (`alignment_score × 100`), which nothing read
    (TODO S29 item 2). Output columns: `concept`, `common_neighbours`, `alignment_score`.

Affects the observed outputs of `compute_llm_mind_alignment_score` and
`compute_llm_llm_alignment_score`. No shell command changed, so nothing reruns; existing files keep
their old order and column until they are regenerated. No reader of these files depends on row
order or on the dropped column.

## Verification

One `compute_llm_mind_alignment_score` job (Caption Scene, `bloom_1b1`, cosine, k = 25) was run
twice in the scratchpad with the project's conda environment: the two parquets are byte-identical,
their concepts are sorted, and their content equals the current file once that is sorted by concept
and stripped of `alignment_score_percentage` (1000 rows).

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-02, Claude Opus 5.5: written for TODO entries S38 (approved by the developer on 2026-10-02) and S29 item 2 (approved on 2026-09-30), implemented together at the developer's request.*
- *Files changed: `workflow/libraries/compute_alignment.py`.*
- *Review status: not yet reviewed by the developer.*
