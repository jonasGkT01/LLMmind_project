# 2026-10-01 — Model download fixed for the installed `huggingface_hub`

Downloading a new model (rule `download_pretrained_llm`) would have crashed with the installed
version of `huggingface_hub`, because the script passed an option that no longer exists. The option
is removed. Models already in `resources/models/` are not affected and nothing is re-downloaded.

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-01, Claude Opus 5.5: written for TODO entry S25, approved by the developer on 2026-09-30 and confirmed on 2026-10-01 ("start solving the problems that do not involve the aggregation code").*
- *Files changed: `workflow/llm_nearest_neighbours/scripts/download_pretrained_llm.py`.*
- *Review status: not yet reviewed by the developer.*
