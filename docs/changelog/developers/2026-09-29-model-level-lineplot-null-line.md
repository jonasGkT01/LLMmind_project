# 2026-09-29 — Hypergeometric null line on the model-level alignment lineplot

## Summary

- `plot_brain_model_alignment_lineplot.py` now draws the hypergeometric
  expectation k/(n−1) as a horizontal reference line. The other five
  alignment plots already had one; this was the only plot without it.
- The concept-level raw plot (`plot_concept_alignment_scatterplot.py`)
  already drew the same line at line 194 and was **not changed**.

## Reference lines across plots after this change

| Plot script | Reference line | Legend label |
|---|---|---|
| `plot_brain_model_alignment_lineplot.py` | k/(n−1) (**new**) | Null expectation (hypergeometric) |
| `plot_concept_alignment_scatterplot.py` | k/(n−1) | Null expectation (hypergeometric) |
| `plot_brain_model_alignment_enrichment_lineplot.py` | 1 | Null expectation (enrichment = 1) |
| `plot_concept_alignment_enrichment_scatterplot.py` | 1 | Null expectation (enrichment = 1) |
| `plot_spearman_alignment.py` (both levels) | 0 | Null expectation (no rank correlation) |

## Changes

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

## Rerun behaviour

- The plot scripts are not declared as rule inputs, so Snakemake does not
  notice the change on its own. Regenerate the figures with the "redraw
  every plot" command in the README (`--forcerun
  plot_brain_model_alignment_lineplot ...`). No upstream rule is affected.

## Verification

- Ran the edited script by hand in the built visualisation conda env
  (`.snakemake/conda/961b78e7…`) on the real inputs for
  `caption_scene / cosine / 25NN` (24 models, n = 1000 concepts). The script
  wrote to the session scratchpad, not to `results/`. The PNG showed the
  dashed line at 25/999 ≈ 0.025, listed first in the legend. The test
  image was then deleted.
- Not run: the full `snakemake --forcerun` redraw. No automated tests exist
  for the plotting scripts.

## Follow-ups

- On the fixed `[0, 1]` y-axis, the model means and the null line all sit
  near 0.02–0.03 for small k/n, so the gap between observed and expected
  is barely visible. The enrichment lineplot shows the same comparison on a
  readable scale. Changing the raw lineplot's y-range would break the
  shared axis with the concept-level plot, so that was left alone.
- This script still uses its own inline family-separator and x-axis code.
  The enrichment lineplot uses `add_model_family_annotations()`,
  `style_model_x_axis()` and `save_model_figure()` instead. Switching to the
  shared helpers would be a separate refactor.

---
*AI disclosure: this changelog entry, together with the code change it
describes and the related README edit, was written by an AI coding
assistant.*

- *Tool: Claude Code (Anthropic), VS Code extension, run inside the
  developer's workspace on the lab server.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Date: 2026-09-29.*
- *Basis: the developer (Jonas Salvalaggio) asked whether the raw concept-
  and model-level alignment plots were missing their expected-alignment
  line. The assistant found that only the model-level plot lacked it,
  added the line using the concept-level script's formula, and then wrote
  this documentation on request.*
- *Verification: limited to the checks listed under "Verification".*
- *Temporary files: the only one was the test PNG in the session
  scratchpad, and it was deleted. Nothing was written to `results/`.*
- *Review status: not yet reviewed by the developer at the time of
  writing. Review it before committing.*

*The user changelog entry of the same name gives a plain-language summary.*
