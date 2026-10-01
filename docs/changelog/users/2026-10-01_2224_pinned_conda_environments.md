# 2026-10-01 — Fixed software versions for every pipeline step

Every software package the pipeline installs now has a fixed version, so rebuilding the
environments (on another machine, or after deleting `.snakemake/conda/`) gives the same
software and the same results. The versions are the latest available on 2026-10-01, with
Python 3.14 everywhere. The README section "Pinned versions" lists the rules and explains how to
upgrade a package safely.

This also fixes a hidden problem: a newly built model-embedding environment would have crashed on
the GPU for the Gemma models. It only worked so far thanks to a file cached from an earlier run.

The new versions were checked against the current ones: the brain data processing, the
statistics, the embeddings (including the 8-bit and 4-bit Gemma models on node5) and a plot gave
the same results.

**What to do:** nothing yet. This change is kept apart and will be added for the next full rerun of
the pipeline, because changing the environments makes Snakemake redo every step. At that time the
Snakemake environment itself has to be rebuilt once by hand (see the README).

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-01, Claude Opus 5.5: written for TODO entry S22, approved by the developer.*
- *Files changed: all 11 `*_environment.yaml` files (`workflow/envs/`, `workflow/*/envs/`, `workflow/dataset_processing/*/envs/`), `README.md`.*
- *Review status: not yet reviewed by the developer.*
