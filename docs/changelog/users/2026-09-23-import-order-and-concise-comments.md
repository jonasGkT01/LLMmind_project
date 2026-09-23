# 2026-09-23 — Tidier code, same results

## What changed

This is a housekeeping update to the project's Python scripts. It makes
them easier to read. It does not change what they do.

- **Consistent layout at the top of every script.** Each script lists the
  tools it relies on at the top. That list now always follows the same
  order: Python's built-in tools first, then general data tools (such as
  NumPy and pandas), then brain-imaging and language-model tools, and
  finally the project's own helpers.
- **Shorter explanatory notes.** Many scripts contain notes explaining why
  something is done a certain way. The longer ones have been cut down to
  a line or two, keeping the reason and dropping the extra detail.
- **Cleaner project history.** Python leaves behind temporary helper files
  when it runs. The project is now set up so these can never be saved into
  its history by accident.

## What this means for you

- Nothing changes in how you run the pipeline or in the results it
  produces.
- There is no need to rerun anything.

## Action needed

None.

---

*AI disclosure: this note was written by an AI coding assistant.*

- *Tool: Claude Code (Anthropic), VS Code extension.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`, 1M-token context).*
- *Date: 2026-09-23.*
- *Basis: the developer's (Jonas Salvalaggio) instructions in the same
  session.*
- *Review status: not yet reviewed by the developer at the time of writing.*

*The developer changelog entry of the same name lists exactly what was
changed and checked.*
