# 2026-10-01 — `.gitignore` ignores Python bytecode everywhere

## Change

`.gitignore`: the entry `workflow/libraries/__pycache__/` is replaced by `__pycache__/`, which
matches a `__pycache__/` directory at any depth. Before, running a script outside
`workflow/libraries/` (for example `workflow/visualisation/scripts/`) left an untracked
`__pycache__/` that could be committed by mistake.

No `*.py[cod]` pattern is added: Python 3 writes bytecode only inside `__pycache__/`.
`git ls-files | grep -E '__pycache__|\.pyc$'` printed nothing before the change, so no tracked
file is affected.

No rule or output changes; nothing reruns.

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-01, Claude Opus 5.5: written for TODO entry S5, approved by the developer on 2026-09-30 and confirmed on 2026-10-01 ("start solving the problems that do not involve the aggregation code").*
- *Files changed: `.gitignore`.*
- *Review status: not yet reviewed by the developer.*
