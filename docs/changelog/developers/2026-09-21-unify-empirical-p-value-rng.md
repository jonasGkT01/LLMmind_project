# 2026-09-21 — Unify empirical-p-value RNG and formula between llm-llm and llm-mind

## Summary

Comparing the `llm-llm` and `llm-mind` empirical-p-value code paths surfaced
two implementation inconsistencies (no statistical bug in either path's
results, but divergent code for equivalent operations):

1. The positive-empirical-p-value correction `(k + 1)/(n + 1)` was already
   centralized in `libraries/compute_statistics.py` as
   `empirical_upper_tail_p_value()` and used by both concept-level scripts,
   but `aggregate_all_p_value_outputs.py`'s model-level p-value function
   reimplemented the same formula inline.
2. `llm-llm`'s permutation loop
   (`compute_llm_llm_empirical_p_value.py`) advanced one
   `np.random.default_rng(random_seed)` sequentially across all
   `number_of_relabellings` draws, while `llm-mind`'s relabelling loop
   (`relabel_llm_similarity_and_compute_relabelled_llm_alignment_score.py`)
   constructed a fresh `np.random.default_rng(random_seed + shuffle_i)` for
   every shuffle. Both are valid ways to produce independent permutations,
   but the two pipelines drew their null permutations differently for no
   documented reason.

Per explicit instruction, this change does **not** add concept-level
empirical or hypergeometric p-values to the `llm-llm` path — it remains a
model-pair-level-only test by design; only the two inconsistencies above
were addressed.

## Changes

### `workflow/libraries/compute_statistics.py`

- Added `create_relabelling_rng(random_seed, shuffle_index)` →
  `np.random.default_rng(random_seed + shuffle_index)`. A fresh,
  independently-seeded generator per shuffle, so relabellings can be
  produced in any order (or in parallel) and still reproduce the same
  sequence for a given `random_seed`.

### `workflow/llm_llm_alignment/scripts/compute_llm_llm_empirical_p_value.py`

- `compute_empirical_p_value()` now calls `create_relabelling_rng(random_seed, shuffle_i)`
  inside the loop instead of advancing one `default_rng(random_seed)` across
  all iterations.
- **Behavioral change**: this alters the exact sequence of permutations
  drawn (not just a refactor) — see Compatibility note below.

### `workflow/llm_mind_alignment/scripts/relabel_llm_similarity_and_compute_relabelled_llm_alignment_score.py`

- `compute_relabelled_alignment_scores()` now calls
  `create_relabelling_rng(random_seed, shuffle_i)` instead of inlining
  `np.random.default_rng(random_seed + shuffle_i)`. Identical arithmetic,
  same seed schedule — no behavioral change, pure extraction to the shared
  helper.

### `workflow/llm_mind_alignment/scripts/aggregate_all_p_value_outputs.py`

- `compute_model_level_empirical_p_value()` now calls
  `empirical_upper_tail_p_value(number_at_least_as_large=..., number_of_relabellings=...)`
  instead of reimplementing `(k + 1)/(n + 1)` inline. No behavioral change —
  identical arithmetic.

## Compatibility note

`llm-llm`'s empirical p-values will now be computed from a different
(though equally valid) sequence of random permutations than before. Any
existing `results/alignment_scores/dataset-*_model-*_model-*_empirical_*
-alignment_score_*NN.p_value.tsv` files were generated under the old
sequential-RNG scheme and should be regenerated (`snakemake --use-conda
--cores <N> --forcerun compute_llm_llm_empirical_p_value` or by deleting the
affected outputs) to be consistent with this change. `llm-mind`'s
concept-level and model-level outputs are numerically unaffected and do not
need regenerating.

## Verification

- Confirmed `create_relabelling_rng(seed, i)` is deterministic
  (`.permutation(...)` on two separately-constructed instances with the
  same arguments returns identical output).
- Ran `compute_llm_llm_empirical_p_value.py` end-to-end against real data
  (`dataset=caption_scene`, `model_1=dinov2_g`, `model_2=clip_h`,
  `similarity=pearson`, `5NN`, `8920` shared concepts, `20` relabellings)
  after the change; exited `0` and produced a well-formed result row.
- Imported all three modified modules under `PYTHONPATH=workflow` to
  confirm no syntax/import errors.

## Files touched

- `workflow/libraries/compute_statistics.py`
- `workflow/llm_llm_alignment/scripts/compute_llm_llm_empirical_p_value.py`
- `workflow/llm_mind_alignment/scripts/relabel_llm_similarity_and_compute_relabelled_llm_alignment_score.py`
- `workflow/llm_mind_alignment/scripts/aggregate_all_p_value_outputs.py`
