# 2026-09-25 — Multimodal models are now compared with themselves across text and images

## What changed

- **New model-vs-model comparisons.** A multimodal model (one with
  `modality: "multimodal"` in `config/config.yaml`) is now compared with
  itself: its neighbourhoods from the text stimuli against its neighbourhoods
  from the image stimuli. Example output:
  `results/alignment_scores/dataset-caption_scene_model-gemma3n_e4b-language_model-gemma3n_e4b-vision_cosine-alignment_score_25NN.parquet`,
  plus the matching `_empirical_..._p_value.tsv`.
- **Only datasets with both text and images are affected.** Today that is
  `caption_scene`.
- **Nothing else changes.** Every comparison that existed before is still
  made, and keeps the same file name.

## What this means for you

- **No effect with the current configuration.** None of the enabled models
  is multimodal. The new comparisons appear once you uncomment the
  Gemma 3n / Gemma 4 models.
- **The model-vs-model heatmaps don't show these comparisons yet.** They name
  rows and columns by model only, not by model plus stimulus type. With a
  multimodal model enabled, the p-value heatmap will stop with a
  "provided more than once" error. The score files themselves are correct.

---
*AI disclosure: this note was written by an AI coding assistant.*

- *Tool: Claude Code (Anthropic), VS Code extension.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Date: 2026-09-25.*
- *Basis: the change made in the same session at the developer's request.*
- *Review status: not yet reviewed by the developer at the time of writing.*

*The developer changelog entry of the same name has the technical details.*
