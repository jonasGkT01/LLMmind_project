# 2026-09-29 — Plots now show language vs vision, and are more colourblind-friendly

> **Update 2026-09-29 (later the same day):** multimodal model support has been
> removed, so the multimodal parts of this entry no longer apply. Gemma 3n and
> Gemma 4 now run as language models. See
> `2026-09-29-remove-multimodal-model-support.md`. *(Note added by Claude Code,
> Claude Opus 5.5, `claude-opus-5-5`.)*

## What changed

- **Every model is labelled with its stimulus type**, for example
  `clip_b-vision` or `bloom_560m-language`. When multimodal models (Gemma 3n,
  Gemma 4) are enabled, `caption_scene` shows two entries per model, one for
  each stimulus type.
- **Model names are colour-coded by stimulus type**, in every plot:
  - **Language**: dark red-orange.
  - **Vision**: dark green.
  - The **brain** stays black.
  - In the model-level line plots, the points also take the colour, and
    language points are **circles** while vision points are **squares**.
  - Boxes and concept points look the same as before.
- **Colourblind-friendly colours.** The usual orange and green look almost the
  same to people with red-green colour blindness, so the pair was checked with
  a colour-blindness simulation. The shades used here stay clearly different
  under every common type of colour blindness, and are dark enough to read as
  text. The `-language` / `-vision` ending also tells them apart, so you never
  need to rely on colour.
- **Other colour fixes:**
  - The **q-value asterisks** are now **blue** (they were red, which looks
    like black to some colourblind readers).
  - The **"degenerate box" diamond** is now **black** with a white outline.
  - The dashed family separators are grey.
- **Heatmaps:** the colour bar no longer overlaps the end of the title.
- **Model-vs-model heatmaps now work with multimodal models.** Before, the
  p-value heatmap failed and the score heatmap merged the language and vision
  results.
- **Image embeddings from multimodal models are now meaningful.** Before this
  fix, every image would have received essentially the same embedding.

## What this means for you

- **Redraw the plots once to see the change.** Snakemake doesn't notice
  changes to plotting code; use the "redraw every plot" command in the README.
  No analysis needs to rerun.
- **Concept points are not colourblind-safe.** Each concept keeps its own
  colour, as before. With 11 to 1,000 concepts, no set of colours can be told
  apart by colourblind readers.
- **Adding a multimodal model.** The README's "Models" section explains how to
  switch on the Gemma models that are listed but commented out in
  `config/config.yaml`. Its "Outputs" section describes the colour code.

---
*AI disclosure: this note was written by an AI coding assistant.*

- *Tool: Claude Code (Anthropic), VS Code extension. The colours were checked
  with an automated colour-blindness simulation.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Date: 2026-09-29.*
- *Basis: the change made in the same session at the developer's request.*
- *Review status: not yet reviewed by the developer at the time of writing.*

*The developer changelog entry of the same name has the technical details.*
