# 2026-10-01 — One model-order rule for every figure

## Change

The required order is **family (alphabetical) → number of parameters → model → stimulus type**,
with the brain after all models in the heatmaps. It was implemented three ways (a local key in the
p-value heatmap, `heatmap_label_sort_key()` in the alignment heatmap, and the shared key without a
stimulus-type level in the six model figures). Now:

- `workflow/libraries/manage_model_metadata.py`: `model_sort_key(model, stimuli_type, parameters_by_model)`
  returns `(model_family(model), parameters_by_model[model], model, stimuli_type)`. Families are
  sorted alphabetically in code. `model_family_order()`, which took the family order from the order
  of the `models:` block in the config, is deleted (its only caller was `model_sort_key()`); the
  config order no longer affects any figure.
- `plot_empirical_p_value_heatmap.py`: the local `model_sort_key()`, the `model_family` import and
  the `number_of_parameters` field of `model_metadata` are deleted.
- `plot_alignment_heatmap.py`: `heatmap_label_sort_key()` is deleted. Its label sort no longer
  depends on the iteration order of a `set` when one model appears with two stimulus types.
- Both heatmaps sort with
  `(1,) if label == "brain" else (0, *model_sort_key(model, stimuli_type, parameters_by_model))`.
- `plot_brain_model_alignment_lineplot.py`, `plot_concept_alignment_scatterplot.py`,
  `plot_spearman_alignment.py` (both figures), `plot_brain_model_alignment_enrichment_lineplot.py`
  and `plot_concept_alignment_enrichment_scatterplot.py` pass the stimulus type, so ties no longer
  depend on the order of the input files.
- `grep -rn "sorted(\|sort_values" workflow/visualisation` finds no other model sort.

Only the plotting rules are affected (`[light]`). Snakemake does not see edits to scripts run from
`shell:` rules, so the figures are redrawn the next time the plot rules run (they rerun anyway after
the S34 aggregation change is merged).

## Verification

- All 38 configured models plus "brain", and a synthetic second stimulus type for `clip_b`, were
  shuffled 20 times and sorted with the old keys (`d3db409`) and the new one. The order was the
  same every time (the config families are alphabetical and contiguous), and the synthetic pair
  was ordered by stimulus type.
- One real job of each of the 7 changed plot rules was run with the new code, its command taken from
  a dry run, figures written to a scratch directory. All 8 figures were byte-identical to the current
  ones in `results/pictures/`.

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-01, Claude Opus 5.5: written for TODO entry S1, modified and approved by the developer on 2026-09-30; implemented on 2026-10-01 after the developer asked which solutions could be done while the S34 check was running ("proceed").*
- *Files changed: `workflow/libraries/manage_model_metadata.py`, `workflow/visualisation/scripts/plot_empirical_p_value_heatmap.py`, `workflow/visualisation/scripts/plot_alignment_heatmap.py`, `workflow/visualisation/scripts/plot_brain_model_alignment_lineplot.py`, `workflow/visualisation/scripts/plot_concept_alignment_scatterplot.py`, `workflow/visualisation/scripts/plot_spearman_alignment.py`, `workflow/visualisation/scripts/plot_brain_model_alignment_enrichment_lineplot.py`, `workflow/visualisation/scripts/plot_concept_alignment_enrichment_scatterplot.py`.*
- *Review status: not yet reviewed by the developer.*
