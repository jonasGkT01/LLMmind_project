# 2026-10-01 — Commented-out rules and targets removed

## Changes

- `workflow/llm_mind_alignment/Snakefile`: deleted the commented-out rules `reduce_all_p_values`
  (wrote `results/tsv_summary.tsv` with `matrix_reduce` and `bawk`, through a conda environment
  `envs/reduce_all_p_values_environment.yaml` that no longer exists) and
  `translate_parquet_to_tsv_adding_observed_alignment_score` (wrote `…NN.observed.tsv` from the
  per-k `…NN_relabelled.parquet` files, which were replaced on 2026-09-30 by the all-k
  `-relabelled_common_neighbours.parquet` files). Deleted their commented-out targets from
  `rule all_llm_mind_alignment`.
- `workflow/Snakefile`, `rule all`: deleted the same commented-out targets (`…NN.observed.tsv`,
  `results/tsv_summary.tsv`).

Comments only: no rule, input, output or shell command changed, so nothing reruns.
`parquet2tsv.sh` is kept (used by hand to view parquet files). The `bawk`, `coreutils`,
`matrix_reduce` and `molinerislab` entries of `llm_mind_alignment_environment.yaml` stay until S22
(TODO S29 item 3), since changing an environment file reruns every rule that uses it.

## Verification

`snakemake --list-rules` and `snakemake -n` parse the changed Snakefiles (run on a copy of the
committed tree, with `resources/` and `results/` linked read-only).

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-01, Claude Opus 5.5: written for TODO entry S29 item 3 (Snakefile part), approved by the developer on 2026-09-30; implemented after the developer asked to do the parts of S29 that do not interfere with the running S34 check.*
- *Files changed: `workflow/Snakefile`, `workflow/llm_mind_alignment/Snakefile`.*
- *Review status: not yet reviewed by the developer.*
