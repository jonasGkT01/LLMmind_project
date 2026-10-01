# 2026-10-01 — Nearest-neighbour code simplified

The two scripts that find the nearest neighbours of every concept, one for the model embeddings
and one for the brain (ISC) vectors, now share the same code. Their results are exactly the same
as before, and nothing needs to be rerun.

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-01, Claude Opus 5.5: written for TODO entries S18 and S20 (item 1), approved by the developer on 2026-09-30; implemented on 2026-10-01 after the developer asked which solutions could be done while the S34 check was running ("proceed").*
- *Files changed: `workflow/libraries/compute_nearest_neighbours.py`, `workflow/llm_nearest_neighbours/scripts/compute_llm_nearest_neighbours.py`, `workflow/isc_nearest_neighbours/scripts/compute_isc_nearest_neighbours.py`.*
- *Review status: not yet reviewed by the developer.*
