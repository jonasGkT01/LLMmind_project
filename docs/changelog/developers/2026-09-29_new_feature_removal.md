# 2026-09-29 — developer changelog

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../../AI_USAGE.md).*

Changes made on this day, in order:

- Hypergeometric null line on the model-level alignment lineplot (new_feature)
- Remove multimodal model support; Gemma 3n and Gemma 4 run as language models (removal)
- Stimulus-type colour code, colourblind-safe plots, multimodal-ready labels and pooling (new_feature)
- One chunk length for all language models (`max_chunk_length`) (new_feature)
- gemma4_26ba4b disabled: MoE experts are not quantized by bitsandbytes (removal)

---

## Hypergeometric null line on the model-level alignment lineplot

Kind: `new_feature`

### Summary

- `plot_brain_model_alignment_lineplot.py` now draws the hypergeometric
  expectation k/(n−1) as a horizontal reference line. The other five
  alignment plots already had one; this was the only plot without it.
- The concept-level raw plot (`plot_concept_alignment_scatterplot.py`)
  already drew the same line at line 194 and was **not changed**.

### Reference lines across plots after this change

| Plot script | Reference line | Legend label |
|---|---|---|
| `plot_brain_model_alignment_lineplot.py` | k/(n−1) (**new**) | Null expectation (hypergeometric) |
| `plot_concept_alignment_scatterplot.py` | k/(n−1) | Null expectation (hypergeometric) |
| `plot_brain_model_alignment_enrichment_lineplot.py` | 1 | Null expectation (enrichment = 1) |
| `plot_concept_alignment_enrichment_scatterplot.py` | 1 | Null expectation (enrichment = 1) |
| `plot_spearman_alignment.py` (both levels) | 0 | Null expectation (no rank correlation) |

### Changes

`workflow/visualisation/scripts/plot_brain_model_alignment_lineplot.py`:

- `read_alignment_score_summary(path)` became
  `read_alignment_score_summary(path, number_of_neighbours)` and now returns
  `(mean, standard_error, expected_alignment_score)`, where
  `expected_alignment_score = number_of_neighbours / (number_of_concepts - 1)`.
  This is the same formula as `read_model_alignment_scores()` in
  `plot_concept_alignment_scatterplot.py`.
- A new `ValueError` is raised when k > n − 1, matching the concept-level
  script.
- `main()` collects the expected scores of all input files in a set and
  raises if they differ, for example when models were scored on different
  concept sets. The concept-level script does the same check.
- `ax.axhline(expected_alignment_score, linestyle="--", linewidth=1.2,
  color="grey", label="Null expectation (hypergeometric)")` is drawn right
  after `ax.errorbar(...)`. `add_legend()` picks up labelled artists
  through `ax.get_legend_handles_labels()`, so the line is listed first in
  the legend, before the significance handles.

**Why the per-concept expectation is valid for the mean:** under the null,
each concept's score is hypergeometric overlap / k, with expectation
k/(n−1). That value is the same for every concept, so the expected *mean*
across concepts is also k/(n−1).

`README.md` ("Outputs" → `results/pictures/`): one sentence saying that both
raw alignment plots draw this line.

### Rerun behaviour

- The plot scripts are not declared as rule inputs, so Snakemake does not
  notice the change on its own. Regenerate the figures with the "redraw
  every plot" command in the README (`--forcerun
  plot_brain_model_alignment_lineplot ...`). No upstream rule is affected.

### Verification

- Ran the edited script by hand in the built visualisation conda env
  (`.snakemake/conda/961b78e7…`) on the real inputs for
  `caption_scene / cosine / 25NN` (24 models, n = 1000 concepts). The script
  wrote to the session scratchpad, not to `results/`. The PNG showed the
  dashed line at 25/999 ≈ 0.025, listed first in the legend. The test
  image was then deleted.
- Not run: the full `snakemake --forcerun` redraw. No automated tests exist
  for the plotting scripts.

### Follow-ups

- On the fixed `[0, 1]` y-axis, the model means and the null line all sit
  near 0.02–0.03 for small k/n, so the gap between observed and expected
  is barely visible. The enrichment lineplot shows the same comparison on a
  readable scale. Changing the raw lineplot's y-range would break the
  shared axis with the concept-level plot, so that was left alone.
- This script still uses its own inline family-separator and x-axis code.
  The enrichment lineplot uses `add_model_family_annotations()`,
  `style_model_x_axis()` and `save_model_figure()` instead. Switching to the
  shared helpers would be a separate refactor.

### Context

- Basis: the developer (Jonas Salvalaggio) asked whether the raw concept- and model-level alignment plots were missing their expected-alignment line. The assistant found that only the model-level plot lacked it, added the line using the concept-level script's formula, and then wrote this documentation on request.
- Verification: limited to the checks listed under "Verification".

---

## Remove multimodal model support; Gemma 3n and Gemma 4 run as language models

Kind: `removal`

### Summary

The `multimodal` modality has been removed from the pipeline. The seven
Gemma 3n / Gemma 4 models that used it are now `modality: "language"` in
`config/config.yaml` and are embedded from text stimuli only. Every code
path that handled `"multimodal"` has been removed, so a model now runs only
on the stimulus type equal to its `modality`.

This reverses the multimodal parts of
`2026-09-25_new_feature_refactor_documentation.md` and
`2026-09-29_new_feature_removal.md`. The
`<model>-<stimuli_type>` labels (`model_key`) and the stimulus-type colour
code from the latter entry are kept.

### Why

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

### Changes

#### `config/config.yaml`

- `gemma3n_e2b`, `gemma3n_e4b`, `gemma4_e2b`, `gemma4_e4b`, `gemma4_12b`,
  `gemma4_26ba4b`, `gemma4_31b`: `modality: "multimodal"` → `"language"`.

#### `workflow/Snakefile`, `workflow/spearman_alignment/Snakefile`

- The model filter in `pairings()`, `llm_llm_pairings()`,
  `LLM_NEIGHBOUR_GENERATION_PAIRINGS` and `SPEARMAN_PAIRINGS` (both
  Snakefiles) changed from
  `config["models"][model]["modality"] in [stimuli_type, "multimodal"]` to
  `config["models"][model]["modality"] == stimuli_type`.
- `llm_llm_pairings()` still pairs `(model, stimuli_type)` representations
  with `itertools.combinations`. Since each model now has exactly one
  representation, no model is paired with itself. The comment about
  cross-stimulus self-pairs was removed. Output filenames are unchanged.

#### `workflow/llm_nearest_neighbours/scripts/get_embeddings.py`

- `--modality` choices: `["language", "vision"]` (was also `"multimodal"`).
- Default pooling: image stimuli → `cls`, text → `avg`. The
  `args.modality != "multimodal"` exception (mean-pooling images for causal
  decoders) was removed.
- `embed_image()` passes `attention_mask=None` to
  `extract_embedding_from_output()` again, instead of
  `inputs.get("attention_mask")`. Vision processors return no attention
  mask, so the output is unchanged for vision models.

#### `workflow/libraries/estimate_batch_size.py`

- Accepted modalities: `("vision", "language")`. The sequence-length scaling
  now applies to `modality == "language"` only.

#### `workflow/libraries/manage_model_metadata.py`

- `model_sort_key(model, parameters_by_model)`: the `stimuli_type`
  parameter and the fourth tuple element were removed. They only broke ties
  between the two entries of one multimodal model.

#### Plot scripts in `workflow/visualisation/scripts/`

- `plot_alignment_heatmap.py`, `plot_brain_model_alignment_lineplot.py`,
  `plot_brain_model_alignment_enrichment_lineplot.py`,
  `plot_concept_alignment_scatterplot.py`,
  `plot_concept_alignment_enrichment_scatterplot.py`,
  `plot_spearman_alignment.py`: `stimuli_type=` removed from the
  `model_sort_key()` calls. `stimuli_type` is still read and used for the
  labels and colours.

#### `workflow/libraries/compute_statistics.py`

- Comment only: removed the reference to multimodal models in
  `read_model_level_empirical_p_values()`.

### Effect on the DAG

- No image jobs remain for the Gemma 3n / Gemma 4 models. Dry run
  (`snakemake -n --cores 4 --resources gpu=1 --sdm conda --quiet rules`):
  15,861 jobs to run, with 10 `download_pretrained_llm` and 42
  `get_embeddings` jobs.
- Existing outputs are not affected. Text embeddings already computed for
  `gemma3_270m` and `gemma3n_e2b` are reused.
- A stale `gemma3n_e2b-vision` output could exist only if an image job had
  succeeded before. None did, so there is nothing to clean up.

### Verification

- `grep -rni multimodal workflow config` finds nothing outside the
  third-party packages in `workflow/envs/`.
- `python -m py_compile` passes for every changed Python file.
- The Snakemake dry run above builds the DAG without errors.
- Not run: any real job for the Gemma 4 models. Text embedding with
  `AutoModel` was only exercised for `gemma3n_e2b` (on `narratives`, in the
  run that crashed).

### Context

- Basis: the developer (Jonas Salvalaggio) asked why the run crashed. The assistant traced it to the Gemma 3n image processor. The developer then asked to switch the multimodal Gemma models to `language` and to remove every code path that handles multimodal models.
- Verification: limited to the checks listed under "Verification".

---

## Stimulus-type colour code, colourblind-safe plots, multimodal-ready labels and pooling

Kind: `new_feature`

> **Update 2026-09-29 (later the same day):** multimodal model support has been
> removed, so the multimodal parts of this entry no longer apply. Gemma 3n and
> Gemma 4 now run as language models. See
> `2026-09-29_new_feature_removal.md`. *(Note added by Claude Code,
> Claude Opus 5.5, `claude-opus-5-5`.)*

### Summary

- Every plot now separates a model's **language** and **vision** entries.
  - Labels are `model-stimuli_type` (via the existing
    `manage_model_metadata.model_key`), everywhere.
  - **Each model name is coloured by stimulus type**: dark vermillion
    `#A84800` for language, dark bluish green `#007A5A` for vision. The brain
    label stays black.
  - In the three model-level line plots, the points and error bars also take
    the colour and a shape: ○ for language, □ for vision.
  - Boxes and per-concept point colours are **unchanged**, at the developer's
    request.
- The red used for q-value asterisks and degenerate-box markers was replaced
  by colourblind-safe choices.
- This fixes the two multimodal blockers from 2026-09-25:
  - `plot_empirical_p_value_heatmap.py` no longer crashes with
    "provided more than once".
  - `plot_alignment_heatmap.py` no longer merges a model's language and vision
    rows, and no longer hides the language-vs-vision self-pair on the
    diagonal.
- `get_embeddings.py` now mean-pools image inputs for multimodal models
  instead of taking the first token.

### Why these two colours

The developer asked for orange/green. Candidate pairs were run through the
dataviz skill's palette validator (Machado 2009 CVD simulation, OKLab ΔE×100,
all pairs, white surface). Because the colours are applied to **text**, each
colour also needs ≥ 4.5:1 contrast on white (the WCAG text threshold).

| pair | CVD ΔE (≥ 8) | contrast on white | verdict |
|---|---|---|---|
| `#D55E00` / `#008300` (plain orange/green) | **1.6** (protan) | 3.9 / 4.9 | fails: protanopes can't tell them apart |
| `#D55E00` / `#009E73` (Okabe–Ito) | 11.0 | 3.9 / **3.4** | fine for marks, too light for text |
| **`#A84800` / `#007A5A`** (same hues, darker) | **9.6** (deutan) | **5.85 / 5.34** | passes all checks |

Colour is never the only cue: every label ends in `-language` / `-vision`, and
line-plot markers differ in shape.

### Changes

#### `workflow/libraries/visualisation_utils.py`

- New constants:
  - `STIMULI_TYPE_COLOURS`, `STIMULI_TYPE_MARKERS`.
  - `NEUTRAL_COLOUR = "#595959"`, used for connecting lines and family
    separators.
  - `SEQUENTIAL_COLOURMAP = "viridis"`, now passed explicitly to both heatmaps
    instead of relying on the rcParams default.
- New helpers:
  - `stimuli_type_colour`.
  - `stimuli_type_legend_handles`: colour-swatch `Patch` handles labelled
    "Language/Vision stimuli (model name colour)". Used by the box-plot scripts
    and the heatmaps.
  - `colour_tick_labels_by_stimuli_type(ax, stimuli_types, axes="x")`: sets
    each tick label's text colour. Labels without a stimulus type (the brain)
    stay black. It must be called after the final `set_xticklabels`, because
    `boxplot()` and `set_xticks()` rebuild the labels.
  - `plot_model_points(ax, x, values, errors, stimuli_types)`: a neutral
    connecting line, plus one `errorbar` call per stimulus type with that
    type's colour and marker. Replaces the single default-blue (`C0`)
    `errorbar` in the three model-level line plots. Its artists supply the
    line plots' legend entries.
- `Q_VALUE_SIGNIFICANCE_COLOUR`: `"red"` → Okabe–Ito blue `#0072B2`. Red and
  black look alike under protanopia. The two asterisk rows also still differ
  in position.
- `mark_degenerate_boxplot_statistics`: default colour red → black with a white
  edge, size 5 → 6, for the same reason.
- `add_model_family_annotations`: separators use `NEUTRAL_COLOUR`. They were
  the default `C0` blue.
- `concept_colours` is unchanged.

#### `workflow/libraries/manage_model_metadata.py`

- `model_sort_key(model, parameters_by_model, stimuli_type="")` now returns
  `(..., model, stimuli_type)`, so a multimodal model's two entries sort next
  to each other. This is backward compatible.

#### `workflow/libraries/compute_statistics.py`

- `read_model_level_empirical_p_values` returns
  `{model_key(model, stimuli_type): p}`. The duplicate check is now per
  `(model, stimuli_type)`. It used to be per model, which rejected any
  multimodal model on `caption_scene`.

#### `workflow/libraries/compute_alignment_enrichment.py`

- `label` is now `model_key(model, stimuli_type)`. It was `model`.

#### Plot scripts (`workflow/visualisation/scripts/`)

All seven plot scripts:
- use `model_key` labels;
- sort with `stimuli_type` as the final tie-break;
- pass **model names** (not labels) to `add_model_family_annotations`;
- colour the model names with `colour_tick_labels_by_stimuli_type`. The
  heatmaps colour both axes.

Per-script notes:
- **Box-plot scripts** (the three concept-level scatterplots): boxes are
  unchanged, and the legend gains the two stimulus-type swatches.
- **Line plots**: use `plot_model_points`.
- `plot_brain_model_alignment_lineplot.py`: its inline copy of the p-value
  reader and of the family-separator loop were replaced by
  `read_model_level_empirical_p_values` and `add_model_family_annotations`,
  whose behaviour is the same.
- `plot_spearman_alignment.py`: its inline family-separator loop was replaced
  by `add_model_family_annotations`.
- **Both heatmaps**:
  - the stimulus-type legend sits in the figure's bottom-left corner;
  - the colour bar is sized with `fraction=0.046, pad=0.04`. It used to rise
    above the axes and clip the right end of the p-value heatmap's title,
    which was already visible in existing outputs.

#### `README.md`

Integrated into the existing sections (not a copy of this entry):

- **`llm_nearest_neighbours/`:** image pooling by modality.
- **`llm_llm_alignment/`:** the `(model, stimulus type)` pairing and the
  multimodal self-pair from 2026-09-25.
- **Models:** how a multimodal model appears once per stimulus type, the
  `<model>-<stimuli_type>` naming, and how to enable the commented-out Gemma
  models, with a dry-run example.
- **Outputs → plot conventions:**
  - the colour code;
  - blue q-value asterisks;
  - the black degenerate-box diamond;
  - the heatmap legend position;
  - a colour-vision note stating that the per-concept colours are the
    exception.

#### `workflow/llm_nearest_neighbours/scripts/get_embeddings.py`

- The default pooling for image inputs is `cls` only for `--modality vision`.
  Multimodal models use `avg`. A multimodal model is a causal decoder: its
  first token (BOS) attends only to itself, so `cls` would give every image
  the same embedding.
- `embed_image` passes the processor's `attention_mask` to pooling. It is
  `None` for vision encoders, so their output is unchanged. For multimodal
  processors, the mask covers the expanded image-token sequence.

### Not changed, known limitations

- **Per-concept point colours** (`concept_colours`: tab10 / tab20 /
  golden-ratio hues for 11, 18 or 1,000 concepts) are kept at the developer's
  request. No palette keeps more than about 3 colours distinguishable under
  CVD in a scatter, so these points are not colourblind-safe.
- **Box medians** keep matplotlib's default `C1` orange (`#ff7f0e`). It is a
  lighter, yellower orange than the language colour, but a reader may still
  associate it with "language". Setting `medianprops={"color": "black"}`
  would remove the ambiguity. It was not changed, because the developer asked
  for the boxes to stay as they were.

### Verification

- **Synthetic multimodal case.** Five representations, including
  `gemma3n_e4b` as both `language` and `vision`, run through all seven
  scripts: all succeed, including the p-value heatmap that used to crash.
  - The self-pair appears as its own off-diagonal cell.
  - PNGs were inspected for label/legend/title collisions. Three collisions
    were found and fixed during the session: tick swatches vs asterisks,
    heatmap legend vs title, and heatmap legend vs x-axis title.
- **Real current results.** Plots for `caption_scene`/cosine/25NN and
  `nature_stories`/cosine/3NN, all seven scripts, were rendered into a scratch
  directory with the visualisation conda env. `results/pictures/` was not
  touched.
- `get_embeddings.py`: **not run**. No multimodal model has been downloaded.
  Vision-encoder behaviour is unchanged by construction: same `cls` default,
  and `attention_mask` is `None`.
- No unit tests exist for the plotting code.

### Rerun note

Snakemake does not detect script edits (see the README). To redraw every
plot, force the plotting rules, e.g.:

```bash
snakemake -s workflow/Snakefile --use-conda --cores 4 \
    --forcerun $(grep '^rule plot' workflow/visualisation/Snakefile | sed 's/rule //; s/://') \
    --allowed-rules $(grep '^rule plot' workflow/visualisation/Snakefile | sed 's/rule //; s/://')
```

Existing embeddings do not need to be recomputed. The pooling change only
affects multimodal models, and none have been run yet.

### Context

- Environment used for verification: the project's cached visualisation conda env (matplotlib 3.11.1). Gemma 3n / Gemma 4 support was checked by reading the installed `transformers` sources (versions 5.9.0–5.16.1 across the cached envs). No model was run.
- Basis: the developer (Jonas Salvalaggio) asked for a language/vision colour code (suggesting orange/green) and for all plots to be colourblind-friendly. They then specified that the model names, not the boxes, carry the colour, and that concept colours stay unchanged. They had earlier approved fixing the multimodal pooling and heatmap labels.
- Verification: limited to the checks listed under "Verification".

---

## One chunk length for all language models (`max_chunk_length`)

Kind: `new_feature`

### Summary

`get_embeddings` for gemma2_27b on `narratives` crashed with `exit status 1`
(most likely CUDA OOM on node5's 24 GB RTX A5000; the traceback was not
captured, see "Diagnosis"). The root cause was an inconsistent, model-dependent
chunk length. A new top-level config key, `max_chunk_length` (default 2048),
now sets the chunk length for every language model. `get_embeddings.py` is
unchanged.

### Diagnosis

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

### Changes

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

### Rerunning

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

### Verification

- `snakemake -n -p` for `gemma2_27b` on `narratives` produced the expected
  commands:
  - With the default config: `--chunk_max_length 2048`.
  - With `--config max_chunk_length=null` and with `max_chunk_length=none`:
    no argument.
- `clip_b` (vision): no argument.
- Dry runs on node5 (`--sdm conda`), with the rerun counts above.
- No job was executed.

### Follow-ups not done

- Add a `log:` directive to `get_embeddings` so failures keep their traceback.
- Possibly pass a bf16 compute dtype for quantized models (declined for now).

### Context

- Basis: the developer (Jonas Salvalaggio) asked why the run crashed with an apparent OOM. After the diagnosis, they asked to set one chunk length of 2048 in the config, and to pass no argument when it is null/"none", following the narratives run-tag pattern.
- Files changed: `config/config.yaml`, `workflow/llm_nearest_neighbours/Snakefile`, `README.md`.

---

## gemma4_26ba4b disabled: MoE experts are not quantized by bitsandbytes

Kind: `removal`

### Summary

The run crashed in `get_embeddings` for `gemma4_26ba4b` on `narratives`.
This was the model's first embedding job on any dataset. It is unrelated to
`max_chunk_length` (see `2026-09-29_new_feature_removal.md`): the crash
happens in `load_model()`, before any text is read. The model is now
commented out in `config/config.yaml`, and its downloaded weights were
deleted.

### Diagnosis

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

### Changes

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

### Verification

- A node5 dry run (`--sdm conda -n`) builds the DAG, and no job references
  `gemma4_26ba4b`.

### Not done / alternatives

Re-enabling the model would need changes to `get_embeddings.py`, using one
of these approaches:

- CPU-only bf16 inference: about 50 GB of RAM, slow.
- GPU/CPU split with `llm_int8_enable_fp32_cpu_offload`: experts in fp32 on
  the CPU, about 90 GB of RAM.
- A pre-quantized third-party checkpoint (GPTQ/AWQ): different weights from
  the official model.

### Context

- Basis: the developer (Jonas Salvalaggio) reported a second crash. After the diagnosis, they asked to delete the model from the project directory and to comment out every model with the same problem.
- Files changed: `config/config.yaml`, `README.md`. Deleted: `resources/models/gemma4_26ba4b/`.
