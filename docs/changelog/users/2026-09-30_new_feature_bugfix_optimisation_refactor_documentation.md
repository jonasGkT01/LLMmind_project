# 2026-09-30 — changes for users

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../../AI_USAGE.md).*

Changes made on this day, in order:

- Model-model results now have their own summary table (new_feature)
- The shuffled ("relabelled") results now take 4 GB instead of 71 GB (optimisation)
- The brain-model summary table has a new name (refactor)
- More precise p-value files, a cleaner ISC manifest, and a page on model embeddings (bugfix, documentation)

---

## Model-model results now have their own summary table

Kind: `new_feature`

### What is new

- **A new summary table:** `results/all_model_model_alignment_scores.tsv`.
  It does for model-model alignment what `results/all_alignment_scores.tsv`
  does for brain-model alignment. It lists every pair of models, for every
  dataset, similarity metric and number of neighbours, in one file.
- **The same statistics as the brain-model table.** Model-model comparisons
  now get the same tests as brain-model ones:
  - a p-value for each concept (empirical and hypergeometric);
  - a p-value for the pair as a whole.
- The brain-model table and its numbers **have not changed**.

### How to read the new table

Each row is one number for one model pair:

```
dataset | similarity_type | number_of_neighbours | model_1 | stimuli_type_1 | model_2 | stimuli_type_2 | statistic | value
```

- Each pair is listed **once**. `model_1` is always the model that comes first
  in the `models:` list of `config/config.yaml`.
- The `statistic` names are the same as in `all_alignment_scores.tsv`. The
  pair-level p-value, for example, is `model_level_empirical_p_value`.
- The p-values are **not corrected for multiple testing**. They are also kept
  separate from the brain-model correction.

To get the pair-level p-values for one setting in Python:

```python
import pandas as pd

df = pd.read_csv("results/all_model_model_alignment_scores.tsv", sep="\t")
p = df[(df.dataset == "caption_scene") & (df.similarity_type == "cosine")
       & (df.number_of_neighbours == 25)
       & (df.statistic == "model_level_empirical_p_value")]
```

### What this means for you

- **The next pipeline run recomputes the model-model tests.** Plan for this:
  it needs about 1.1 TB of extra disk space and roughly a day of CPU time,
  mostly for caption_scene and nsd_data.
- The per-pair `…_empirical_…p_value.tsv` files keep their names but now
  list one row **per concept**, like the brain-model ones. The pair-level
  p-value is in the new summary table. If you have your own scripts that
  read those files, point them at the summary table instead.
- The p-value heatmaps now read their model-model p-values from the new
  table. They look the same.

### Context

- Basis: the change made in the same session at the developer's request, checked on five real model pairs whose results matched the earlier ones.

---

## The shuffled ("relabelled") results now take 4 GB instead of 71 GB

Kind: `optimisation`

### What changed

- The files holding the shuffled results, which the empirical p-values are built
  from, are now about **10 times smaller**. `results/alignment_scores/` went from
  about 71 GB to about 4 GB.
- There is now **one shuffled-results file per model and similarity metric**, in
  `results/alignment_scores/relabelled_common_neighbours/`. The extra copies,
  one per number of neighbours (`…NN_relabelled.parquet`), are gone.
- **No result changed.** Every p-value, summary table and enrichment value is
  exactly the same as before.

### Why

The old files mostly contained a row counter that nothing used, and two columns
that can be recalculated at any time. Each file was also stored twice. Dropping
these matters especially for the model-model comparisons, whose shuffled results
would otherwise have needed about 1 TB.

### What you need to do

Nothing. The next time you run the workflow, Snakemake recomputes the
per-concept empirical p-values and the summary table, which is quick, and gets the
same numbers. The shuffling itself, the slow part, is not redone.

If you read the shuffled results yourself, the alignment score is now calculated
from the stored number of shared neighbours:

```python
import pandas as pd

k = 25
df = pd.read_parquet(
    "results/alignment_scores/relabelled_common_neighbours/"
    "dataset-caption_scene_model-bloom_1b1-language_brain_cosine-relabelled_common_neighbours.parquet",
    filters=[("number_of_neighbours", "==", k)],
)
df["alignment_score"] = df["common_neighbours"] / k
```

### Context

- Basis: the change made in the same session at the developer's request (TODO entry S23). It was checked by comparing every rewritten file with its old copy, and by recomputing p-values and summary-table rows, which came out identical.

---

## The brain-model summary table has a new name

Kind: `refactor`

- `results/all_alignment_scores.tsv` is now called
  **`results/all_model_brain_alignment_scores.tsv`**, so it pairs with
  `results/all_model_model_alignment_scores.tsv`.
- Its content is exactly the same. The existing file was renamed, not recomputed.
- If you load the table in your own scripts, or ask Snakemake for it by name, use the new
  name:

  ```bash
  snakemake --use-conda --cores <N> results/all_model_brain_alignment_scores.tsv
  ```

### Context

- Basis: the rename the developer asked for in the same session.

---

## 20:06 — More precise p-value files, a cleaner ISC manifest, and a page on model embeddings

Kind: `bugfix`, `documentation`

- **Very small p-values are no longer rounded away.** The per-concept p-value files
  (`results/alignment_scores/*.p_value.tsv`) and the Spearman tables
  (`results/spearman_alignment_scores/*.p_value.tsv`) now keep 6 *significant* digits instead of
  6 decimals. Before, a p-value smaller than 0.0000005 would have been written as `0.000000`,
  and small values lost most of their digits. Very small values now appear in scientific
  notation, such as `3.12e-06`. Spreadsheet programs and `pandas` read this format directly.
- **`isc_inputs.tsv` no longer has an unnamed first column.** The file
  `results/mind/<dataset>/manifests/isc_inputs.tsv` now has just the columns `dataset`, `task`
  and `isc_file`.
- **New page: [`docs/reference/model_embeddings.md`](../../reference/model_embeddings.md).**
  It explains, for the methods section, how each model turns a stimulus into one vector: how long
  texts are split into chunks, that the average over tokens includes the start-of-text (BOS)
  token, and which token vision models use.

Nothing is recomputed automatically. The existing files keep their old format until the
pipeline regenerates them, planned for the next full rerun. The numbers are the same, only
written with more digits. Summary statistics computed from them may change in their last digits.

### Context

- Basis: a project review requested by the developer, who approved these changes.
