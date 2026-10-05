# 2026-10-05 — Manifests and summary tables are rebuilt when their code changes

The run of 2 October stopped because a list of input files (the Narratives ISC manifest) had been
written months earlier by an older version of the code. The code had changed, but the pipeline
did not notice and kept the old file.

The steps that write these lists (manifests) and the steps that collect results into the final
summary tables now remember a fingerprint of the code that writes them. When that code changes,
the step runs again on the next launch, and so does everything that depends on it. Editing only
comments does not trigger a rerun.

What to know:

- Nothing to do in normal use: launch the pipeline as usual.
- If you launch with `--rerun-triggers mtime`, this check is switched off. To rebuild a manifest
  by hand, add `--forcerun <rule name>`, for example `--forcerun write_narratives_isc_manifest`.
- Changes to `config/config.yaml` that alter which files a manifest lists are not detected by
  this check.
- On the first run after this change, these steps run once more; this is part of the full
  recomputation already planned.

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-05, Claude Opus 5.5: written after the developer asked why the 2026-10-02 run crashed and then asked that the rules producing manifests or collecting outputs always run; the approved solution reruns them when their code changes instead.*
- *Files changed: `workflow/libraries/code_version.py` (new), the dataset, alignment and ISC Snakefiles, `README.md`.*
- *Review status: not yet reviewed by the developer.*
