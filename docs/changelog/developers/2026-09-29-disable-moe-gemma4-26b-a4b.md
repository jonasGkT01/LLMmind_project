# 2026-09-29 — gemma4_26ba4b disabled: MoE experts are not quantized by bitsandbytes

## Summary

The run crashed in `get_embeddings` for `gemma4_26ba4b` on `narratives`.
This was the model's first embedding job on any dataset. It is unrelated to
`max_chunk_length` (see `2026-09-29-global-max-chunk-length.md`): the crash
happens in `load_model()`, before any text is read. The model is now
commented out in `config/config.yaml`, and its downloaded weights were
deleted.

## Diagnosis

- Traceback obtained by rerunning the job's shell command on node5 inside
  the rule's conda env, with `--output /dev/null`:

  ```
  get_embeddings.py:361 load_model → AutoModel.from_pretrained(..., device_map="auto")
  transformers/quantizers/quantizer_bnb_4bit.py:74 validate_environment
  ValueError: Some modules are dispatched on the CPU or the disk. Make sure you
  have enough GPU RAM to fit the quantized model. ...
  ```

- `gemma4_26ba4b` is a mixture-of-experts model: `enable_moe_block: true`,
  `num_experts: 128`, `top_k_experts: 8`, 30 layers, `hidden_size` 2816,
  `moe_intermediate_size` 704.
- In `transformers/models/gemma4/modeling_gemma4.py`, `Gemma4TextExperts`
  stores its weights as fused 3D `nn.Parameter`s:
  - `gate_up_proj`: `[num_experts, 2·inter, hidden]`
  - `down_proj`: `[num_experts, hidden, inter]`

  They are applied with `nn.functional.linear`. bitsandbytes replaces only
  `nn.Linear` modules, so these parameters stay in the checkpoint dtype
  (bf16).
- The expert parameters come to 30 × 128 × 3 × 704 × 2816 ≈ 22.8B, about
  45.7 GB in bf16. That is roughly twice node5's 24 GB (RTX A5000).
  `device_map="auto"` then places modules on the CPU, and the bnb 4-bit
  quantizer refuses CPU offload unless both of these are set:
  `llm_int8_enable_fp32_cpu_offload=True` and a custom `device_map`.
- All 38 other configured models were checked for `num_experts`,
  `num_local_experts`, `n_routed_experts`, `enable_moe_block` and
  `num_experts_per_tok` in their `config.json`. None is MoE, so no other
  model is affected.

## Changes

- `config/config.yaml`: the `gemma4_26ba4b` block is commented out, with a
  comment explaining why.
- `resources/models/gemma4_26ba4b/` (49 GB) deleted. There were no outputs
  for this model under `results/`.
- `README.md`:
  - "Models": new paragraph stating that MoE models are unsupported on the
    24 GB GPU, why, and which `config.json` keys to check before adding a
    model.
  - "Troubleshooting": the GPU out-of-memory entry now covers the
    `Some modules are dispatched on the CPU or the disk` error.
- No code changed.

## Verification

- A node5 dry run (`--sdm conda -n`) builds the DAG, and no job references
  `gemma4_26ba4b`.

## Not done / alternatives

Re-enabling the model would need changes to `get_embeddings.py`, using one
of these approaches:

- CPU-only bf16 inference: about 50 GB of RAM, slow.
- GPU/CPU split with `llm_int8_enable_fp32_cpu_offload`: experts in fp32 on
  the CPU, about 90 GB of RAM.
- A pre-quantized third-party checkpoint (GPTQ/AWQ): different weights from
  the official model.

---
*AI disclosure: this entry was written by an AI coding assistant.*

- *Tool: Claude Code, VS Code extension, running on the lab server's
  `frontend` host (checks on node5 via `ssh`).*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Date: 2026-09-29.*
- *Basis: the developer (Jonas Salvalaggio) reported a second crash. After
  the diagnosis, they asked to delete the model from the project directory
  and to comment out every model with the same problem.*
- *Files changed: `config/config.yaml`, `README.md`. Deleted:
  `resources/models/gemma4_26ba4b/`.*
- *Temporary files: one traceback log in the session scratchpad (deleted).
  The reproduction wrote its output to `/dev/null`.*
- *Review status: not yet reviewed by the developer at the time of writing.
  Review it before committing.*

*The user changelog entry of the same name gives a plain-language summary.*
