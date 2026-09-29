# 2026-09-29 — Gemma 4 26B A4B removed from the models

## What happened

The pipeline stopped while loading Gemma 4 26B A4B. The model does not fit
on the 24 GB GPU of node5.

It is a "mixture-of-experts" model: most of it is made of many small expert
networks. The tool that shrinks large models to 4-bit (bitsandbytes)
cannot shrink those experts, so the model stays around 46 GB instead of
about 13 GB. This has nothing to do with the chunk-length change made
earlier the same day.

## What changed

- Gemma 4 26B A4B is commented out in `config/config.yaml`, with a note
  explaining why. It no longer appears in any result or plot.
- Its downloaded files (49 GB) were deleted from `resources/models/`.
- All other models were checked. None of them is a mixture-of-experts model,
  so none has this problem.

## What this means for you

- Nothing to do: just restart the pipeline.
- If you add a new model, check that it is not a mixture-of-experts model.
  The "Models" section of the README explains how.

---
*AI disclosure: this note was written by an AI coding assistant.*

- *Tool: Claude Code, VS Code extension.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Date: 2026-09-29.*
- *Basis: the developer's report of the crash and their instructions in the
  same session.*
