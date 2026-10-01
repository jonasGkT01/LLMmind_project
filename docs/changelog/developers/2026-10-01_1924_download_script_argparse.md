# 2026-10-01 — `download_pretrained_llm.py` uses argparse

## Changes

- `workflow/llm_nearest_neighbours/scripts/download_pretrained_llm.py`: replaced the `sys.argv`
  handling (two positional arguments, and a usage message with the stale path
  `workflow/scripts/...`) with `argparse`: required `--model_name` (Hugging Face repository ID) and
  `--save_dir`. Removed `download_model_repo()`; `main()` calls
  `snapshot_download(repo_id = ..., local_dir = ...)` directly. `--help` now works like in the
  other scripts.
- Rule `download_pretrained_llm` (`workflow/llm_nearest_neighbours/Snakefile`): passes
  `--model_name {params.hf_name:q}` and `--save_dir {output.model_dir:q}`.

## Rerun impact

The rule's shell command changed, so with Snakemake's default rerun triggers all 38
`download_pretrained_llm` jobs, and through their outputs the whole pipeline, rerun. That is why
this change sits on the branch `s37-download-argparse` and is merged only together with the S22
full rerun (TODO S37), like S7. With `--rerun-triggers mtime` nothing reruns.

## Verification

In the rule's conda environment: `--help` prints both options; a missing `--save_dir` exits
with an argparse error; the command rendered by `snakemake -n -p` for `bloom_560m`, run with
`snapshot_download` replaced by a stub, calls it with
`repo_id = "bigscience/bloomz-560m", local_dir = "resources/models/bloom_560m"`, as before.

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-01, Claude Opus 5.5: written for TODO entry S37, option (b) chosen by the developer on 2026-10-01 ("switch the script to argparse"), after the post-merge check found the stale usage path.*
- *Files changed: `workflow/llm_nearest_neighbours/scripts/download_pretrained_llm.py`, `workflow/llm_nearest_neighbours/Snakefile`.*
- *Review status: not yet reviewed by the developer.*
