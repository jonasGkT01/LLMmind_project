# 2026-10-02 — One random stream for all relabelling permutations (TODO S17)

## Changes

- `workflow/libraries/compute_relabelled_alignment.py::compute_relabelled_common_neighbours_for_all_k()`:
  creates `rng = np.random.default_rng(random_seed)` once before the shuffle loop and draws every
  shuffle's permutation from it. Before, shuffle *i* used `default_rng(random_seed + i)`, so a
  replication run with a nearby seed reused almost all shuffles (seed 37 shuffle 1 was seed 38
  shuffle 0), and the alignment tests used different permutations from the Spearman null.
- `workflow/libraries/compute_statistics.py`: deleted `create_relabelling_rng()`, which had no
  other caller.
- `docs/reference/2026-10-02_0925_statistics.md`, section 2: describes the single stream.

## Behaviour

Every LLM-brain and LLM-LLM relabelling null changes, so all alignment p-values, the model-level
empirical p-values, the summary TSVs and the enrichment values change slightly. The Spearman
results do not change. The relabelling rules' shell commands are unchanged, so this change alone
would not trigger a rerun. It is merged together with S22, whose environment change reruns every
job, so the full recomputation picks it up.

Since every test draws only `permutation(number_of_concepts)` from `default_rng(random_seed)`, the
alignment and Spearman tests of a dataset now use exactly the same permutations.

## Verification

On synthetic neighbour arrays (40 concepts, k = 3 and 6, 25 shuffles, seed 37), the function's
common-neighbour counts equal those computed from permutations drawn in sequence from one
`default_rng(37)` stream.

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-02, Claude Opus 5.5: written for TODO entry S17 (approved by the developer on 2026-09-30), implemented when the developer asked to include S17 in the full recomputation.*
- *Files changed: `workflow/libraries/compute_relabelled_alignment.py`, `workflow/libraries/compute_statistics.py`, `docs/reference/2026-10-02_0925_statistics.md`.*
- *Review status: not yet reviewed by the developer.*
