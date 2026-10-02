# 2026-10-02 — Narratives: excluded stories listed once, by reason

In `config/config.yaml`, the Narratives stories left out of the analysis are now listed only once,
in two groups that say why: `schema_subtasks` (the schema sub-stories) and `notthefall_variants`
(the two scrambled versions of "Not the Fall"). The third list, `problematic_subtasks`, which
repeated both groups, is gone; the pipeline combines the two groups itself. The excluded stories
are exactly the same as before. To exclude another story, add it to one of the two groups.

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-02, Claude Opus 5.5: written after the developer chose to keep the two reason lists separate and derive the exclusion list from them.*
- *Files changed: `config/config.yaml`, `workflow/dataset_processing/narratives_dataset/Snakefile`, `docs/reference/fmri_preprocessing.md`.*
- *Review status: not yet reviewed by the developer.*
