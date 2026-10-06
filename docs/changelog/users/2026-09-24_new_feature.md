# 2026-09-24 — changes for users

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../../AI_USAGE.md).*

Changes made on this day, in order:

- New enrichment plots, error bars on Spearman plots, and clearer, consistent plots (new_feature)
- You can now choose how many subjects must have seen a stimulus (new_feature)

---

## New enrichment plots, error bars on Spearman plots, and clearer, consistent plots

Kind: `new_feature`

### What changed

- **New enrichment plots.** For each dataset, similarity and neighbourhood
  size there are now two more plots:
  - `results/alignment_enrichment_lineplots/` (one point per model);
  - `results/concept_alignment_enrichment_scatterplots/` (one point per
    concept).

  They show how many times larger the observed alignment is than expected
  by chance (1 = no better than chance, marked by a dashed line). The
  expected value and the error bars both come from the random relabellings
  the pipeline already runs. The error bars show how much the enrichment
  varies by chance. The two plots for the same settings share their
  vertical axis.
- **Error bars on the Spearman plots.** Both Spearman plots now show the
  same kind of chance-level error bar.
- **Two kinds of significance asterisks** on every brain-model plot (not
  the heatmaps):
  - black: the model passes the plain p-value test;
  - red, just above: it also passes the Benjamini-Hochberg correction.

  On the concept-level plots they appear at the top of each model's
  column.
- **Model families** are separated by dashed vertical lines on every plot
  except the heatmaps.
- **Concept colours.** On concept-level plots each concept has its own
  colour, the same for every model in that plot. Plots with at most 20
  concepts list them in a legend.
- **Consistent titles and labels.** Every title now reads like
  "Model-level brain-model alignment enrichment". Its second line gives
  the dataset, similarity and number of neighbours.

### What this means for you

- To get the Spearman error bars, the Spearman step must be rerun once:
  `snakemake --use-conda --cores <N> --forcerun compute_spearman_alignmentwith_empirical_p_value`.
  Until then, the Spearman plots stop with an error about a missing column.
- The enrichment plots take a few minutes each on the large datasets
  (Caption Scene, NSD).
- On datasets with about 1,000 concepts, a few concepts reach very high
  enrichment. Because the two enrichment plots share their vertical axis,
  the model-level one then shows its points close to 1.

### Context

- Basis: the developer's instructions in the same session.

---

## You can now choose how many subjects must have seen a stimulus

Kind: `new_feature`

### What changed

A stimulus is used in the analysis only if enough different subjects saw
it. That number used to be fixed at 2 inside the code. It is now a setting
at the top of `config/config.yaml`, next to `number_of_relabellings` and
`random_seed`:

```yaml
minimum_subjects_per_stimulus: 2
```

### What this means for you

- The default is still 2, so results do not change unless you change the
  value.
- Raising it keeps only stimuli seen by more subjects. This applies to
  Caption Scene, NSD and Narratives. Nature Stories already requires every
  subject to have heard every story.
- Changing the value makes Snakemake rebuild the stimulus lists and
  everything that depends on them.

### Context

- Basis: the developer's instructions in the same session.
