# 2026-09-29 — Gemma 3n and Gemma 4 now read text only

## What changed

- **The pipeline no longer crashes on the Gemma 3n and Gemma 4 models.** The
  run stopped when Gemma 3n E2B tried to read the NSD images. These models
  can only read an image when it comes with a short text prompt, and the
  pipeline sends images alone.
- **These seven models are now language models.** In `config/config.yaml`,
  Gemma 3n E2B / E4B and Gemma 4 E2B / E4B / 12B / 26B A4B / 31B are set to
  `modality: "language"`. They are compared with the brain on text stimuli
  only, like the other Gemma models.
- **"multimodal" is no longer a valid modality.** A model is either
  `language` (runs on text) or `vision` (runs on images). A model is no
  longer compared with itself across text and images.
- **Plots look the same.** Models are still labelled as
  `<model>-<stimulus type>`, with the same colours.

## What you need to do

Nothing. Rerun the pipeline as usual. It picks up where it stopped, and
results that were already computed are kept.

---
*AI disclosure: this entry was written by an AI coding assistant.*

- *Tool: Claude Code (Anthropic), VS Code extension.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Date: 2026-09-29.*
- *Basis: the change made in the same session at the developer's request,
  after the run crashed on Gemma 3n E2B with the NSD images. Checked with a
  Snakemake dry run.*
- *Review status: not yet reviewed by the developer at the time of writing.*

*The developer changelog entry of the same name has the technical details.*
