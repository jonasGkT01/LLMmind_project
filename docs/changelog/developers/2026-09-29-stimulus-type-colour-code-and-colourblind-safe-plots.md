# 2026-09-29 — Stimulus-type colour code, colourblind-safe plots, multimodal-ready labels and pooling

> **Update 2026-09-29 (later the same day):** multimodal model support has been
> removed, so the multimodal parts of this entry no longer apply. Gemma 3n and
> Gemma 4 now run as language models. See
> `2026-09-29-remove-multimodal-model-support.md`. *(Note added by Claude Code,
> Claude Opus 5.5, `claude-opus-5-5`.)*

## Summary

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

## Why these two colours

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

## Changes

### `workflow/libraries/visualisation_utils.py`

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

### `workflow/libraries/manage_model_metadata.py`

- `model_sort_key(model, parameters_by_model, stimuli_type="")` now returns
  `(..., model, stimuli_type)`, so a multimodal model's two entries sort next
  to each other. This is backward compatible.

### `workflow/libraries/compute_statistics.py`

- `read_model_level_empirical_p_values` returns
  `{model_key(model, stimuli_type): p}`. The duplicate check is now per
  `(model, stimuli_type)`. It used to be per model, which rejected any
  multimodal model on `caption_scene`.

### `workflow/libraries/compute_alignment_enrichment.py`

- `label` is now `model_key(model, stimuli_type)`. It was `model`.

### Plot scripts (`workflow/visualisation/scripts/`)

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

### `README.md`

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

### `workflow/llm_nearest_neighbours/scripts/get_embeddings.py`

- The default pooling for image inputs is `cls` only for `--modality vision`.
  Multimodal models use `avg`. A multimodal model is a causal decoder: its
  first token (BOS) attends only to itself, so `cls` would give every image
  the same embedding.
- `embed_image` passes the processor's `attention_mask` to pooling. It is
  `None` for vision encoders, so their output is unchanged. For multimodal
  processors, the mask covers the expanded image-token sequence.

## Not changed, known limitations

- **Per-concept point colours** (`concept_colours`: tab10 / tab20 /
  golden-ratio hues for 11, 18 or 1,000 concepts) are kept at the developer's
  request. No palette keeps more than about 3 colours distinguishable under
  CVD in a scatter, so these points are not colourblind-safe.
- **Box medians** keep matplotlib's default `C1` orange (`#ff7f0e`). It is a
  lighter, yellower orange than the language colour, but a reader may still
  associate it with "language". Setting `medianprops={"color": "black"}`
  would remove the ambiguity. It was not changed, because the developer asked
  for the boxes to stay as they were.

## Verification

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

## Rerun note

Snakemake does not detect script edits (see the README). To redraw every
plot, force the plotting rules, e.g.:

```bash
snakemake -s workflow/Snakefile --use-conda --cores 4 \
    --forcerun $(grep '^rule plot' workflow/visualisation/Snakefile | sed 's/rule //; s/://') \
    --allowed-rules $(grep '^rule plot' workflow/visualisation/Snakefile | sed 's/rule //; s/://')
```

Existing embeddings do not need to be recomputed. The pooling change only
affects multimodal models, and none have been run yet.

---
*AI disclosure: the code change and this changelog entry were written by an AI
coding assistant, at the developer's request.*

- *Tool: Claude Code (Anthropic), VS Code extension, in auto mode. The palette
  was checked with the Claude Code dataviz skill's `validate_palette.js`
  (Node.js 20.2).*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Date: 2026-09-29.*
- *Environment used for verification: the project's cached visualisation
  conda env (matplotlib 3.11.1). Gemma 3n / Gemma 4 support was checked by
  reading the installed `transformers` sources (versions 5.9.0–5.16.1 across
  the cached envs). No model was run.*
- *Temporary files: all test inputs, renders and validator copies lived in a
  session scratch directory outside the repository and were deleted at the end
  of the session.*
- *Basis: the developer (Jonas Salvalaggio) asked for a language/vision colour
  code (suggesting orange/green) and for all plots to be colourblind-friendly.
  They then specified that the model names, not the boxes, carry the colour,
  and that concept colours stay unchanged. They had earlier approved fixing
  the multimodal pooling and heatmap labels.*
- *Verification: limited to the checks listed under "Verification".*
- *Review status: not yet reviewed by the developer at the time of writing.
  The code change is uncommitted. Review it before committing.*
