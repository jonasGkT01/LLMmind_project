# 2026-09-23 — Repository cleanup and corrections to the previous note

## What changed

**Cleanup.** When Python runs, it saves helper files (in folders called
`__pycache__`) to start faster next time. A few of these were stored in
the project history by mistake. They are gone, and the project is now set
up so they can't be added again.

**Corrections to the
[previous note](2026-09-23-long-text-chunking-and-constant-signal-check.md).**
That note described two fixes. The fixes themselves still stand, but three
things it said were not accurate:

- **Short texts can change too.** It said only long texts were affected.
  In fact, texts just short enough to fit in one piece were also given an
  unnecessary second piece before, so their results can shift as well.
  Images are still unaffected.
- **Not every part of a text counts equally.** Long texts are still cut
  into overlapping pieces, so the parts where two pieces overlap still
  count a little more than the very start and end of the text. The fix
  only removed the extra repeated piece at the end.
- **"Flat" is a small tolerance, not a perfect test.** A brain region still
  gets a score of zero if its signal barely moves, even if the movement is
  real. The margin is tiny (about one part in a million of the signal's
  size), but it is a choice, not a mathematical certainty. Whether to keep
  it will be decided after checking real data.

## What this means for you

- Your results do not change because of this note: no analysis code was
  touched.
- If you rerun embeddings as the previous note suggested, expect some
  short texts to change as well as long ones.

## Action needed

None beyond the rerun already described in the previous note.

---

*AI disclosure: this note was written by an AI coding assistant.*

- *Tool: Claude Code, VS Code extension.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`, 1M-token context).*
- *Date: 2026-09-23.*
- *Basis: an external review of the project and the developer's
  instructions (Jonas Salvalaggio) in the same session.*
- *Review status: not yet reviewed by the developer at the time of writing.*

*The developer changelog entry of the same name lists exactly what was
changed and checked.*
