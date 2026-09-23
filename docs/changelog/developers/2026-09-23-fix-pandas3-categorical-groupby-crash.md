# 2026-09-23 — Fix pandas 3 crash in `relabel_llm_similarity_and_compute_relabelled_llm_alignment_score`

## Summary

The 2026-09-23 run (`.snakemake/log/2026-09-23T112911.353357.snakemake.log`)
stopped at 358/8031 steps. Rule
`relabel_llm_similarity_and_compute_relabelled_llm_alignment_score` failed
for `dataset=nature_stories, model=bloom_560m, stimuli_type=language,
similarity_type=cosine` (k=3) with:

```
File ".../relabel_llm_similarity_and_compute_relabelled_llm_alignment_score.py", line 22, in encode_brain_nearest_neighbours
    neighbours_by_concept = brain_nearest_neighbours_df.groupby("concept", sort=False)["neighbour"].agg(list).to_dict()
TypeError: unhashable type: 'list'
```

The Snakemake log shows only `CalledProcessError`. The traceback above came
from re-running the rule's shell command by hand in its conda env
(`.snakemake/conda/8c935a13331796cb2f07682d758b4d59_`).

## Root cause

- `isc_{similarity_type}_nearest_neighbours.parquet` stores `concept` and
  `neighbour` as `category`, a deliberate storage choice
  (`libraries/compute_nearest_neighbours.py`, shared `CategoricalDtype`).
- The rule's env resolves to **pandas 3.0.5, Python 3.14**, because
  `envs/llm_mind_alignment_environment.yaml` does not pin `pandas`.
- In pandas 3, `SeriesGroupBy.agg(list)` on a categorical column tries to
  cast the aggregated result back to the column's `CategoricalDtype`. That
  means looking each per-group `list` up in the categories index, and a list
  is unhashable.
- The input data is fine: 11 concepts × 3 neighbours for Nature Stories.

## Change

`workflow/llm_mind_alignment/scripts/relabel_llm_similarity_and_compute_relabelled_llm_alignment_score.py`,
`encode_brain_nearest_neighbours`:

```diff
-    neighbours_by_concept = brain_nearest_neighbours_df.groupby("concept", sort=False)["neighbour"].agg(list).to_dict()
+    neighbours_by_concept = brain_nearest_neighbours_df.groupby("concept", sort=False, observed=True)["neighbour"].apply(list).to_dict()
```

- `.apply(list)` returns an object Series of Python lists and does not cast
  back to the categorical dtype.
- `observed=True` keeps only categories that actually occur as a group
  instead of the full category set. It was already the pandas 3 default;
  passing it explicitly guards against older pandas versions, where the
  default was `False`.
- Behaviour is otherwise unchanged:
  - neighbour order within each group follows row order, which is the
    stored similarity ranking;
  - the missing-concept and too-few-neighbours checks further down still
    run, via `.get(concept, [])`.

No other workflow script uses `.agg(list)`. The other `groupby` call sites
were not audited for pandas-3 categorical behaviour.

## Verification performed

- Reproduced the failure by re-running the failing command with
  `--number_of_relabellings 2`, output written to a scratch directory.
- Confirmed in isolation, against the same input file, that `.agg(list)`
  raises the `TypeError` and that `.apply(list)` returns the expected
  mapping (e.g. `alternateithicatom → ['life', 'avatar', 'undertheinfluence']`).
- Ran the patched script end to end with the exact production arguments
  (`--number_of_neighbours 3 --number_of_relabellings 1000 --random_seed 37`),
  output written to a scratch directory. It completed all 1000 relabellings
  and wrote an 11,000 × 7 parquet with the expected columns.

**Not verified:**

- The Snakemake workflow has not been restarted.
- No other `(dataset, model, similarity_type)` combination of this rule has
  been run with the patch.
- Results were not compared numerically against a pandas-2 run.

## Follow-ups

- Restart with `--rerun-incomplete`. The crashed run left entries in
  `.snakemake/incomplete`.
- Consider pinning `pandas` (and `python`) in
  `envs/llm_mind_alignment_environment.yaml`. Until then, any env rebuild
  can pull in a new major version.
- Other scripts that `groupby` on categorical columns from the
  nearest-neighbour parquets may hit similar pandas-3 differences.

---

*AI disclosure: this changelog entry, together with the diagnosis and the
code change it describes, was written by an AI coding assistant.*

- *Tool: Claude Code (Anthropic), VS Code extension.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`, 1M-token context).*
- *Date: 2026-09-23.*
- *Basis: the Snakemake log of the crashed run, a manual re-run of the
  failing command in the rule's conda env, and the developer's (Jonas
  Salvalaggio) go-ahead to apply the fix.*
- *Verification: limited to the checks listed under "Verification
  performed".*
- *Review status: not yet reviewed by the developer at the time of writing.
  Review it before committing.*
