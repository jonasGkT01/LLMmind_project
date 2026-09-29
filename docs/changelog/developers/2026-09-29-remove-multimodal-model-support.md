# 2026-09-29 — Remove multimodal model support; Gemma 3n and Gemma 4 run as language models

## Summary

The `multimodal` modality has been removed from the pipeline. The seven
Gemma 3n / Gemma 4 models that used it are now `modality: "language"` in
`config/config.yaml` and are embedded from text stimuli only. Every code
path that handled `"multimodal"` has been removed, so a model now runs only
on the stimulus type equal to its `modality`.

This reverses the multimodal parts of
`2026-09-25-llm-llm-self-pairs-across-stimuli-types.md` and
`2026-09-29-stimulus-type-colour-code-and-colourblind-safe-plots.md`. The
`<model>-<stimuli_type>` labels (`model_key`) and the stimulus-type colour
code from the latter entry are kept.

## Why

The run of 2026-09-29 (log
`.snakemake/log/2026-09-29T113156.101889.snakemake.log`) stopped in
`get_embeddings` for `model=gemma3n_e2b`, `dataset=nsd_data`,
`stimuli_type=vision`. Rerunning the command on two images gave:

```
File ".../get_embeddings.py", line 331, in embed_image
    inputs = processor(images=image, return_tensors="pt",)
File ".../transformers/models/gemma3n/processing_gemma3n.py", line 91, in __call__
    raise TypeError("Invalid input text. Please provide a string, or a list of strings")
```

`Gemma3nProcessor` (and the Gemma 4 processor) requires a text prompt that
contains the image placeholder token, which is expanded into the image
soft tokens. `embed_image()` passes `images=` alone, which is correct for
vision encoders but not for these models. The developer chose not to use
these models on images rather than add prompt handling.

## Changes

### `config/config.yaml`

- `gemma3n_e2b`, `gemma3n_e4b`, `gemma4_e2b`, `gemma4_e4b`, `gemma4_12b`,
  `gemma4_26ba4b`, `gemma4_31b`: `modality: "multimodal"` → `"language"`.

### `workflow/Snakefile`, `workflow/spearman_alignment/Snakefile`

- The model filter in `pairings()`, `llm_llm_pairings()`,
  `LLM_NEIGHBOUR_GENERATION_PAIRINGS` and `SPEARMAN_PAIRINGS` (both
  Snakefiles) changed from
  `config["models"][model]["modality"] in [stimuli_type, "multimodal"]` to
  `config["models"][model]["modality"] == stimuli_type`.
- `llm_llm_pairings()` still pairs `(model, stimuli_type)` representations
  with `itertools.combinations`. Since each model now has exactly one
  representation, no model is paired with itself. The comment about
  cross-stimulus self-pairs was removed. Output filenames are unchanged.

### `workflow/llm_nearest_neighbours/scripts/get_embeddings.py`

- `--modality` choices: `["language", "vision"]` (was also `"multimodal"`).
- Default pooling: image stimuli → `cls`, text → `avg`. The
  `args.modality != "multimodal"` exception (mean-pooling images for causal
  decoders) was removed.
- `embed_image()` passes `attention_mask=None` to
  `extract_embedding_from_output()` again, instead of
  `inputs.get("attention_mask")`. Vision processors return no attention
  mask, so the output is unchanged for vision models.

### `workflow/libraries/estimate_batch_size.py`

- Accepted modalities: `("vision", "language")`. The sequence-length scaling
  now applies to `modality == "language"` only.

### `workflow/libraries/manage_model_metadata.py`

- `model_sort_key(model, parameters_by_model)`: the `stimuli_type`
  parameter and the fourth tuple element were removed. They only broke ties
  between the two entries of one multimodal model.

### Plot scripts in `workflow/visualisation/scripts/`

- `plot_alignment_heatmap.py`, `plot_brain_model_alignment_lineplot.py`,
  `plot_brain_model_alignment_enrichment_lineplot.py`,
  `plot_concept_alignment_scatterplot.py`,
  `plot_concept_alignment_enrichment_scatterplot.py`,
  `plot_spearman_alignment.py`: `stimuli_type=` removed from the
  `model_sort_key()` calls. `stimuli_type` is still read and used for the
  labels and colours.

### `workflow/libraries/compute_statistics.py`

- Comment only: removed the reference to multimodal models in
  `read_model_level_empirical_p_values()`.

## Effect on the DAG

- No image jobs remain for the Gemma 3n / Gemma 4 models. Dry run
  (`snakemake -n --cores 4 --resources gpu=1 --sdm conda --quiet rules`):
  15,861 jobs to run, with 10 `download_pretrained_llm` and 42
  `get_embeddings` jobs.
- Existing outputs are not affected. Text embeddings already computed for
  `gemma3_270m` and `gemma3n_e2b` are reused.
- A stale `gemma3n_e2b-vision` output could exist only if an image job had
  succeeded before. None did, so there is nothing to clean up.

## Verification

- `grep -rni multimodal workflow config` finds nothing outside the
  third-party packages in `workflow/envs/`.
- `python -m py_compile` passes for every changed Python file.
- The Snakemake dry run above builds the DAG without errors.
- Not run: any real job for the Gemma 4 models. Text embedding with
  `AutoModel` was only exercised for `gemma3n_e2b` (on `narratives`, in the
  run that crashed).

---
*AI disclosure: this changelog entry, together with the code change it
describes and the related README edit, was written by an AI coding
assistant.*

- *Tool: Claude Code (Anthropic), VS Code extension, run inside the
  developer's workspace on the lab server.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Date: 2026-09-29.*
- *Basis: the developer (Jonas Salvalaggio) asked why the run crashed. The
  assistant traced it to the Gemma 3n image processor. The developer then
  asked to switch the multimodal Gemma models to `language` and to remove
  every code path that handles multimodal models.*
- *Verification: limited to the checks listed under "Verification".*
- *Temporary files: two symlinked test images and a test exclusion file in
  the session scratchpad (deleted), plus two `__pycache__/` folders created
  by `py_compile` (deleted). Nothing was written to `results/`.*
- *Review status: not yet reviewed by the developer at the time of
  writing. Review it before committing.*

*The user changelog entry of the same name gives a plain-language summary.*
