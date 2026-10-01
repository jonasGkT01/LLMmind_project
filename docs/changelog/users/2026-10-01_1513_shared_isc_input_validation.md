# 2026-10-01 — ISC scripts share one input check; Narratives reports truncation

The four scripts that compute the inter-subject correlation (ISC) for Narratives, Caption Scene,
Nature Stories and NSD now load and check their input files with the same code. In practice:

- The ISC values are exactly the same as before, and nothing needs to be rerun.
- Narratives used to shorten all subjects of a story to the shortest run without saying so. It now
  writes to the job log which files were shortened and from which length.
- Narratives now also stops with an error if a parcel file has the wrong shape, as the other
  datasets already did.

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-01, Claude Opus 5.5: written for TODO entry S6, approved by the developer on 2026-09-30; the implementation plan was approved on 2026-10-01 ("go on with S6, S7, S28, and S32").*
- *Files changed: `workflow/libraries/fmri_processing.py`, `workflow/dataset_processing/narratives_dataset/scripts/compute_narratives_isc.py`, `workflow/dataset_processing/caption_scene_dataset/scripts/compute_caption_scene_isc.py`, `workflow/dataset_processing/nature_stories_dataset/scripts/compute_nature_stories_isc.py`, `workflow/dataset_processing/nsd_data_dataset/scripts/compute_nsd_isc.py`.*
- *Review status: not yet reviewed by the developer.*
