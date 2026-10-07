# Statistics: alignment scores, null distributions, tests and figures

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../AI_USAGE.md).*

This page describes how the workflow measures brain-model and model-model alignment, how it tests
it, and what the figures show. It is written from the code (`workflow/libraries/` and the
`llm_mind_alignment/`, `llm_llm_alignment/`, `spearman_alignment/` and `visualisation/`
scripts). Use it as the source for the methods section.

Notation: *n* concepts (stimuli) per dataset, *k* nearest neighbours, *N* relabellings
(`number_of_relabellings` in `config/config.yaml`, 10,000), random seed `random_seed` (37).

## 1. Alignment score

For each concept, both representations (the brain's ISC vectors and a model's embeddings, or two
models' embeddings) give a set of *k* nearest neighbours among the other *n* − 1 concepts, under
one similarity type (cosine, Pearson or Spearman). The concept's **alignment score** is the number
of neighbours the two sets share, divided by *k*, so it lies in [0, 1]
(`compute_alignment.compute_alignment_scores()`). The **model-level alignment score** is the mean
over concepts.

## 2. Relabelling null

The null hypothesis is that the two representations are unrelated beyond chance. It is built by
permuting the concept labels of one side:

- **LLM-brain:** the brain side stays fixed and the model's labels are permuted. **LLM-LLM:** the
  first model stays fixed and the second model's labels are permuted.
- In shuffle *i*, concept *c* receives the neighbour set of concept π(*c*), with every neighbour
  renamed through the same permutation π (`compute_nearest_neighbours.relabel_nearest_neighbours()`).
  The neighbourhood structure of the permuted side is therefore preserved; only its link to the
  concept labels is broken.
- One permutation per shuffle is reused for every *k*
  (`compute_relabelled_alignment.compute_relabelled_common_neighbours_for_all_k()`).
- **Random stream:** every null (alignment score, enrichment, Spearman) draws its *N*
  permutations in sequence from one `numpy.random.default_rng(random_seed)` stream
  (`compute_relabelled_alignment.compute_relabelled_common_neighbours_for_all_k()` and the
  Spearman script). Every test only draws `permutation(n)`, so the alignment and Spearman tests of
  a dataset use exactly the same permutations, and all models share them on purpose (a paired
  design). A replication run only needs a different seed.

## 3. Tests of the alignment score

All tests are one-sided (upper tail): they ask whether the alignment is larger than chance.

| Test | Level | Statistic | p-value | Output column |
|---|---|---|---|---|
| Empirical | concept | the concept's alignment score | (*b* + 1)/(*N* + 1), *b* = number of relabellings whose score for that concept is ≥ the observed one | `empirical_upper_tail_p_value` (per-concept TSV) |
| Hypergeometric | concept | the concept's number of common neighbours *x* | P(*X* ≥ *x*), *X* ~ Hypergeometric(population *n* − 1, *k* successes, *k* draws) | `hypergeometric_upper_tail_p_value` (per-concept TSV) |
| Empirical | model | the mean alignment score over concepts | (*b* + 1)/(*N* + 1), *b* = number of relabellings whose mean score is ≥ the observed mean | `model_level_empirical_p_value` (summary TSVs) |

The (*b* + 1)/(*N* + 1) form (`compute_statistics.empirical_upper_tail_p_value()`) counts the
observed value as one draw of the null, so a p-value is never 0; with *N* = 10,000 the smallest
possible value is about 1 × 10⁻⁴.

The **hypergeometric expectation** of every concept's alignment score is *k*/(*n* − 1): two random
*k*-subsets of *n* − 1 concepts share *k*²/(*n* − 1) elements on average. It is the dashed
reference line of the alignment-score line plot and concept scatterplot, and the subtitle of the
alignment heatmap.

**The model-level test is `model_level_empirical_p_value`.** The six statistics
`{mean,median,min}_{empirical,hypergeom}_p_value_across_concepts` in
`results/all_model_brain_alignment_scores.tsv` and `results/all_model_model_alignment_scores.tsv`
are descriptive summaries of the per-concept p-values, **not tests**: a mean or median of
p-values has no calibrated interpretation, and the minimum is the best concept's uncorrected
p-value. They are kept on purpose (decision of 2026-09-30) but must not be reported as model-level
p-values.

## 4. Enrichment

The enrichment plots (`compute_alignment_enrichment.compute_model_alignment_enrichment()`)
express alignment relative to the relabelling null of the same model:

- **expected score** = mean relabelled alignment score over every relabelling and every concept;
- **concept-level enrichment** = observed score / expected score;
- **model-level enrichment** = mean observed score / expected score, which is exactly the mean of
  the concept-level enrichments, since both use the same expected score;
- **model-level null SD** = SD over relabellings of the mean relabelled score, divided by the
  expected score.

Enrichment = 1 means chance-level alignment.

## 5. Multiple testing

Benjamini-Hochberg q-values are computed in the plotting scripts
(`compute_statistics.benjamini_hochberg()`). **Rule: one Benjamini-Hochberg family per
(dataset, similarity type, *k*, statistic); brain-model and model-model tests are corrected
separately.** The families are:

| Family | Members | Used by |
|---|---|---|
| Brain-model alignment | `model_level_empirical_p_value` of every model, for one (dataset, similarity, *k*) | the alignment line plot, the concept scatterplot, both enrichment plots and the brain row/column of the p-value heatmap (`compute_statistics.model_level_significance()`), so their asterisks agree |
| Model-model alignment | `model_level_empirical_p_value` of every model pair, for one (dataset, similarity, *k*) | the model-model cells of the p-value heatmap |
| Spearman | model-level Spearman p-value of every model, for one (dataset, similarity) | the two Spearman plots |

There is no correction across *k* values, datasets or similarity types: the *k* values are a
sensitivity analysis, and each configuration is reported on its own. The summary TSVs contain the
uncorrected p-values only. The per-concept p-values are not corrected and not shown as asterisks.

## 6. Spearman alignment

`spearman_alignment/scripts/compute_spearman_alignment_with_empirical_p_value.py` compares the
full similarity structure instead of the neighbour sets:

- **model level:** Spearman's ρ between the brain's and the model's pairwise concept
  similarities (the upper triangle of the two *n* × *n* similarity matrices);
- **concept level:** for each concept, Spearman's ρ between its similarities to the other
  *n* − 1 concepts in the brain and in the model;
- **null:** the model's concept labels are permuted *N* times, with all permutations drawn from
  one `default_rng(random_seed)` stream, and ρ is recomputed;
- **p-value:** upper tail, (*b* + 1)/(*N* + 1) as in section 3;
- **null SD:** the SD of the *N* relabelled model-level coefficients
  (`empirical_null_standard_deviation_spearman_coefficient`).

It runs once per similarity type, so with the `spearman` similarity it is a Spearman correlation
between two Spearman similarity structures: the first compares stimuli, the second compares the
brain's and the model's similarity structures.

## 7. What the figures show

| Figure | Point or box | Error bar | Grey reference |
|---|---|---|---|
| Model-level alignment line plot | mean alignment score over concepts | standard error of that mean across concepts (SD/√*n*) | dashed line at the hypergeometric expectation *k*/(*n* − 1) |
| Concept-level alignment scatterplot | one point per concept, boxplot per model | none | dashed line at *k*/(*n* − 1) |
| Model-level enrichment line plot | model-level enrichment | that model's null SD | dashed line at enrichment = 1 |
| Concept-level enrichment scatterplot | one point per concept, boxplot per model | none | dashed line at enrichment = 1 |
| Model-level Spearman line plot | model-level ρ | that model's null SD | dashed line at ρ = 0 |
| Concept-level Spearman scatterplot | one point per concept, boxplot per model | none | dashed line at ρ = 0 |
| Alignment heatmap | mean alignment score of each pair; the diagonal is blank | — | — |
| p-value heatmap | −log10 of each pair's model-level empirical p-value; the diagonal is blank | — | — |

Conventions:

- **What the error bars mean differs between plots.** In the alignment line plot, the bar is the
  standard error of the plotted mean, an uncertainty of the value. In the model-level enrichment
  and Spearman plots, the bar is the model's null SD drawn around the observed value (the y-label
  reads "± null SD"): it shows how wide chance variation is for that model, but the null
  distribution is centred on chance (enrichment = 1, ρ = 0), not on the observed value, so the bar
  is not a confidence interval and whether it reaches the reference line is not a significance
  test.
- **Significance is carried by asterisks:** in the model plots, black asterisks give the
  uncorrected model-level empirical p-value and blue asterisks below them the Benjamini-Hochberg
  q-value (`*` < 0.05, `**` < 0.01, `***` < 0.001); in the p-value heatmap, the asterisks give the
  q-value. Section 5 lists the families.
- The concept-level enrichment and Spearman scatterplots draw no error bars, to stay readable.

Layout, shared by all plots (constants and helpers in `libraries/visualisation_utils.py`):

- **Names.** The "scatterplots" in rule, script and folder names are concept-level boxplots with
  one point per concept; the name is historical.
- **Titles and labels.** Titles read `<level> <quantity>` (for example "Model-level brain-model
  alignment enrichment"), with `dataset: …, similarity: …, neighbours: …` on the second line.
  Y-axis labels read `<quantity> ± <error>`, or just `<quantity>` when the plot has no error bars.
- **Legend.** Inside the plot, in its top-left corner; the top quarter of the y-range is left
  empty so the legend never hides data. The heatmaps are the exception: their only legend (the
  stimulus-type colours) sits in the figure's bottom-left corner. Concept names are never listed.
- **Model order.** The same in every plot: model family (alphabetical), then number of parameters
  (`parameters_millions` in `config/config.yaml`), then model name, then stimulus type
  (`model_sort_key()` in `libraries/manage_model_metadata.py`). The order of the `models:` block
  does not matter. In the heatmaps the brain comes after all models. Every non-heatmap plot draws
  dashed vertical lines between model families.
- **Colours.** Model names show the model only (`clip_b`, not `clip_b-vision`), coloured by
  stimulus type: dark orange (`#A84800`) for language, dark green (`#007A5A`) for vision, black
  for the brain (`STIMULI_TYPE_COLOURS`), on both axes of the heatmaps. In the model-level line
  plots the points take the same colour, as circles (language) or squares (vision). Boxes are not
  coloured. Concept-level plots give each concept the same colour for every model in the plot.
- **Colour-vision deficiency.** The stimulus-type pair passes a colour-blindness simulation
  (protan, deutan, tritan) with ≥ 5:1 contrast on white, the heatmaps use `viridis`, and red is
  avoided for the q-value asterisks and the degenerate-box marker. The per-concept colours are
  the exception: with 11 to 1,000 concepts, no palette keeps them distinguishable.
- **Degenerate boxes.** In the concept-level alignment and Spearman plots, a model whose
  per-concept values show no spread would render as a flat, easy-to-miss box; it is marked with a
  black diamond instead.
- **Shared y-axes.** The model-level alignment line plot and the concept-level alignment plot of
  one dataset/similarity/*k* share the y-range `[0, 1]` (plus legend space), so they can be
  compared side by side. The two enrichment plots share one range too, computed from both
  (`enrichment_ylim()` in `libraries/compute_alignment_enrichment.py`) so that every concept,
  model-level value and its error bar fits. Their y-axis is linear from 0 to 1 and log10 above 1
  (matplotlib `symlog`, `set_enrichment_y_scale()`), with [0, 1] as tall as one decade, so a few
  very high concepts don't squash the rest. Because the range must fit the highest concepts, the
  model-level null-SD error bars (about 0.05) are often shorter than the markers; the shared range
  is kept on purpose, so the two plots stay comparable.

## 8. Changes

Changes to the methods described above, oldest first. Each entry gives when the change happened,
what changed and why. The sections above always describe the current code.

### 2026-10-02 09:50 — one random stream for every null

Until then, shuffle *i* of the relabelling null used `default_rng(random_seed + i)`, while the
Spearman null drew from one `default_rng(random_seed)` stream. Now every null draws from one
stream (section 2), so the alignment and Spearman tests of a dataset use the same permutations.
Results computed before the full rerun of 2026-10-02 use the old scheme.

### 2026-10-05 11:10 — file renamed

Renamed from `2026-10-02_0925_statistics.md` to `statistics.md` (living reference pages carry no
date in their name); the dated note of section 2 moved to the entry above. The content was
checked against the current code (function names, columns, `config.yaml` values) and needed no
other change.

### 2026-10-06 16:30 — plot layout conventions moved here; TODO ID and attribution block removed

The plot layout conventions (titles, legends, model order, colours, degenerate boxes, shared
y-axes) moved here from the "Outputs" section of `README.md`, which now links to this page,
together with the note on Spearman alignment under the `spearman` similarity (section 6). The
TODO reference in the entry of 2026-10-02 was removed, and the AI attribution block at the end was
replaced by the note under the title.

### 2026-10-07 16:30 — null SD drawn as the error bar of the model-level points

At the developer's request, the model-level enrichment and Spearman plots now draw each model's
null SD as the error bar of its point, instead of as a grey interval "Null ± 1 SD" around the
reference line (enrichment = 1, ρ = 0), which they had done since 2026-10-02. The y-labels read
"± null SD", the y-ranges fit value + null SD, and section 7 explains that the bar is the spread
of the null, not a confidence interval.
The developer chose to keep the shared y-range of the two enrichment
plots, even though the bars are often shorter than the markers there.

