# 2026-10-01 — The two summary tables are built faster

The steps that build `results/all_model_brain_alignment_scores.tsv` and
`results/all_model_model_alignment_scores.tsv` now use 4 processor cores instead of one, and skip
a check that could never fail. The model-model table took 4 h 10 min on node5; it should now take
about 1 h. The model-brain table should drop from about 16 min to about 5 min.

The tables themselves are exactly the same (checked byte for byte).

**What to do:** nothing special. The next time you run the pipeline, these two steps (and the plots
that use the tables) run once more. Give Snakemake at least `--cores 4`, as usual, so they run at
full speed.

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-01, Claude Opus 5.5: written for TODO entry S34, approved by the developer on 2026-10-01 and revised after measurement, after the developer asked to start addressing the TODO problems while the pipeline was running.*
- *Files changed: `workflow/libraries/aggregate_alignment_scores.py`, `workflow/llm_mind_alignment/Snakefile`, `workflow/llm_mind_alignment/scripts/aggregate_all_p_value_outputs.py`, `workflow/llm_llm_alignment/Snakefile`, `workflow/llm_llm_alignment/scripts/aggregate_all_llm_llm_p_value_outputs.py`, `README.md`, `docs/reference/2026-10-01_0926_clean_run_duration.md`.*
- *Review status: not yet reviewed by the developer.*
