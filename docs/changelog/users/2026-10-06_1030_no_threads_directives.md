# 2026-10-06 — No step reserves several cores any more

The run of 5 October stopped making progress overnight. Three small jobs had finished their work
but never closed, so they kept 3 of the 4 cores busy. The next step, the NSD parcel extraction,
asked for all 4 cores at once, so it waited forever.

Now no step asks Snakemake for more than one core. The few steps that work in parallel internally
(NSD parcel extraction, Caption Scene T1w registration and the two final summary tables) take
their number of workers from a new setting in `config/config.yaml`:

```yaml
number_of_workers: 4
```

What to know:

- Launch the pipeline as usual, e.g. `snakemake --use-conda --cores 4 --resources gpu=1`.
- While one of these steps runs next to other jobs, the run can briefly use more CPUs than
  `--cores`. Lower `number_of_workers` if that is a problem.
- The Caption Scene registration now uses 4 threads instead of 8.
- This change adds no extra work to the run in progress: relaunching it still has the same 4,195
  jobs left to do.

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-06, Claude Opus 5.5: written after the developer asked why the run had stalled since 01:00 and then asked to remove every rule's core specification.*
- *Files changed: `config/config.yaml`, the NSD, Caption Scene, LLM-brain and LLM-LLM Snakefiles, `README.md`, `docs/reference/clean_run_duration.md`.*
- *Review status: not yet reviewed by the developer.*
