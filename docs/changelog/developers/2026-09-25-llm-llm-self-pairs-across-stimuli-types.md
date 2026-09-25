# 2026-09-25 — LLM–LLM pairings: compare a multimodal model with itself across stimuli types

## Summary

`llm_llm_pairings()` in `workflow/Snakefile` now also pairs a multimodal
model's language representation with its own vision representation, for
example `gemma3n_e4b-language` vs `gemma3n_e4b-vision` on `caption_scene`.
Every pairing produced before is still produced, with the same filenames.

## Changes

### `workflow/Snakefile`

- `llm_llm_pairings()` now builds a list of **representations**, one
  `(model, stimuli_type)` per stimuli type the dataset offers and the model
  can embed (`modality` equals the type, or is `"multimodal"`). It then takes
  `itertools.combinations(representations, 2)`.
  - Before, it took `combinations(compatible_models, 2)` and then
    `product(available_modalities, repeat=2)`. A model was never paired with
    itself.
- Why this is exact:
  - `combinations` never pairs a representation with itself, so there is no
    `X-language` vs `X-language` job.
  - A self-pair appears once (`language` → `vision`), never in both orders.
  - For distinct models, both `(A-language, B-vision)` and
    `(A-vision, B-language)` are still emitted, as before.
  - The representations are model-major in `MODEL_KEYS` order, so `model_1`
    still precedes `model_2` and existing output paths are unchanged.
- Removed the now-unused `product` import.

No rule changes were needed: `compute_llm_llm_alignment_score` and
`compute_llm_llm_empirical_p_value` take `stimuli_type_1`/`stimuli_type_2`
from wildcards, so the two inputs of a self-pair are different files.

## Known limitation (not fixed): heatmaps label cells by model only

`plot_alignment_heatmap.py` and `plot_empirical_p_value_heatmap.py` use
`model` alone as the row/column label, not `model-stimuli_type`. Once a
multimodal model is enabled on `caption_scene`:

- **Alignment heatmap:** the self-pair lands on the diagonal, which is
  hard-coded to 1.0, so its score is not shown. The model's language and
  vision scores against other models also overwrite each other.
- **Empirical p-value heatmap:** the script raises
  `The empirical p-value for X and Y was provided more than once`, because
  `(A-language, B)` and `(A-vision, B)` both map to `(A, B)`. This already
  happened before this change for any multimodal model. The self-pair only
  adds another case.

The fix is to label by `f"{model}-{stimuli_type}"` in both scripts. It is not
implemented yet.

## Verification

- The old and new function bodies were compared in a standalone script
  (`itertools` + `yaml`, run in the project env).
  - Current config (24 models, no multimodal): old 3,116 pairings, new 3,116,
    identical sets.
  - Config with every commented-out Gemma model enabled (39 models): old
    11,104, new 11,160, no duplicates, old ⊂ new. The 56 extra pairings are
    all self-pairs across stimuli types: 7 multimodal models ×
    4 `caption_scene` k values × 2 similarity types.
- `snakemake -n --cores 1` on the current config parses and builds the DAG.
- Not run: any actual LLM–LLM job for a multimodal model.

---
*AI disclosure: the code change and this changelog entry were written by an AI
coding assistant, at the developer's request.*

- *Tool: Claude Code (Anthropic), VS Code extension.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Date: 2026-09-25.*
- *Basis: the developer (Jonas Salvalaggio) asked to compare the same model
  across different stimulus types.*
- *Verification: limited to the checks listed under "Verification".*
- *Review status: not yet reviewed by the developer at the time of writing.
  The code change is uncommitted. Review it before committing.*
