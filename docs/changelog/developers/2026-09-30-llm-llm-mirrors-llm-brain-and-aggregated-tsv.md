# 2026-09-30 — LLM-LLM statistics mirror LLM-brain; new `all_model_model_alignment_scores.tsv`

## Summary

- The `llm_llm_alignment/` workflow now runs the same statistical chain as
  `llm_mind_alignment/`: all-k relabelling → per-k relabelled scores →
  per-concept empirical and hypergeometric p-values → one aggregated long TSV.
- New output: `results/all_model_model_alignment_scores.tsv`, the model-model
  counterpart of `results/all_alignment_scores.tsv`, with the same 17
  statistics per configuration and 11,184 configurations (`len(LLM_LLM_PAIRINGS)`).
- Duplicated code is now in two new shared libraries, and the LLM-brain scripts
  import it. `all_alignment_scores.tsv` is byte-identical before and after
  (see Verification).
- No multiple-testing correction is applied in the new TSV. The LLM-brain BH
  family is unchanged.

## Output schema

```
dataset | similarity_type | number_of_neighbours | model_1 | stimuli_type_1 | model_2 | stimuli_type_2 | statistic | value
```

- The metadata columns are also the sort order. Statistic rows keep the order
  of `aggregate_model_results()`, as in `all_alignment_scores.tsv`.
- Float format `%.10g`, as in the LLM-brain TSV.
- **Canonical pair order:** each unordered pair appears once, with `model_1` no
  later than `model_2` in `config["models"]` order. This is the order that
  `llm_llm_pairings()` (`workflow/Snakefile`) already produces through
  `itertools.combinations` over model-major representations. The aggregator
  checks it (`validate_canonical_pair_order()`, with `--model_order` from
  `MODEL_KEYS`) and fails on a reversed or duplicated pair.

## Rules (`workflow/llm_llm_alignment/Snakefile`)

| Rule | Mirrors (llm_mind_alignment) | Script |
|---|---|---|
| `relabel_llm_similarity_and_compute_relabelled_llm_llm_alignment_score` (new) | `relabel_llm_similarity_and_compute_relabelled_llm_alignment_score` | `llm_llm_alignment/scripts/relabel_llm_similarity_and_compute_relabelled_llm_llm_alignment_score.py` (new) |
| `extract_llm_llm_relabelled_alignment_score_for_k` (new) | `extract_relabelled_alignment_score_for_k` | reuses `llm_mind_alignment/scripts/extract_relabelled_alignment_score_for_k.py` |
| `compute_llm_llm_empirical_p_value` (rewritten) | `compute_empirical_p_value` | reuses `llm_mind_alignment/scripts/compute_empirical_p_value.py` |
| `compute_llm_llm_hypergeometric_p_value` (new) | `compute_hypergeometric_p_value` | reuses `llm_mind_alignment/scripts/compute_hypergeometric_p_value.py` |
| `aggregate_all_llm_llm_p_value_outputs` (new) | `aggregate_all_p_value_outputs` | `llm_llm_alignment/scripts/aggregate_all_llm_llm_p_value_outputs.py` (new) |

- New paths:
  - `results/alignment_scores/relabelled_common_neighbours/dataset-{d}_model-{m1}-{s1}_model-{m2}-{s2}_{sim}-relabelled_common_neighbours.parquet` (all k)
  - `results/alignment_scores/dataset-…_model-…_model-…_{sim}-alignment_score_{k}NN_relabelled.parquet`
  - `results/alignment_scores/dataset-…_model-…_model-…_hypergeometric_{sim}-alignment_score_{k}NN.p_value.tsv`
  - `results/all_model_model_alignment_scores.tsv`
- **Changed schema, same path:** `…_empirical_{sim}-alignment_score_{k}NN.p_value.tsv`
  used to be one model-level row (`number_at_least_as_extreme`,
  `empirical_p_value`, `number_of_parameters_1/2`, …). It is now the per-concept
  table written by `compute_empirical_p_value.py`, as on the LLM-brain side.
  The model-level values now live in the aggregated TSV.
- The relabelling uses the three `llm_mind_alignment/` per-k scripts unchanged,
  because they do not depend on what the two sides are. They run in
  `envs/llm_llm_alignment_environment.yaml`, which has numpy, pandas, pyarrow
  and scipy.
- `all_llm_llm_alignment` and the top-level `all` now request the relabelled
  per-k files, both p-value types and the new TSV.

## Null model

- One job per (dataset, pair, similarity) covers every configured k, with one
  shared permutation per shuffle, as on the LLM-brain side.
- Top-k for **both** models is recomputed on the shared concepts, in
  model_1's concept order. model_1 stays fixed and model_2 is relabelled, as
  the brain stays fixed and the LLM is relabelled in the LLM-brain case. The
  RNG, seed, concept order and relabelled side are the same as in the removed
  `compute_llm_llm_empirical_p_value.py`, so the model-level counts match the
  old results (see Verification).
- The model-level p-value is now computed like the LLM-brain one: the observed
  mean over concepts is compared with the per-shuffle means of the relabelled
  per-concept scores (`compute_model_level_empirical_p_value()`).

## Shared libraries

- `workflow/libraries/compute_relabelled_alignment.py` (new):
  `compute_topk_on_concept_subset()`, `select_common_neighbour_dtype()`,
  `compute_relabelled_common_neighbours_for_all_k(fixed_neighbours_at_max_k,
  relabelled_neighbours_at_max_k, …)` (the shuffle loop) and
  `create_relabelled_alignment_dataframe()`. These were moved out of the
  LLM-brain relabel script, which now calls them.
- `workflow/libraries/aggregate_alignment_scores.py` (new): the readers,
  validators, `aggregate_model_results()`, `reshape_summary()` and a driver,
  `aggregate_all_p_value_outputs()`, all moved from
  `aggregate_all_p_value_outputs.py`. They now take a `metadata` dict instead
  of fixed `dataset/model/stimuli_type/...` arguments. `key_columns` pairs up
  the files and `metadata_columns` sets the output column and sort order.
  Error messages now describe a result as `name=value, …` from that dict.
- `llm_mind_alignment/scripts/aggregate_all_p_value_outputs.py` went from 546
  to 87 lines: it keeps its filename parsers and `main()`.

## Removed

- `workflow/llm_llm_alignment/scripts/compute_llm_llm_empirical_p_value.py`
  (model-level-only permutation test, one job per k). The new chain replaces
  it.

## Other consumers

- `plot_empirical_p_value_heatmap` (`workflow/visualisation/Snakefile`) now
  takes `results/all_model_model_alignment_scores.tsv` as
  `llm_llm_empirical_p_values`, instead of 11,184 per-pair files.
- `read_llm_llm_records()` in `plot_empirical_p_value_heatmap.py` now filters
  the TSV like `read_llm_brain_records()` does (dataset, similarity, k,
  `statistic == model_level_empirical_p_value`). The old check of the files'
  `number_of_parameters_1/2` against the config was dropped, because the TSV
  does not carry parameter counts. The model must still be in
  `--model_parameters`. The heatmap still applies BH across its own LLM-LLM
  and LLM-brain cells; that behaviour is unchanged.

## Rerun behaviour and cost

- Dry run (`snakemake -n --quiet rules`): no missing inputs, no ambiguous rules.
  It shows 4,038 relabel jobs and 11,184 jobs each for extract, empirical and
  hypergeometric, plus one `aggregate_all_llm_llm_p_value_outputs`.
- Before this change the whole DAG was already scheduled to rerun, because of
  earlier conda-env changes, so the dry run cannot isolate this change's effect.
- **Disk:** one all-k file per (pair, similarity) is about 217 MB for
  caption_scene and nsd_data (1,000 concepts × 10,000 shuffles × 4 k), and
  its per-k slices take about the same again. Estimated total about 1.1 TB
  (caption_scene about 0.94 TB, nsd_data about 0.12 TB, narratives and
  nature_stories a few MB). `/home` had 2.7 TB free (94% used) on 2026-09-30.
  To save space, the per-k slices could be marked `temp()`; this was not done.
- **CPU:** one caption_scene relabel job took about 37 s on the frontend, so
  roughly 22 core-hours for caption_scene plus about 3 for nsd_data. The
  extract, empirical and hypergeometric jobs come on top.

## Verification

- **LLM-brain refactor:**
  - The old and new relabel scripts wrote identical DataFrames
    (`pd.testing.assert_frame_equal`) for caption_scene / bloom_1b1 / cosine,
    k = 5, 25, 50, 100, 30 shuffles, seed 37.
  - The old `aggregate_all_p_value_outputs.py`, run on the current 768 inputs,
    reproduces `results/all_alignment_scores.tsv` byte for byte (md5
    `2e3612c943676b3a3996c3d09ad79b86`).
  - The old and new versions give byte-identical output (`cmp`) on a
    168-configuration subset covering all four datasets: all of narratives
    and nature_stories, plus caption_scene/bloom_1b1 and nsd_data/clip_b.
  - The new version, run on all 768 inputs, reproduces
    `results/all_alignment_scores.tsv` byte for byte (`cmp`, same md5
    `2e3612c943676b3a3996c3d09ad79b86`; about 18 minutes on the frontend).
- **LLM-LLM chain, end to end:** 5 real pairs with 10,000 shuffles each gave
  11 configurations. They cover narratives (cosine, pearson), nature_stories
  (k=3), caption_scene language-vision (cosine, 4 k) and vision-vision
  (spearman, 4 k). All output went to the session scratchpad. Results:
  - no duplicate `(metadata…, statistic)` keys;
  - no pair in both orders;
  - `model_level_empirical_p_value == (1 + count) / (1 + number_of_relabellings)`
    for every configuration;
  - 17 statistics per configuration;
  - `model_level_number_of_null_scores_at_least_as_large`, the observed mean and
    `number_of_concepts` match the old per-pair files for all 11
    configurations.
- Not run: the full pipeline. No file in `results/` was written.

## Follow-ups (not done)

- `compute_model_level_empirical_p_value()` calls `groupby("shuffle_id")` on a
  categorical without `observed=`, which gives a pandas FutureWarning. This is
  pre-existing and gives the same result with either setting, because every
  shuffle is present.
- `compute_hypergeometric_p_value.py` writes `%.6f`, so p-values below 5e-7
  appear as `0.000000`, for example `min_hypergeom_p_value_across_concepts = 0`.
  This now affects the LLM-LLM files too. The format was left unchanged, as
  agreed.

---
*AI disclosure: this entry, the code change it describes and the related README
edits were written by an AI coding assistant.*

- *Tool: Claude Code (Anthropic), VS Code extension, on the lab server.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Date: 2026-09-30.*
- *Basis: the developer (Jonas Salvalaggio) asked for an aggregated model-model
  summary table, then asked that the LLM-LLM workflow mirror the LLM-brain one
  as closely as possible, with duplicated functions moved to shared libraries.
  They chose the column order.*
- *Files changed: `workflow/Snakefile`, `workflow/llm_llm_alignment/Snakefile`,
  `workflow/visualisation/Snakefile`,
  `workflow/visualisation/scripts/plot_empirical_p_value_heatmap.py`,
  `workflow/llm_mind_alignment/scripts/aggregate_all_p_value_outputs.py`,
  `workflow/llm_mind_alignment/scripts/relabel_llm_similarity_and_compute_relabelled_llm_alignment_score.py`,
  `README.md`. New: the two libraries and two LLM-LLM scripts named above.
  Deleted: `compute_llm_llm_empirical_p_value.py`.*
- *Verification: limited to the checks listed under "Verification".*
- *Review status: not yet reviewed by the developer at the time of writing.*

*The user changelog entry of the same name gives a plain-language summary.*
