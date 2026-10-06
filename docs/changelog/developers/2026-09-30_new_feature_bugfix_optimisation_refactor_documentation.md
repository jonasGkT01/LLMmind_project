# 2026-09-30 — developer changelog

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../../AI_USAGE.md).*

Changes made on this day, in order:

- LLM-LLM statistics mirror LLM-brain; new `all_model_model_alignment_scores.tsv` (new_feature)
- Compact relabelled null files; per-k `_relabelled.parquet` layer removed (optimisation)
- `all_alignment_scores.tsv` renamed to `all_model_brain_alignment_scores.tsv` (refactor)
- P-value TSV precision, ISC manifest index, model-embeddings reference page (bugfix, documentation)

---

## LLM-LLM statistics mirror LLM-brain; new `all_model_model_alignment_scores.tsv`

Kind: `new_feature`

### Summary

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

### Output schema

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

### Rules (`workflow/llm_llm_alignment/Snakefile`)

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

### Null model

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

### Shared libraries

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

### Removed

- `workflow/llm_llm_alignment/scripts/compute_llm_llm_empirical_p_value.py`
  (model-level-only permutation test, one job per k). The new chain replaces
  it.

### Other consumers

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

### Rerun behaviour and cost

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

### Verification

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

### Follow-ups (not done)

- `compute_model_level_empirical_p_value()` calls `groupby("shuffle_id")` on a
  categorical without `observed=`, which gives a pandas FutureWarning. This is
  pre-existing and gives the same result with either setting, because every
  shuffle is present.
- `compute_hypergeometric_p_value.py` writes `%.6f`, so p-values below 5e-7
  appear as `0.000000`, for example `min_hypergeom_p_value_across_concepts = 0`.
  This now affects the LLM-LLM files too. The format was left unchanged, as
  agreed.

### Context

- Basis: the developer (Jonas Salvalaggio) asked for an aggregated model-model summary table, then asked that the LLM-LLM workflow mirror the LLM-brain one as closely as possible, with duplicated functions moved to shared libraries. They chose the column order.
- Files changed: `workflow/Snakefile`, `workflow/llm_llm_alignment/Snakefile`, `workflow/visualisation/Snakefile`, `workflow/visualisation/scripts/plot_empirical_p_value_heatmap.py`, `workflow/llm_mind_alignment/scripts/aggregate_all_p_value_outputs.py`, `workflow/llm_mind_alignment/scripts/relabel_llm_similarity_and_compute_relabelled_llm_alignment_score.py`, `README.md`. New: the two libraries and two LLM-LLM scripts named above. Deleted: `compute_llm_llm_empirical_p_value.py`.
- Verification: limited to the checks listed under "Verification".

---

## Compact relabelled null files; per-k `_relabelled.parquet` layer removed

Kind: `optimisation`

### Summary

- The all-k relabelled files
  (`results/alignment_scores/relabelled_common_neighbours/*-relabelled_common_neighbours.parquet`)
  now store only `shuffle_id`, `model`, `concept`, `number_of_neighbours` and
  `common_neighbours`, with no pandas index. On the existing 300 LLM-brain files,
  the size per file dropped from ~216 MB to ~23 MB.
- The per-k copies `*-alignment_score_{k}NN_relabelled.parquet` and the rules that
  produced them no longer exist. Consumers read the k they need straight from the
  all-k file.
- Disk usage of `results/alignment_scores/` went from ~71 GB to ~4 GB. For
  the LLM-LLM pairs, whose relabelling has not run yet, the expected size is
  ~0.1× what the old format would have needed (on the order of 1 TB).
- All statistics are unchanged (see Verification).

### Why

The space in a representative old all-k file (216 MB, 40 M rows) split as follows:

- `__index_level_0__`: 163 MB. It came from `to_parquet(..., index=True)` on a
  RangeIndex and was never read.
- `alignment_score` and `alignment_score_percentage` (float64): 30 MB, even
  though both are exactly `common_neighbours / k` (×100).
- The rest (~23 MB) is the real information.

The per-k files then repeated all of these rows once more.

### Changes

#### Libraries

- `libraries/compute_relabelled_alignment.py`
  - `create_relabelled_alignment_dataframe()` no longer writes `alignment_score` or
    `alignment_score_percentage`.
  - New: `write_relabelled_common_neighbours(results_by_k, numbers_of_neighbours, output_path)`
    concatenates the per-k frames and writes one parquet with `index=False`. Both
    relabelling scripts use it.
- `libraries/compute_alignment.py`
  - New: `read_relabelled_alignment_scores(path, number_of_neighbours)` reads
    `shuffle_id`, `concept` and `common_neighbours` for one k, using a pyarrow row
    filter on `number_of_neighbours`, and adds
    `alignment_score = common_neighbours / k` as float64. That is exactly the value
    the old writer stored. It lives here and not in `compute_relabelled_alignment.py`
    because the visualisation environment has no SciPy, and
    `compute_relabelled_alignment` imports `compute_similarity`, which needs SciPy.
- `libraries/aggregate_alignment_scores.py`
  - `aggregate_all_p_value_outputs()` takes `relabelled_common_neighbours` and
    `parse_relabelled_common_neighbours_path` in place of the per-k arguments.
    All-k files are keyed by the result key without `number_of_neighbours`, and
    each result reads its k from the matching file.
  - `read_relabelled_alignment_scores()` became `read_unique_relabelled_alignment_scores(path, k)`:
    it calls the shared reader, then keeps the duplicate shuffle/concept check.
- `libraries/compute_alignment_enrichment.py`
  - `observed_path_for_relabelled_path()` was replaced by
    `relabelled_name_for_observed_path(observed_path, k)`, which maps
    `…-alignment_score_{k}NN.parquet` to `…-relabelled_common_neighbours.parquet`.
    `RELABELLED_SUFFIX` is now `-relabelled_common_neighbours.parquet`.
  - Relabelled scores are read with `read_relabelled_alignment_scores()`.

#### Scripts

- `llm_mind_alignment/scripts/compute_empirical_p_value.py`:
  `--relabelled_alignment_score` became `--relabelled_common_neighbours` plus
  `--number_of_neighbours`. The unused `numpy` import was removed.
- Both `aggregate_all*_p_value_outputs.py` scripts:
  `--relabelled_alignment_scores` became `--relabelled_common_neighbours` (the all-k
  files), and `parse_relabelled_alignment_score_path()` became
  `parse_relabelled_common_neighbours_path()`.
- Both `relabel_llm_similarity_and_compute_relabelled_*_alignment_score.py`
  scripts: they now call `write_relabelled_common_neighbours()`. The unused
  `pathlib` import was removed. **Their command line is unchanged.**
- `compute_llm_mind_alignment_score.py` and `compute_llm_llm_alignment_score.py`
  now write with `index=False`. This affects new files only; nothing read the index.
- Deleted: `llm_mind_alignment/scripts/extract_relabelled_alignment_score_for_k.py`.
- The enrichment plot scripts: only their help text changed.

#### Snakefiles

- Deleted the rules `extract_relabelled_alignment_score_for_k` and
  `extract_llm_llm_relabelled_alignment_score_for_k`, and the per-k
  `_relabelled.parquet` targets in `rule all`, `all_llm_mind_alignment` and
  `all_llm_llm_alignment`.
- `compute_empirical_p_value` and `compute_llm_llm_empirical_p_value`: the input is
  now the all-k file, and a new param `number_of_neighbours` is passed.
- `aggregate_all_p_value_outputs` and `aggregate_all_llm_llm_p_value_outputs`: the
  input `relabelled_common_neighbours` is a de-duplicated list of all-k files
  (`list(dict.fromkeys(...))`).
- Both enrichment plot rules take the all-k files.
- **The relabelling rules were deliberately left unchanged** (shell command and
  params). Snakemake's provenance triggers compare the shell command, not the
  script contents, so the 300 existing relabelling jobs do not rerun. For the same
  reason, the constant `model` column is still written (0.1 MB per file).

### Effect on reruns

A dry run of `results/all_alignment_scores.tsv` with
`--rerun-triggers mtime code params input` schedules only the 768
`compute_empirical_p_value` jobs and `aggregate_all_p_value_outputs`. These are
cheap, and their outputs are identical. Without that option, Snakemake still wants to
rerun the whole pipeline, but that comes from earlier environment-file changes
("software environment definition has changed", e.g. `download_pretrained_llm`), not
from this change.

### Migration of existing results

- A one-off script (in the session scratchpad, not in the repository) rewrote each
  of the 300 all-k files. Before replacing each file, it checked every k of the
  compact file, read through `read_relabelled_alignment_scores()`, against the old
  per-k file: shuffle IDs, concepts, `common_neighbours` and `alignment_score` all
  matched exactly. The original modification times were kept.
- The 768 per-k files (35.6 GB) were then deleted.

### Verification

- For one configuration (caption_scene, bloom_1b1, cosine, k=25), the new
  `compute_empirical_p_value.py` output is byte-identical to the existing TSV.
- `compute_alignment_enrichment()` (the HEAD version on the per-k files, against
  the new version on the compact all-k file) returns exactly equal concept-level and
  model-level frames for caption_scene/bloom_1b1/cosine at k = 5, 25, 50 and 100.
  This check ran in the visualisation environment, which also confirms the import
  chain works without SciPy.
- The new aggregation over all Narratives and all Nature Stories configurations
  (1224 rows each) is byte-identical to the corresponding rows of
  `results/all_alignment_scores.tsv`.
- The new pair-name parser was checked on synthetic filenames. The LLM-LLM
  relabelling has not run yet, so no real pair file exists.

### Context

- Basis: the developer (Jonas Salvalaggio) reported low disk space and asked for unneeded outputs to be found. This change implements TODO entry S23 (`LLMmind/.claude/TODO/LLMmind_project.md`) at their request.
- Files changed: `workflow/Snakefile`, `workflow/llm_mind_alignment/Snakefile`, `workflow/llm_llm_alignment/Snakefile`, `workflow/visualisation/Snakefile`, `workflow/libraries/{aggregate_alignment_scores,compute_alignment,compute_alignment_enrichment,compute_relabelled_alignment}.py`, both `aggregate_all*_p_value_outputs.py`, both `relabel_*` scripts, `compute_empirical_p_value.py`, `compute_llm_mind_alignment_score.py`, `compute_llm_llm_alignment_score.py`, the two enrichment plot scripts and `README.md`. Deleted: `extract_relabelled_alignment_score_for_k.py`.

---

## `all_alignment_scores.tsv` renamed to `all_model_brain_alignment_scores.tsv`

Kind: `refactor`

### Change

- The brain-model summary table is now `results/all_model_brain_alignment_scores.tsv`, so
  its name pairs with `results/all_model_model_alignment_scores.tsv`. The content and
  format are unchanged.
- `workflow/llm_mind_alignment/scripts/aggregate_all_p_value_outputs.py`: the option
  `--all_alignment_scores_tsv` is now `--all_model_brain_alignment_scores_tsv`, matching
  `--all_model_model_alignment_scores_tsv` in the LLM-LLM script.
- Updated the path in: `workflow/Snakefile` (`rule all`),
  `workflow/llm_mind_alignment/Snakefile` (`all_llm_mind_alignment` and the output
  `all_model_brain_alignment_scores_tsv` of `aggregate_all_p_value_outputs`),
  `workflow/visualisation/Snakefile` (the inputs of the five plot rules that read the
  model-level p-values), and a comment in `workflow/libraries/compute_statistics.py`.
- `README.md`: the example target and "Outputs".
- The existing file was moved with `mv`, so its modification time is unchanged.
  `all_spearman_alignment_scores.tsv` keeps its name.

### Effect on reruns

The aggregation rule's shell command and output path changed, and so did the input path of
the plot rules. Snakemake will therefore rerun `aggregate_all_p_value_outputs` (already due
after S23) and the plot rules that read the table. Both are light and give the same numbers.
Older changelog entries keep the old name, because they describe the state at their date.

### Context

- Basis: the developer (Jonas Salvalaggio) asked for the rename. They wrote the singular `…_alignment_score.tsv`; the plural was used to match `all_model_model_alignment_scores.tsv`.
- Verification: a search confirmed that no reference to the old name remains outside the historical changelog entries. No Snakemake dry run was made, because every dry run rewrites the Narratives QC files (TODO P28).

---

## 20:06 — P-value TSV precision, ISC manifest index, model-embeddings reference page

Kind: `bugfix`, `documentation`

### Changes

- **P-value TSVs keep 6 significant digits instead of 6 decimals.** `float_format` changed from
  `"%.6f"` to `"%.6g"` in:
  - `workflow/llm_mind_alignment/scripts/compute_empirical_p_value.py` (LLM-brain and LLM-LLM
    empirical p-value files);
  - `workflow/llm_mind_alignment/scripts/compute_hypergeometric_p_value.py` (LLM-brain and
    LLM-LLM hypergeometric p-value files);
  - `workflow/spearman_alignment/scripts/compute_spearman_alignment_with_empirical_p_value.py`
    (model- and concept-level Spearman TSVs).

  With `%.6f`, a hypergeometric p-value below 5e-7 was written as `0.000000`, and values below
  0.001 kept only 1–3 significant digits. As of 2026-09-30, no stored value was 0 (the smallest
  was 3e-6), but 630 hypergeometric p-values were below 0.001. With `%.6g`, small values are
  written in scientific notation (e.g. `3.12e-06`), which `pandas.read_csv` parses unchanged.
  Every float column of these files is affected. Values ≥ 0.1 are written with the same digits
  as before (e.g. `0.708333`, `0.333333`); values in [0.001, 0.1) gain up to two digits; and
  trailing zeros are dropped (`0.04` instead of `0.040000`).
- **`workflow/isc_nearest_neighbours/scripts/create_isc_manifest.py`** writes
  `results/mind/{dataset}/manifests/isc_inputs.tsv` with `index = False`. The unnamed leading
  index column is gone. Its only reader, `isc_npys_from_manifest()` in
  `workflow/isc_nearest_neighbours/Snakefile`, reads the `isc_file` column by name.
- **`workflow/isc_nearest_neighbours/scripts/create_isc_dataframe.py`**: `load_isc_value()`
  calls `np.load()` without `allow_pickle=True`. The ISC files are plain float arrays, so
  pickle loading was never needed.
- **New reference page `docs/reference/model_embeddings.md`**: how `get_embeddings.py` builds
  each stimulus vector, including that the mean pooling of language models includes the BOS
  token that is prepended to every chunk, and that vision models use the CLS token after the
  final norm, without the CLIP projection or classification heads. Linked from `README.md`
  ("Documentation").

### Effect on reruns

No shell command changed, so Snakemake reruns nothing by itself. Existing files keep their old
format until they are regenerated: the p-value files at the next full recomputation (TODO S22),
and `isc_inputs.tsv` when the checkpoint `create_isc_manifest` next runs. Tested on
Nature Stories, with outputs written to a scratch directory:

- both p-value scripts give the same values as before, in the new format;
- the ISC dataframe is identical to the existing one;
- the manifest has the columns `dataset`, `task`, `isc_file` and no index.

Once the p-value files are regenerated, the summary statistics that
`libraries/aggregate_alignment_scores.py` reads from them can change in their last digits
(`observed_average_*`, `empirical_null_mean_*` and the `*_p_value_across_concepts`
statistics), because they are then computed from more precise values.

### Context

- Basis: a project review requested by the developer; the developer approved these fixes (review items 1 and 4) and asked for the embeddings page (item 2).
