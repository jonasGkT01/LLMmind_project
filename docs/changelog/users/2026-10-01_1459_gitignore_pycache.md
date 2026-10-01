# 2026-10-01 — Python cache folders no longer show up in git

The `__pycache__/` folders that Python creates when you run a script are now ignored by git
wherever they appear, not only in `workflow/libraries/`. They no longer appear as untracked
files in `git status`. Nothing else changes.

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-01, Claude Opus 5.5: written for TODO entry S5, approved by the developer on 2026-09-30 and confirmed on 2026-10-01 ("start solving the problems that do not involve the aggregation code").*
- *Files changed: `.gitignore`.*
- *Review status: not yet reviewed by the developer.*
