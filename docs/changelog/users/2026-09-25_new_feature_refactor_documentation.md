# 2026-09-25 — changes for users

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../../AI_USAGE.md).*

Changes made on this day, in order:

- What happens when you change `minimum_subjects_per_stimulus` (documentation)
- Spearman results moved, and tidier plots (new_feature, refactor)
- Enrichment plots no longer squashed by a few extreme concepts (new_feature)
- Enrichment plots now show every point, with a log scale above 1 (new_feature)
- All plots are now in `results/pictures/` (refactor)
- Multimodal models are now compared with themselves across text and images (new_feature)

---

## What happens when you change `minimum_subjects_per_stimulus`

Kind: `documentation`

### What changed

Nothing in how the pipeline works. This note explains what to expect when
you change the `minimum_subjects_per_stimulus` setting in
`config/config.yaml`.

### What this means for you

- **You don't need to delete anything.** Change the value and run
  Snakemake again. It rebuilds every result that depends on the setting.
- **Expect a long run.** For Caption Scene and NSD, both the brain data and
  the model embeddings are recomputed, and the embeddings use the GPU.
  Changing the value from 2 to 3 adds roughly 6,000 jobs.
- **Narratives and Nature Stories are usually not affected.** Nature Stories
  doesn't use this setting. In Narratives every story was heard by at least
  14 subjects, so nothing changes until you set 15 or more.
- **Use a value from 2 to 8.** Below 2 there is nothing to compare between
  subjects, and the pipeline stops with an error. Caption Scene and NSD have
  8 subjects each, so above 8 no stimulus would be left.
- **Preview first.** This command shows what would run for a given value,
  without changing the config file or running anything:

  ```bash
  snakemake -n --cores 8 --rerun-triggers mtime params input code \
      --config minimum_subjects_per_stimulus=3 --quiet rules
  ```

- **One known issue (Narratives, values of 15 or more only).** If you raise
  the value and later lower it again, the Narratives step may stop with a
  "missing output" error. Add `--forcerun write_narratives_parcel_manifest`
  to your command to fix it.

### Context

- Basis: the developer's question in the same session, answered by reading the workflow code and running dry runs.

---

## Spearman results moved, and tidier plots

Kind: `new_feature`, `refactor`

### What changed

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

### What this means for you

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

### Context

- Basis: the developer's instructions in the same session.

---

## Enrichment plots no longer squashed by a few extreme concepts

Kind: `new_feature`

### What changed

- **Taller, more readable enrichment plots.** Before, a handful of concepts
  with very high enrichment set the height of the vertical axis. Everything
  else was pressed flat against the bottom of the plot. The axis now stops
  where the boxplot whiskers end, so the boxes and most points are visible.
  This applies to both plots:
  - `results/alignment_enrichment_lineplots/`
  - `results/concept_alignment_enrichment_scatterplots/`
- **The two plots still share their vertical axis**, so you can compare them
  side by side.
- **Nothing is removed from the results.** The extreme concepts are only left
  off the drawing. They still count in the boxes, the model-level values and
  every significance test.
- **You're told what is hidden.** When some concept points fall above the
  axis, the concept-level plot's legend says how many, for example
  "113 of 24000 concept points above the axis (not shown)".

### How the cut-off is chosen

A point is left off the drawing only if the boxplot already treats it as an
outlier. That means it is above the top of the box plus 1.5 times the box's
height (a standard rule known as Tukey's fence). Each model's values and error
bars always stay visible, and so does the dashed "enrichment = 1" line.

### What this means for you

- **Redraw the plots once to see the change.** Snakemake doesn't notice
  changes to plotting code by itself, so use the "redraw every plot" command
  in the README. No other step needs to rerun.
- **Some plots can still look low.** Sometimes most concepts genuinely spread
  much higher than the model averages. In that case the model-level line
  still sits in the lower part of its plot, because it shares the axis with
  the concept plot.
- **Very small neighbourhoods can give almost-empty concept plots.** For
  example, NSD with 5 neighbours: when nearly every concept scores 0, all the
  non-zero concepts count as outliers and are hidden. The legend count tells
  you when this happens.

### Context

- Basis: the change made in the same session at the developer's request, checked by regenerating all enrichment plots.

---

## Enrichment plots now show every point, with a log scale above 1

Kind: `new_feature`

### What changed

- **All points are back on the enrichment plots.** The earlier change the
  same day hid a few very high concepts to keep the plots readable. That is
  undone, and nothing is hidden any more.
- **New vertical axis.** From 0 to 1 the axis is ordinary (evenly spaced).
  Above 1 it is logarithmic: 1 to 10 takes the same height as 10 to 100, and
  the same height as 0 to 1. Very high values therefore fit without
  squeezing everything else against the bottom.
- **Clear tick labels:** 0, 0.25, 0.5, 0.75, 1, 2, 5, 10, 20, 50 and so on.
- **The two enrichment plots still share their vertical axis:**
  - `alignment_enrichment_lineplots/` (one point per model);
  - `concept_alignment_enrichment_scatterplots/` (one point per concept).
- The note "N concept points above the axis (not shown)" is gone from the
  legend, because no points are hidden now.

### What this means for you

- **Read the axis carefully above 1.** Equal distances mean equal *ratios*
  there, not equal differences. For example, going from 2 to 4 looks as big
  as going from 20 to 40.
- **The model-level line can still look flat.** Model averages are usually
  between 1.0 and 1.2. When some concepts reach much higher values, that
  range takes up only a small part of the plot.
- **Redraw once** with the "redraw every plot" command in the README.

### Context

- Basis: the change made in the same session at the developer's request, checked by regenerating all enrichment plots.

---

## All plots are now in `results/pictures/`

Kind: `refactor`

### What changed

- **One place for every picture.** All plots and heatmaps are now saved
  inside `results/pictures/`, not directly in `results/`.
- **Same subfolders as before.** Each kind of plot keeps its own subfolder,
  for example `results/pictures/alignment_heatmaps/` or
  `results/pictures/concept_alignment_enrichment_scatterplots/`. File names
  haven't changed.
- **Existing plots were moved, not redrawn.** In this copy of the project the
  old folders are already inside `results/pictures/`.
- The other results (score tables, embeddings, brain data) stay where they
  were.

### What this means for you

- **Look for plots in `results/pictures/`** from now on. Update any
  shortcuts, scripts or slides that point to the old folders.
- **If you have your own copy of the project with plots already made,** move
  the old folders once so the plots don't all get drawn again:

  ```bash
  mkdir -p results/pictures
  for d in alignment_heatmaps alignment_p_value_heatmaps alignment_lineplots \
           concept_alignment_scatterplots alignment_enrichment_lineplots \
           concept_alignment_enrichment_scatterplots spearman_alignment_lineplots \
           concept_spearman_alignment_scatterplots; do
      [ -d "results/$d" ] && mv "results/$d" results/pictures/
  done
  ```

  If you skip this, nothing breaks. The pipeline simply draws the plots again
  in the new place, and the old folders stay behind until you delete them.

### Context

- Basis: the change made in the same session at the developer's request.

---

## Multimodal models are now compared with themselves across text and images

Kind: `new_feature`

> **Update 2026-09-29:** multimodal model support has been
> removed, so the multimodal parts of this entry no longer apply. Gemma 3n and
> Gemma 4 now run as language models. See
> `2026-09-29_new_feature_removal.md`. *(Note added by Claude Code,
> Claude Opus 5.5, `claude-opus-5-5`.)*

### What changed

- **New model-vs-model comparisons.** A multimodal model (one with
  `modality: "multimodal"` in `config/config.yaml`) is now compared with
  itself: its neighbourhoods from the text stimuli against its neighbourhoods
  from the image stimuli. Example output:
  `results/alignment_scores/dataset-caption_scene_model-gemma3n_e4b-language_model-gemma3n_e4b-vision_cosine-alignment_score_25NN.parquet`,
  plus the matching `_empirical_..._p_value.tsv`.
- **Only datasets with both text and images are affected.** Today that is
  `caption_scene`.
- **Nothing else changes.** Every comparison that existed before is still
  made, and keeps the same file name.

### What this means for you

- **No effect with the current configuration.** None of the enabled models
  is multimodal. The new comparisons appear once you uncomment the
  Gemma 3n / Gemma 4 models.
- **The model-vs-model heatmaps don't show these comparisons yet.** They name
  rows and columns by model only, not by model plus stimulus type. With a
  multimodal model enabled, the p-value heatmap will stop with a
  "provided more than once" error. The score files themselves are correct.
  *Update 2026-09-29: fixed. The heatmaps now show each model's language and
  vision entries separately.*

### Context

- Basis: the change made in the same session at the developer's request.
