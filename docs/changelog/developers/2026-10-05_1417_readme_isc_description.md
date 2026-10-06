# 2026-10-05 — README: ISC description and module references corrected

Documentation only; no code or result changes.

- `README.md`, inclusion rule: removed "every presentation (including repeats by the same subject)
  then counts as one fMRI observation in its ISC", outdated since the repeat averaging of
  2026-10-02 (`average_repeats_by_subject()`, called by `load_isc_inputs()` in
  `workflow/libraries/compute_isc.py` when `subjects` is given). The text now says each subject's
  repeats are averaged first. Narratives, NSD and Caption Scene pass `subjects`; Nature Stories does
  not, because `compute_nature_stories_isc.py` rejects duplicate subjects.
- `README.md`, overview: the leave-one-out ISC compares "each subject against the mean of the other
  subjects" (was "each observation").
- `README.md`: `is_constant_signal()` and the `compute_leave_one_out_isc` import of the code-layout
  example now point to `libraries/compute_isc.py` (were `libraries/fmri_processing.py`).

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-05, Claude Opus 5.5: written after the developer approved the README fix of TODO P39/S39 while reviewing the open TODO entries one at a time.*
- *Files changed: `README.md`.*
- *Review status: not yet reviewed by the developer.*
