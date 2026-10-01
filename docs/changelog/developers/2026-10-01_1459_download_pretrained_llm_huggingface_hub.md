# 2026-10-01 — Model download works with current `huggingface_hub`

## Change

`workflow/llm_nearest_neighbours/scripts/download_pretrained_llm.py::download_model_repo()`: the
`local_dir_use_symlinks=False` keyword is removed from the `huggingface_hub.snapshot_download()`
call. The parameter was deprecated and is gone in the installed `huggingface_hub` 1.31.0, which
rejects unknown keyword arguments, so the next download (a new model, or a re-download after an
environment rebuild) would have raised a `TypeError`. With `local_dir` set, current versions write
real files into `local_dir`, which is what the removed argument requested.

The `download_pretrained_llm` rule's shell command and its `directory()` output are unchanged, so
nothing reruns. Existing models in `resources/models/` are untouched.

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-01, Claude Opus 5.5: written for TODO entry S25, approved by the developer on 2026-09-30 and confirmed on 2026-10-01 ("start solving the problems that do not involve the aggregation code").*
- *Files changed: `workflow/llm_nearest_neighbours/scripts/download_pretrained_llm.py`.*
- *Review status: not yet reviewed by the developer.*
