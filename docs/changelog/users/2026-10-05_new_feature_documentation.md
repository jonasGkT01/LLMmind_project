# 2026-10-05 — changes for users

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../../AI_USAGE.md).*

Changes made on this day, in order:

- Manifests and summary tables are rebuilt when their code changes (new_feature)
- README now describes the ISC as it is computed (documentation)

---

## 12:00 — Manifests and summary tables are rebuilt when their code changes

Kind: `new_feature`

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

### Context

- Request: Written after the developer asked why the 2026-10-02 run crashed and then asked that the rules producing manifests or collecting outputs always run; the approved solution reruns them when their code changes instead.
- Files changed: `workflow/libraries/code_version.py` (new), the dataset, alignment and ISC Snakefiles, `README.md`.

---

## 14:17 — README now describes the ISC as it is computed

Kind: `documentation`

The README said that every presentation of a stimulus, including a subject seeing it twice, counts
as a separate observation in the inter-subject correlation (ISC). Since 2 October this is no longer
true: when a subject saw a stimulus more than once, those responses are first averaged, so the ISC
compares subjects, not presentations. The README now says so. Nature Stories is unaffected, since
each subject heard each story once.

Two references to the code file that holds the ISC functions were also corrected
(`libraries/compute_isc.py`).

Nothing changes in the results, and there is nothing to rerun.

### Context

- Request: Written after the developer approved the README fix of TODO P39/S39 while reviewing the open TODO entries one at a time.
- Files changed: `README.md`.
