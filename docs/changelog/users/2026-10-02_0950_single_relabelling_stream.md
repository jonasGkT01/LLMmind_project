# 2026-10-02 — Shuffled (null) scores drawn from one random sequence

The significance tests compare each alignment score with scores computed after randomly
shuffling the concept labels 10,000 times. These shuffles are now all drawn from one random
sequence, started from `random_seed` in `config/config.yaml`, exactly as the Spearman test already
did. As a result, all tests of a dataset use the same shuffles, and a replication with a
different seed gives genuinely different shuffles.

**What changes:** after the full recomputation, the alignment p-values and enrichment values
differ slightly from the previous run, as expected for a new set of random shuffles. The Spearman
results stay the same. The methods should say that all tests share one random sequence (see
`docs/reference/statistics.md`, section 2).

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-02, Claude Opus 5.5: written for TODO entry S17 (approved by the developer on 2026-09-30), implemented when the developer asked to include S17 in the full recomputation.*
- *Files changed: `workflow/libraries/compute_relabelled_alignment.py`, `workflow/libraries/compute_statistics.py`, `docs/reference/statistics.md`.*
- *Review status: not yet reviewed by the developer.*
