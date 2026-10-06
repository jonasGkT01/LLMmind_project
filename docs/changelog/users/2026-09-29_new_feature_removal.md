# 2026-09-29 — changes for users

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../../AI_USAGE.md).*

Changes made on this day, in order:

- Model-level alignment plot now shows the "chance" line (new_feature)
- Gemma 3n and Gemma 4 now read text only (removal)
- Plots now show language vs vision, and are more colourblind-friendly (new_feature)
- All language models now read text in pieces of the same size (new_feature)
- Gemma 4 26B A4B removed from the models (removal)

---

## Model-level alignment plot now shows the "chance" line

Kind: `new_feature`

### What changed

- **The model-level alignment plots** in
  `results/pictures/alignment_lineplots/` now have a grey dashed line. It
  shows the score a model would get **by pure chance**, meaning if its
  nearest neighbours were picked at random. The legend calls it
  "Null expectation (hypergeometric)".
- **The concept-level plots** in
  `results/pictures/concept_alignment_scatterplots/` already had this line.
  They have not changed.
- Every alignment plot now has a reference line:
  - raw scores: the chance level
  - enrichment: 1
  - Spearman: 0

### How to read it

- The chance level is *number of neighbours ÷ (number of concepts − 1)*.
  For example, 25 neighbours among 1000 concepts gives 25/999 ≈ 0.025.
- A model point **above** the line agrees with the brain data more than
  chance would. Whether the difference is significant is shown by the
  asterisks under each model.
- With few neighbours, the chance level is close to 0, and the model
  points usually sit just above it. On the 0–1 axis the gap can be hard to
  see. The **enrichment plots** (`alignment_enrichment_lineplots/`) show
  the same comparison on a clearer scale.

### What this means for you

- **Redraw the plots once to see the line.** Snakemake does not notice
  changes to plotting code by itself, so use the "redraw every plot"
  command in the README. No other step needs to rerun, and no numbers
  change.

### Context

- Basis: the change made in the same session at the developer's request, checked by drawing one real plot (caption_scene, cosine, 25 neighbours).

---

## Gemma 3n and Gemma 4 now read text only

Kind: `removal`

### What changed

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

### What you need to do

Nothing. Rerun the pipeline as usual. It picks up where it stopped, and
results that were already computed are kept.

### Context

- Basis: the change made in the same session at the developer's request, after the run crashed on Gemma 3n E2B with the NSD images. Checked with a Snakemake dry run.

---

## Plots now show language vs vision, and are more colourblind-friendly

Kind: `new_feature`

> **Update 2026-09-29 (later the same day):** multimodal model support has been
> removed, so the multimodal parts of this entry no longer apply. Gemma 3n and
> Gemma 4 now run as language models. See
> `2026-09-29_new_feature_removal.md`. *(Note added by Claude Code,
> Claude Opus 5.5, `claude-opus-5-5`.)*

### What changed

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

### What this means for you

- **Redraw the plots once to see the change.** Snakemake doesn't notice
  changes to plotting code; use the "redraw every plot" command in the README.
  No analysis needs to rerun.
- **Concept points are not colourblind-safe.** Each concept keeps its own
  colour, as before. With 11 to 1,000 concepts, no set of colours can be told
  apart by colourblind readers.
- **Adding a multimodal model.** The README's "Models" section explains how to
  switch on the Gemma models that are listed but commented out in
  `config/config.yaml`. Its "Outputs" section describes the colour code.

### Context

- Basis: the change made in the same session at the developer's request.

---

## All language models now read text in pieces of the same size

Kind: `new_feature`

### Why

Long texts, such as the Narratives stories, are cut into pieces
("chunks") before a language model reads them. Until now, each model chose
its own piece size: 8192 tokens for Gemma 1 and Gemma 2, and 2048 for all
the others. Two problems followed:

- The large Gemma 2 27B model ran out of GPU memory on node5 with 8192-token
  pieces, and the whole run stopped.
- The models were not compared under the same conditions, because piece
  size affects the embeddings.

### What changed

A new setting at the top of `config/config.yaml`:

```yaml
max_chunk_length: 2048
```

- **A number (default `2048`)**: every language model reads text in pieces
  of exactly that many tokens.
- **`null` or `"none"`**: the pipeline does not set a piece size. Each model
  goes back to choosing its own, as before this change (8192 for Gemma 1/2,
  2048 for the others). Use this only on purpose: the models are then no
  longer comparable, and Gemma 2 27B will run out of memory again.

Image models are not affected.

### What this means for you

- On the next run, all language-model embeddings, and everything built on
  them, are recomputed. This is expected.
- Snakemake will also want to recompute the image-model embeddings, even
  though they won't change. To skip that, start the next run once with:

  ```bash
  snakemake --use-conda --cores <N> --rerun-triggers mtime params input software-env
  ```

- Switching the model to 8-bit would not have fixed the crash. It would make
  the model too large for the GPU.

### Context

- Basis: the developer's question about the crash and their instructions in the same session.

---

## Gemma 4 26B A4B removed from the models

Kind: `removal`

### What happened

The pipeline stopped while loading Gemma 4 26B A4B. The model does not fit
on the 24 GB GPU of node5.

It is a "mixture-of-experts" model: most of it is made of many small expert
networks. The tool that shrinks large models to 4-bit (bitsandbytes)
cannot shrink those experts, so the model stays around 46 GB instead of
about 13 GB. This has nothing to do with the chunk-length change made
earlier the same day.

### What changed

- Gemma 4 26B A4B is commented out in `config/config.yaml`, with a note
  explaining why. It no longer appears in any result or plot.
- Its downloaded files (49 GB) were deleted from `resources/models/`.
- All other models were checked. None of them is a mixture-of-experts model,
  so none has this problem.

### What this means for you

- Nothing to do: just restart the pipeline.
- If you add a new model, check that it is not a mixture-of-experts model.
  The "Models" section of the README explains how.

### Context

- Basis: the developer's report of the crash and their instructions in the same session.
