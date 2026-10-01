# 2026-10-01 — ISC NIfTI maps are no longer produced

The workflow used to save every stimulus's ISC values also as a brain map
(`results/mind/*/isc/*_isc_mean.nii.gz`, 2018 files, 1.3 GB). Nothing used these maps, so they are
no longer written. The ISC values themselves (`*_isc_mean.npy`) are exactly the same.

This change becomes active together with the next full rerun of the pipeline, because Snakemake
would otherwise recompute the whole downstream analysis just for it. The existing maps are deleted
at that point.

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-01, Claude Opus 5.5: written for TODO entry S7 (option B, approved by the developer on 2026-09-30); on 2026-10-01 the developer approved implementing it now and merging it only with the batched full rerun ("go on with S6, S7, S28, and S32").*
- *Files changed: `workflow/dataset_processing/narratives_dataset/Snakefile`, `workflow/dataset_processing/caption_scene_dataset/Snakefile`, `workflow/dataset_processing/nsd_data_dataset/Snakefile`, `workflow/dataset_processing/narratives_dataset/scripts/compute_narratives_isc.py`, `workflow/dataset_processing/caption_scene_dataset/scripts/compute_caption_scene_isc.py`, `workflow/dataset_processing/nsd_data_dataset/scripts/compute_nsd_isc.py`.*
- *Review status: not yet reviewed by the developer.*
