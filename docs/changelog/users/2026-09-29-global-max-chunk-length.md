# 2026-09-29 — All language models now read text in pieces of the same size

## Why

Long texts, such as the Narratives stories, are cut into pieces
("chunks") before a language model reads them. Until now, each model chose
its own piece size: 8192 tokens for Gemma 1 and Gemma 2, and 2048 for all
the others. Two problems followed:

- The large Gemma 2 27B model ran out of GPU memory on node5 with 8192-token
  pieces, and the whole run stopped.
- The models were not compared under the same conditions, because piece
  size affects the embeddings.

## What changed

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

## What this means for you

- On the next run, all language-model embeddings, and everything built on
  them, are recomputed. This is expected.
- Snakemake will also want to recompute the image-model embeddings, even
  though they won't change. To skip that, start the next run once with:

  ```bash
  snakemake --use-conda --cores <N> --rerun-triggers mtime params input software-env
  ```

- Switching the model to 8-bit would not have fixed the crash. It would make
  the model too large for the GPU.

---
*AI disclosure: this note was written by an AI coding assistant.*

- *Tool: Claude Code, VS Code extension.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Date: 2026-09-29.*
- *Basis: the developer's question about the crash and their instructions in
  the same session.*
