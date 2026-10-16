# 2026-10-15 — developer changelog

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../../AI_USAGE.md).*

Changes made on this day, in order:

- Hemodynamic delay of the event windows documented as a limitation (documentation)

---

## 15:26 — Hemodynamic delay of the event windows documented as a limitation

Kind: documentation

`docs/reference/fmri_preprocessing.md` has a new section "Limitation: the hemodynamic delay" and a
pointer to it in step 2. The event windows of NSD (`onset_shift_volumes: 0`, 3 volumes) and
Caption Scene (`onset_shift_s: 0`, 6 volumes) start at the stimulus onset, with no allowance for
the BOLD delay (peak about 5–6 s). NSD trials are 3 volumes apart, so its window mostly covers the
response to the preceding trials. Measured from `nsd_occurrence_manifest.tsv` and the design
files (the design entry at `onset_vol - 3`): the preceding trial is a subject-specific image for
81.1% of the retained presentations, a shared image for 9.5% and blank for 9.4%; 919 of the 1000
shared images have their first presentation at the same session, run and volume in all subjects,
but only 178 have the same preceding trial in all subjects. The developer decided not to shift
the windows or model the response (the delay of each response cannot be known exactly) and to
report it as a limitation. No code, config or result changed.

### Context

- Request: while discussing SUGGESTIONS entry I13 (NSD single-trial betas), the zero onset shift
  was found; the developer chose to record it as a limitation instead of correcting it.
- Files changed: `docs/reference/fmri_preprocessing.md`.
- Verification: trial spacing and preceding trials computed with pandas/numpy from
  `results/mind/nsd_data/manifests/nsd_occurrence_manifest.tsv` and the `source_design` files it
  lists; Caption Scene trial structure from the dataset paper cited on the same page.
