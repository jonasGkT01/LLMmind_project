# 2026-09-30 — Model-model results now have their own summary table

## What is new

- **A new summary table:** `results/all_model_model_alignment_scores.tsv`.
  It does for model-model alignment what `results/all_alignment_scores.tsv`
  does for brain-model alignment. It lists every pair of models, for every
  dataset, similarity metric and number of neighbours, in one file.
- **The same statistics as the brain-model table.** Model-model comparisons
  now get the same tests as brain-model ones:
  - a p-value for each concept (empirical and hypergeometric);
  - a p-value for the pair as a whole.
- The brain-model table and its numbers **have not changed**.

## How to read the new table

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

## What this means for you

- **The next pipeline run recomputes the model-model tests.** Plan for this:
  it needs about 1.1 TB of extra disk space and roughly a day of CPU time,
  mostly for caption_scene and nsd_data.
- The per-pair `…_empirical_…p_value.tsv` files keep their names but now
  list one row **per concept**, like the brain-model ones. The pair-level
  p-value is in the new summary table. If you have your own scripts that
  read those files, point them at the summary table instead.
- The p-value heatmaps now read their model-model p-values from the new
  table. They look the same.

---
*AI disclosure: this note was written by an AI coding assistant.*

- *Tool: Claude Code (Anthropic), VS Code extension.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Date: 2026-09-30.*
- *Basis: the change made in the same session at the developer's request,
  checked on five real model pairs whose results matched the earlier ones.*
- *Review status: not yet reviewed by the developer at the time of writing.*

*The developer changelog entry of the same name has the technical details.*
