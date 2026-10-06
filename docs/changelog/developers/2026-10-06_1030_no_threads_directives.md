# 2026-10-06 — `threads:` removed from every rule; internal workers from `number_of_workers`

## Problem

The run started on 2026-10-05 at 09:49 stalled at 38,484 of 42,679 steps. Three
`compute_llm_llm_hypergeometric_p_value` jobs had written their complete output but their Python
process never exited (main thread blocked in `futex`), so Snakemake kept 3 of the 4 cores
reserved for them. Every remaining job depended on `assemble_nsd_bold`, which declared
`threads: workflow.cores` (4) and so could never be scheduled on the single free core. Snakemake
looped on job selection from 01:06 until the jobs were killed at about 09:55.

## Changes

- `config/config.yaml`: new top-level key `number_of_workers: 4`.
- The `threads:` directive was removed from the four rules that had one. Each now takes
  `params: number_of_workers = config["number_of_workers"]` and passes it where it used
  `{threads}`:
  - `assemble_nsd_bold` (`workflow/dataset_processing/nsd_data_dataset/Snakefile`): was
    `workflow.cores`; `--jobs {params.number_of_workers}`.
  - `register_caption_scene_t1w` (`workflow/dataset_processing/caption_scene_dataset/Snakefile`):
    was 8 (capped by Snakemake at `--cores`); `antsRegistrationSyNQuick.sh -n
    {params.number_of_workers}`.
  - `aggregate_all_p_value_outputs` (`workflow/llm_mind_alignment/Snakefile`) and
    `aggregate_all_llm_llm_p_value_outputs` (`workflow/llm_llm_alignment/Snakefile`): were 4;
    `--threads {params.number_of_workers}`.
- No script changed: `assemble_nsd_bold.py --jobs` and the aggregators' `--threads` keep their
  names and meaning.

## Behaviour

- Snakemake now counts every job as one core, so no job waits for several free cores. The four
  rules above may use up to `number_of_workers` CPUs while counted as one, so the run can briefly
  exceed `--cores` (e.g. 4 + 3 = 7 busy processes on node5's 4-CPU Slurm allocation).
- No extra reruns: none of the four rules had produced its output in the current rerun yet
  (`register_caption_scene_t1w` outputs are missing, `assemble_nsd_bold` and the aggregations
  were still queued), so the new param and shell commands add no job.
- Not addressed: why the three hypergeometric jobs hung at exit.

## Verification

- `grep` finds no `threads:` or `workflow.cores` left in the project's Snakefiles.
- `snakemake --use-conda --cores 4 --resources gpu=1 --rerun-incomplete -n --quiet rules` on the
  frontend parses the workflow and schedules 4,195 jobs, the same number the stalled run still had
  to do, among them the 3 killed hypergeometric jobs, `assemble_nsd_bold`, the 8
  `register_caption_scene_t1w` jobs and 795 `extract_caption_scene_run_parcels` jobs (more are
  added after the Caption Scene checkpoint).

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-06, Claude Opus 5.5: written after the developer asked why the run had stalled since 01:00 and then asked to remove every rule's core specification; the developer chose a fixed worker count from the config over running these steps single-process.*
- *Files changed: `config/config.yaml`, `workflow/dataset_processing/nsd_data_dataset/Snakefile`, `workflow/dataset_processing/caption_scene_dataset/Snakefile`, `workflow/llm_mind_alignment/Snakefile`, `workflow/llm_llm_alignment/Snakefile`, `README.md`, `docs/reference/clean_run_duration.md`.*
- *Review status: not yet reviewed by the developer.*
