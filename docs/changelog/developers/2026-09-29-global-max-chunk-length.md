# 2026-09-29 — One chunk length for all language models (`max_chunk_length`)

## Summary

`get_embeddings` for gemma2_27b on `narratives` crashed with `exit status 1`
(most likely CUDA OOM on node5's 24 GB RTX A5000; the traceback was not
captured, see "Diagnosis"). The root cause was an inconsistent, model-dependent
chunk length. A new top-level config key, `max_chunk_length` (default 2048),
now sets the chunk length for every language model. `get_embeddings.py` is
unchanged.

## Diagnosis

- `get_embeddings.py` was always called without `--chunk_max_length`, so
  `get_safe_max_length()` inferred it per model: `min(tokenizer.model_max_length,
  config.max_position_embeddings)`, dropping values ≥ 100,000, fallback 2048.
- Resulting chunk lengths (checked in the `chunk_max_length` column of the
  narratives embeddings):
  - Gemma 1/2: 8192.
  - BLOOM and OpenLLaMA: 2048 (their native context).
  - Gemma 3/3n/4: 2048, because their 131k/262k contexts are discarded.
- gemma2_27b at 8192 tokens:
  - The 4-bit weights take about 13–14 GB.
  - The checkpoint is fp32 and no `dtype` is passed, so the unquantized
    embedding (256000 × 4608) stays in fp32 and adds about 4.7 GB.
  - Gemma 2 is forced to `eager` attention (logit softcapping), so one
    attention matrix is 32 × 8192² × 4 B ≈ 8.6 GB, with several live copies
    during the softcap and softmax steps.
  - This exceeds 24 GB.
- gemma4_31b (bf16, 2048 chunks) and gemma2_2b (8 heads) fit.
- The traceback was not captured: the rule has no `log:`, and the Snakemake
  log only shows `CalledProcessError`. The OOM diagnosis rests on the arithmetic
  above.

## Changes

- `config/config.yaml`: new top-level key `max_chunk_length: 2048`, placed
  after `minimum_subjects_per_stimulus`, with a comment on the `null`
  behaviour.
- `workflow/llm_nearest_neighbours/Snakefile`:
  - New helper `chunk_max_length_arg(model)`. It returns
    `"--chunk_max_length <int>"`, or `""` when either of these holds:
    - the model's `modality` is not `language`;
    - `max_chunk_length` is missing, YAML `null`, or a string
      `"none"`/`"null"`/`""` (case-insensitive, stripped).
  - A non-integer value raises in `int()` at DAG build time.
  - This is the same empty-string pattern as `quantization_arg` in the same
    rule and `narratives_run_label` / `narratives_scan_prefix` for the empty
    run tag.
  - `get_embeddings`: new param `chunk_max_length_arg`, inserted in the shell
    command after `{params.quantization_arg}`.
- `get_embeddings.py`: not modified. `--chunk_max_length` already overrides
  `get_safe_max_length()`, and without it the old inference is used.
- `README.md`:
  - The `llm_nearest_neighbours/` section now has a table of what an integer
    versus `null`/`"none"` does, with a warning about inconsistent chunk
    lengths.
  - New "Troubleshooting" entry on GPU OOM, which also explains why 8-bit
    does not help gemma2_27b.
- Not changed, by request: the compute dtype stays as it was (no bf16).

## Rerunning

- Language `get_embeddings` jobs (75): params change from `""` to
  `--chunk_max_length 2048`. They rerun under the params trigger, followed by
  the whole downstream chain.
  - This includes models that already used 2048 (BLOOM, OpenLLaMA,
    Gemma 3/3n/4). Their outputs should come out unchanged.
- Vision `get_embeddings` jobs (28): their params are unchanged (still `""`).
  However, the shell template gained a placeholder, so the **code** trigger
  reruns them.
  - Verified on node5 with a dry run:
    - `--rerun-triggers params` lists only the 75 language jobs.
    - The default triggers list all 103.
  - To avoid re-embedding the vision models (nsd_data ≈ 66k images each),
    launch once with
    `--rerun-triggers mtime params input software-env`.
- Dry-run note: without `--sdm conda`/`--use-conda`, Snakemake reports
  "Software environment definition has changed" for every
  `download_pretrained_llm` job. That is an artefact of the missing flag, not
  of this change.

## Verification

- `snakemake -n -p` for `gemma2_27b` on `narratives` produced the expected
  commands:
  - With the default config: `--chunk_max_length 2048`.
  - With `--config max_chunk_length=null` and with `max_chunk_length=none`:
    no argument.
- `clip_b` (vision): no argument.
- Dry runs on node5 (`--sdm conda`), with the rerun counts above.
- No job was executed.

## Follow-ups not done

- Add a `log:` directive to `get_embeddings` so failures keep their traceback.
- Possibly pass a bf16 compute dtype for quantized models (declined for now).

---
*AI disclosure: this entry was written by an AI coding assistant.*

- *Tool: Claude Code, VS Code extension, running on the lab server's
  `frontend` host (checks on node5 via `ssh`).*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Date: 2026-09-29.*
- *Basis: the developer (Jonas Salvalaggio) asked why the run crashed with an
  apparent OOM. After the diagnosis, they asked to set one chunk length of 2048
  in the config, and to pass no argument when it is null/"none", following the
  narratives run-tag pattern.*
- *Files changed: `config/config.yaml`,
  `workflow/llm_nearest_neighbours/Snakefile`, `README.md`.*
- *Temporary files: two dry-run outputs in the session scratchpad (deleted).*
- *Review status: not yet reviewed by the developer at the time of writing.
  Review it before committing.*

*The user changelog entry of the same name gives a plain-language summary.*
