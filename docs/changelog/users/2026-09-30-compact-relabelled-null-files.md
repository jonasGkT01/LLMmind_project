# 2026-09-30 — The shuffled ("relabelled") results now take 4 GB instead of 71 GB

## What changed

- The files holding the shuffled results, which the empirical p-values are built
  from, are now about **10 times smaller**. `results/alignment_scores/` went from
  about 71 GB to about 4 GB.
- There is now **one shuffled-results file per model and similarity metric**, in
  `results/alignment_scores/relabelled_common_neighbours/`. The extra copies,
  one per number of neighbours (`…NN_relabelled.parquet`), are gone.
- **No result changed.** Every p-value, summary table and enrichment value is
  exactly the same as before.

## Why

The old files mostly contained a row counter that nothing used, and two columns
that can be recalculated at any time. Each file was also stored twice. Dropping
these matters especially for the model-model comparisons, whose shuffled results
would otherwise have needed about 1 TB.

## What you need to do

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

---

*This entry was written by an AI coding assistant.*

- *Tool: Claude Code (Anthropic), VS Code extension.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Date: 2026-09-30.*
- *Basis: the change made in the same session at the developer's request (TODO
  entry S23). It was checked by comparing every rewritten file with its old copy,
  and by recomputing p-values and summary-table rows, which came out identical.*
- *Review status: not yet reviewed by the developer at the time of writing.*

*The developer changelog entry of the same name has the technical details.*
