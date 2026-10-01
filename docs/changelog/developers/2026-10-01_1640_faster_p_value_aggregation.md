# 2026-10-01 — Faster p-value aggregation (both summary TSVs)

## Problem

`libraries/aggregate_alignment_scores.py::aggregate_all_p_value_outputs()`, shared by the rules
`aggregate_all_p_value_outputs` (LLM-brain) and `aggregate_all_llm_llm_p_value_outputs` (LLM-LLM),
handled one result at a time on one core. The first complete LLM-LLM run on node5 took 4 h 10 min
for 11,184 results (~1.4 s each). About a quarter of that was a duplicate check on the relabelled
rows of each result.

## Changes

- `workflow/libraries/aggregate_alignment_scores.py`:
  - deleted `read_unique_relabelled_alignment_scores()`, which ran
    `duplicated(subset = ["shuffle_id", "concept"])` on the up-to-10-M relabelled rows of each
    result. The relabelled files are written only by `libraries/compute_relabelled_alignment.py`,
    where (k, shuffle, concept) is unique by construction, and `compute_empirical_p_value.py`
    already reads them without the check. The reads now call
    `compute_alignment.read_relabelled_alignment_scores()` directly (unchanged filtered per-k read);
  - new top-level `aggregate_result(metadata, empirical_path, hypergeometric_path, relabelled_path)`:
    reads one result's inputs and returns `aggregate_model_results()`;
  - `aggregate_all_p_value_outputs()` gains a required `threads` parameter and maps
    `aggregate_result` over the results, in sorted key order, with
    `concurrent.futures.ProcessPoolExecutor(max_workers = threads).map(..., chunksize = 16)`.
    `map()` keeps the input order, so the rows, and the TSV, are unchanged.
- `workflow/llm_mind_alignment/scripts/aggregate_all_p_value_outputs.py`,
  `workflow/llm_llm_alignment/scripts/aggregate_all_llm_llm_p_value_outputs.py`: new required
  `--threads` (int), passed to `aggregate_all_p_value_outputs()`.
- Rules `aggregate_all_p_value_outputs` and `aggregate_all_llm_llm_p_value_outputs`: `threads: 4`
  and `--threads {threads}` (after `@"$args_file"` in the LLM-LLM rule). Peak memory: about 4 ×
  one result's relabelled rows.

Rejected (TODO S34 part 1, implemented and measured): reading each all-k relabelled file once and
splitting it by k with `groupby`. On a Caption Scene file (40 M rows, k = 5, 25, 50, 100) that took
14–17 s against ~0.7 s for the four filtered per-k reads, because the split copies the categorical
`shuffle_id` and `concept` columns.

## Rerun impact

The two shell commands changed, so Snakemake reruns both aggregation rules, and the plots that
wait for their TSVs, once. The outputs do not change.

## Verification

Old code (`main` at `d3db409`) and new code, run in the same conda environment on the frontend:
- all 768 LLM-brain results: output byte-identical (`cmp`) to
  `results/all_model_brain_alignment_scores.tsv`; 23 min 24 s old, 6 min 20 s new;
- 180 LLM-LLM results (60 relabelled files, 40 of them Caption Scene or NSD): byte-identical;
  4 min 27 s old, 2 min 25 s new (with the frontend's load about 10 and about 40 respectively).

A full LLM-LLM comparison was stopped after 2 h by the frontend's load (~40 on 8 cores) and not
repeated; the developer accepted the evidence above. The node5 duration of the new code is still
to be measured (`docs/reference/2026-10-01_0926_clean_run_duration.md`).

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-01, Claude Opus 5.5: written for TODO entry S34, approved by the developer on 2026-10-01 and revised after measurement (part 1 dropped), after the developer asked to start addressing the TODO problems while the pipeline was running.*
- *Files changed: `workflow/libraries/aggregate_alignment_scores.py`, `workflow/llm_mind_alignment/Snakefile`, `workflow/llm_mind_alignment/scripts/aggregate_all_p_value_outputs.py`, `workflow/llm_llm_alignment/Snakefile`, `workflow/llm_llm_alignment/scripts/aggregate_all_llm_llm_p_value_outputs.py`, `README.md`, `docs/reference/2026-10-01_0926_clean_run_duration.md`.*
- *Review status: not yet reviewed by the developer.*
