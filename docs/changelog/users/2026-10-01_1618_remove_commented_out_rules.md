# 2026-10-01 — Old, disabled pipeline steps removed from the code

Two pipeline steps had been switched off long ago but were still in the Snakefiles as comments:
one that built `results/tsv_summary.tsv` and one that built `…observed.tsv` files. Both have been
replaced by `results/all_model_brain_alignment_scores.tsv`. Their leftover code is now deleted.

Nothing changes when you run the pipeline: no step reruns and no result changes.

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-01, Claude Opus 5.5: written for TODO entry S29 item 3 (Snakefile part), approved by the developer on 2026-09-30; implemented after the developer asked to do the parts of S29 that do not interfere with the running S34 check.*
- *Files changed: `workflow/Snakefile`, `workflow/llm_mind_alignment/Snakefile`.*
- *Review status: not yet reviewed by the developer.*
