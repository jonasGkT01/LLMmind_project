# 2026-10-01 — Dead `safe_pearsonr()` removed from `fmri_processing.py`

## Change

`workflow/libraries/fmri_processing.py`:

- `safe_pearsonr()` is deleted. It had no caller since `compute_leave_one_out_isc()` was
  vectorised (see `2026-09-22-nsd-scale-similarity-streaming-and-isc-speedup.md`).
- `from scipy.stats import pearsonr`, used only by it, is deleted.
- The `compute_leave_one_out_isc()` docstring no longer describes the function by reference to
  `safe_pearsonr()`. It now states what it computes: per parcel, the mean over subjects of the
  Pearson r between each subject's time course and the mean time course of the other subjects,
  with r = 0 for a constant signal.
- `is_constant_signal()` is kept: `compute_leave_one_out_isc()` uses it.

Not done, on purpose: computing the leave-one-out means as `(total − x_i)/(n − 1)`. It saves a
fraction of a second per task, but its different rounding would change the ISC values in their
last bits and force a full downstream recompute.

## Verification

`compute_leave_one_out_isc()` from the old (`HEAD`) and new module returned identical arrays
(`np.array_equal`) on random float32 data of shape 6 × 50 × 200 with one constant parcel.
No shell command changes, so nothing reruns.

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-01, Claude Opus 5.5: written for TODO entry S8, approved by the developer on 2026-09-30 and confirmed on 2026-10-01 ("start solving the problems that do not involve the aggregation code").*
- *Files changed: `workflow/libraries/fmri_processing.py`.*
- *Review status: not yet reviewed by the developer.*
