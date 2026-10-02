# 2026-10-02 — New table: how reliable the brain representations are

The pipeline now measures how reliable each stimulus's brain representation (its 200-region ISC
pattern) is: it splits the participants at random into two halves 100 times and checks how well
the two halves agree. The results are in `results/mind/all_isc_reliability.tsv` (one row per
dataset) and `results/mind/{dataset}/isc_reliability.tsv` (one row per stimulus).

A first measurement on the current data shows a large difference between the datasets. For the
stories (Narratives, Nature Stories) the two halves agree very well (corrected reliability 0.97
and 0.86). For the short image events (NSD: 3 brain volumes per image; Caption Scene: 6) they
barely agree (0.03 and 0.01), so these brain representations are mostly noise. The Caption Scene
value will be measured again after the full recomputation, now that its brain data are aligned to
MNI.

Also fixed: a file-naming mismatch introduced earlier today in the new Caption Scene processing,
which would have stopped the Caption Scene brain-response step during the recomputation.

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-02, Claude Opus 5.5: written for TODO entry S30 (approved by the developer on 2026-09-30), implemented when the developer asked to proceed with S30.*
- *Files changed: see the developer changelog entry of the same name.*
- *Review status: not yet reviewed by the developer.*
