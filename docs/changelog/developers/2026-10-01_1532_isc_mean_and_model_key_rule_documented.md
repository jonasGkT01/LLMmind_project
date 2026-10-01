# 2026-10-01 — ISC averaging and the model-key naming rule are documented

No code or numerical change; nothing reruns.

- **ISC averaging (TODO S11):** `libraries/fmri_processing.py::compute_leave_one_out_isc()` keeps
  the arithmetic mean of the per-subject r values. `docs/reference/fmri_preprocessing.md`, step 6,
  now states this and why Fisher-z averaging was rejected: with the 3- and 6-volume windows of NSD and
  Caption Scene, r is often near ±1, where `arctanh` explodes (≈ 7.25 at r = 0.999999) and the z
  standard error `1/sqrt(n − 3)` is undefined for n = 3; for Narratives and Nature Stories the two
  means barely differ; and the downstream top-k similarities are hardly affected by a small
  shrinkage.
- **Model family (TODO S14):** `libraries/manage_model_metadata.py::model_family()` stays
  `model.rsplit("_", 1)[0]`. The rule it relies on, `<family>_<size>` with no `_` in the size, is now
  a comment above `models:` in `config/config.yaml`. A key such as `gemma3_1b_it` would break it.

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-01, Claude Opus 5.5: written for TODO entries S11 (option b) and S14 (option B), approved by the developer on 2026-09-30; implemented on 2026-10-01 after the developer asked which solutions could be done while the S34 check was running ("proceed").*
- *Files changed: `docs/reference/fmri_preprocessing.md`, `config/config.yaml`.*
- *Review status: not yet reviewed by the developer.*
