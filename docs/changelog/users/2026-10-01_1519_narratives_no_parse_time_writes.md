# 2026-10-01 — Snakemake commands no longer rewrite Narratives files

Every Snakemake command, even a dry run, used to rewrite 18 length-check files in
`results/mind/narratives/qc/` and a list of excluded scans in `resources/datasets/narratives_dataset/`.
Nothing used them, so they are no longer written, and the existing ones are deleted.

- Which Narratives runs are shortened, and from which length, now appears in the log of the
  `compute_narratives_isc` job.
- Which Narratives tasks are excluded, and why, is in `config/config.yaml` (`tasks`,
  `schema_subtasks`, `notthefall_variants`).
- `docs/reference/fmri_preprocessing.md` (step 5) explains why shortening the runs is safe.

Nothing needs to be rerun.

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-01, Claude Opus 5.5: written for TODO entries S28 and S32, approved by the developer on 2026-09-30; the implementation plan was approved on 2026-10-01 ("go on with S6, S7, S28, and S32").*
- *Files changed: `workflow/dataset_processing/narratives_dataset/Snakefile`, `config/config.yaml`, `docs/reference/fmri_preprocessing.md`.*
- *Review status: not yet reviewed by the developer.*
