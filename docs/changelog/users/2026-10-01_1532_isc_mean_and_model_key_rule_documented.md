# 2026-10-01 — Two methods details written down

- `docs/reference/fmri_preprocessing.md` (step 6) now says that the ISC is averaged over subjects
  as a plain mean of correlation values, without a Fisher z-transform, and why. Use it for the
  methods section.
- `config/config.yaml` now explains how model names must be built: `<family>_<size>`, where the
  size has no underscore (for example `clip_i21k_ft_b` is family `clip_i21k_ft`, size `b`). Follow
  it when you add a model, because the figures group and order models by this family.

Nothing changes in the results.

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-01, Claude Opus 5.5: written for TODO entries S11 (option b) and S14 (option B), approved by the developer on 2026-09-30; implemented on 2026-10-01 after the developer asked which solutions could be done while the S34 check was running ("proceed").*
- *Files changed: `docs/reference/fmri_preprocessing.md`, `config/config.yaml`.*
- *Review status: not yet reviewed by the developer.*
