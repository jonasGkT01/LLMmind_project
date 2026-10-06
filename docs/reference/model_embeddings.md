# Model embeddings: how each stimulus becomes one vector

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../AI_USAGE.md).*

This page describes how `workflow/llm_nearest_neighbours/scripts/get_embeddings.py` turns each
stimulus into one embedding vector per model. These vectors are the model-side representations
whose nearest neighbours are compared with the brain's. Use it as the source for the methods
section. For how to *configure* the chunk length, see section 3 of
[`running_and_troubleshooting.md`](../guides/running_and_troubleshooting.md).

## 1. Stimuli

- One file per stimulus in the dataset's `stimuli_dir` (`config/config.yaml`), read in sorted
  file-name order. The stimulus name is the file name without its extension.
- Stimuli listed in the dataset's `excluded_stimuli` file are skipped. The ISC side applies the
  same file, so both sides cover exactly the same stimuli (checked when the alignment is computed).
- Text stimuli are `.txt` files, read as UTF-8. Image stimuli are `.bmp`, `.jpeg`, `.jpg`, `.png`,
  `.tif`, `.tiff` or `.webp` files. A directory must contain only one of the two kinds.

## 2. Loading the models

- Every model is loaded with `transformers.AutoModel` (the base model, without any language-model,
  classification or projection head) from the local copy in `resources/models/{model}`.
- Weights are loaded in the dtype stored in the checkpoint (`dtype="auto"`), except for the models
  with a `quantization_method` in the config. These are loaded with `bitsandbytes`, in 8 bit
  (`gemma2_9b`, `gemma3_12b`, `gemma4_12b`, `openllama_13b`) or 4 bit (`gemma2_27b`, `gemma3_27b`,
  `gemma4_31b`), so that they fit on one 24 GB GPU.
- All forward passes run in inference mode. Each vector is stored as `float32`.

## 3. Language models (text stimuli)

1. **Tokenisation.** The whole text is tokenised once, without special tokens.
2. **Chunks.** The tokens are split into chunks of at most `max_chunk_length − 1` tokens
   (`max_chunk_length` = 2048 in the config, the same for every language model), overlapping by
   256 tokens. Chunking stops at the first chunk that reaches the end of the text, so a text that
   fits in one chunk gets exactly one.
3. **BOS token.** If the tokenizer defines a beginning-of-sequence (BOS) token, it is added in
   front of every chunk, so each chunk has at most `max_chunk_length` tokens. All the configured
   tokenizers (BLOOMZ, Gemma 1–4, OpenLLaMA) define one.
4. **Chunk vector.** The chunk is run through the model, and its vector is the **mean of the last
   layer's hidden states over all its tokens, including the BOS token**.
5. **Stimulus vector.** The mean of the chunk vectors, weighted by the number of text tokens in
   each chunk (the BOS token is not counted). Tokens in an overlap therefore contribute to two
   chunks.

The number of tokens and chunks of each stimulus is stored in the `n_tokens` and `n_chunks`
columns of the embeddings file.

**Caveat: the BOS token is included in the mean.** In many decoder models, Gemma and
Llama-style models in particular, the hidden state at the first position (here the BOS token) is
an outlier: it acts as an "attention sink" and can have a much larger norm than the other tokens.
Averaging over all tokens, BOS included, can therefore pull every stimulus vector toward the same
direction. The effect is largest for short texts, where the BOS is one of few tokens, and for the
first chunk of each text. It shrinks as texts get longer. Every stimulus of a model gets the same
treatment, but a shared offset still compresses the similarities between stimuli, and none of
the three similarity types removes it. Excluding the BOS
position from the mean would change every language-model embedding and every result downstream,
so it has not been done. The manuscript's methods state that the BOS token is included.

## 4. Vision models (image stimuli)

1. The image is converted to RGB and prepared by the model's own image processor
   (`AutoProcessor`: resizing, cropping and normalisation as defined for that checkpoint).
2. The vector is the **first (CLS) token of the last layer's hidden states**, after the model's
   final normalisation layer (`get_embeddings.py --pool` can override this; the workflow does
   not pass it):
   - CLIP, CLIP fine-tuned on ImageNet-12k, and the ImageNet-21k ViTs are `timm` checkpoints,
     loaded through the `transformers` timm wrapper with its head removed. The hidden states are
     timm's `forward_features()` output, so the CLIP projection and the classification heads
     are **not** applied.
   - DINOv2 is loaded as `Dinov2Model`. Its CLS token after the final layer norm is the same
     vector as its `pooler_output`.

## 5. From vectors to neighbours

The embeddings file holds one row per stimulus. `compute_llm_nearest_neighbours.py` then
normalises the vectors for the chosen similarity (L2 for cosine, centring + L2 for Pearson, ranks
+ centring + L2 for Spearman), and keeps the largest configured k nearest neighbours of each
stimulus, excluding the stimulus itself.

## 6. Sources

The content comes from the code (`get_embeddings.py`, `compute_similarity.py`,
`compute_nearest_neighbours.py`, `config/config.yaml`) and from the installed `transformers`
source (`modeling_timm_wrapper.py`, `modeling_dinov2.py`). The ImageNet-12k fine-tuning of the
`clip_i21k_ft_*` models was checked on the Hugging Face model card of
`timm/vit_base_patch16_clip_224.laion2b_ft_in12k` (an 11,821-class subset of ImageNet-22k).
**Not verified:** the size of the BOS outlier in these specific models was not measured.

## Changes

Changes to this page, oldest first. The sections above always describe the current code.

### 2026-09-30 — page written

Written to document the BOS-token pooling, after a project review found it.

### 2026-10-06 16:30 — sources moved into the page

The sources and the "not verified" note of the old attribution block became section 6, and the
block was replaced by the note under the title. The `--pool` option (from `README.md`) is now
mentioned in section 4, and the chunk-length link points to the new guide.
