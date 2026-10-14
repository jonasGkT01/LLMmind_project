# 2026-10-14 — developer changelog

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../../AI_USAGE.md).*

Changes made on this day, in order:

- `docs/AI_USAGE.md` no longer lists the TODO and SUGGESTIONS files (documentation)

---

## 12:13 — `docs/AI_USAGE.md` no longer lists the TODO and SUGGESTIONS files

Kind: documentation

The table in `docs/AI_USAGE.md` listed `../.claude/TODO/LLMmind_project.md` and
`../.claude/SUGGESTIONS/LLMmind_project.md`, which live in `LLMmind/.claude/`, outside the
project folder. Both rows and the sentence introducing them were removed; the table now lists only
files inside `LLMmind_project/`. The TODO and SUGGESTIONS files keep a one-line AI note under their
title, now without a link to `docs/AI_USAGE.md`. The rule in `LLMmind/.claude/CLAUDE.md`
(sections 1, 3 and 6) was changed to match.

### Context

- Request: the developer noted that `AI_USAGE.md` tracked files in `.claude/`, which is outside the
  project, and asked to stop doing so and remove those rows.
- Files changed: `docs/AI_USAGE.md`. Outside the project: `LLMmind/.claude/CLAUDE.md`,
  `LLMmind/.claude/TODO/LLMmind_project.md`, `LLMmind/.claude/TODO/public_datasets.md` (old
  end-of-file attribution block replaced by the one-line note),
  `LLMmind/.claude/SUGGESTIONS/LLMmind_project.md`.
- Verified: `grep` finds no reference to `.claude/`, `TODO/` or `SUGGESTIONS/` in any
  `AI_USAGE.md`.
