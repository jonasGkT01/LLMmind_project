# 2026-10-15 — changes for users

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../../AI_USAGE.md).*

Changes made on this day, in order:

- Delay of the brain response documented as a limitation (documentation)

---

## 15:26 — Delay of the brain response documented as a limitation

Kind: documentation

The fMRI signal reacts to a stimulus only a few seconds after it appears. For the two image
datasets, the time windows used to measure each image start when the image appears, so they do
not fully capture the response to it. For NSD, where a new image comes every 4 seconds, the
window mostly holds the response to the images shown just before. This is now described as a
limitation of the study in `docs/reference/fmri_preprocessing.md`, under "Limitation: the
hemodynamic delay". Nothing in the pipeline or its results changed.
