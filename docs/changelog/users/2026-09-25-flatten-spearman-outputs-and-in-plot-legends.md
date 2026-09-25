# 2026-09-25 — Spearman results moved, and tidier plots

## What changed

- **The Spearman results have moved.** They used to be in a separate
  folder, `results/spearman_alignment/`. They are now directly in
  `results/`, next to the other alignment results:

  | What | Where it is now |
  |---|---|
  | Spearman scores and p-values, one file per model and level | `results/spearman_alignment_scores/` (file names end in `_model_level.p_value.tsv` or `_concept_level.p_value.tsv`) |
  | Model-level Spearman plot | `results/spearman_alignment_lineplots/` |
  | Concept-level Spearman plot | `results/concept_spearman_alignment_scatterplots/` |
  | Summary table | `results/all_spearman_alignment_scores.tsv` (unchanged) |

  The existing files were moved and renamed, not recomputed. Their
  contents are the same.
- **The legend is inside the plot.** It sits in the top-left corner. The
  top of each plot is left empty, so the legend never covers any points.
- **Stimulus names are no longer listed in the legend.** On the
  concept-level plots each stimulus still has its own colour, the same for
  every model.
- **The significance asterisks have moved.** They now sit just below the
  horizontal axis, right above each model's name. The black row is the
  plain p-value test; the red row, below it, is the Benjamini-Hochberg
  correction.
- **No more error bars on individual concepts.** The concept-level
  enrichment plot and the concept-level Spearman plot showed a thin
  vertical bar on every point. Those bars are gone, because they made the
  plots hard to read. The model-level plots keep their error bars.
- On the alignment-score plots, the vertical axis now goes a little past 1,
  to make room for the legend. The labels still stop at 1.

## What this means for you

- **Update any script or notebook that reads from
  `results/spearman_alignment/`.** That folder no longer exists; use the
  new locations above.
- **The plots in `results/` are still the old ones.** Snakemake doesn't
  notice changes to how plots are drawn, so you have to ask it to redraw
  them:

  ```bash
  snakemake --use-conda --cores <N> --rerun-triggers mtime \
      --forcerun plot_brain_model_alignment_lineplot plot_concept_alignment_scatterplot \
                 plot_brain_model_alignment_enrichment_lineplot \
                 plot_concept_alignment_enrichment_scatterplot plot_spearman_alignment
  ```

- **For Narratives and Nature Stories, the Spearman step has to be rerun
  first.** Their Spearman results are older than the 2026-09-24 update, so
  their Spearman plots can't be drawn yet. That is also why, for now, their
  Spearman scatterplots show every stimulus in the same colour. Add
  `compute_spearman_alignmentwith_empirical_p_value` to the `--forcerun`
  list above.
- On Narratives (18 stories), some pairs of stimulus colours are still
  quite similar. A clearer set of colours has been suggested but not made
  yet.

---
*AI disclosure: this note was written by an AI coding assistant.*

- *Tool: Claude Code (Anthropic), VS Code extension.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Date: 2026-09-25.*
- *Basis: the developer's instructions in the same session.*
- *Review status: not yet reviewed by the developer at the time of writing.*

*The developer changelog entry of the same name lists exactly what was
changed and tested.*
