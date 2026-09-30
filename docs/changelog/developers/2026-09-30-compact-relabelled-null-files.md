# 2026-09-30 — Compact relabelled null files; per-k `_relabelled.parquet` layer removed

## Summary

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

## Why

The space in a representative old all-k file (216 MB, 40 M rows) split as follows:

- `__index_level_0__`: 163 MB. It came from `to_parquet(..., index=True)` on a
  RangeIndex and was never read.
- `alignment_score` and `alignment_score_percentage` (float64): 30 MB, even
  though both are exactly `common_neighbours / k` (×100).
- The rest (~23 MB) is the real information.

The per-k files then repeated all of these rows once more.

## Changes

### Libraries

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

### Scripts

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

### Snakefiles

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

## Effect on reruns

A dry run of `results/all_alignment_scores.tsv` with
`--rerun-triggers mtime code params input` schedules only the 768
`compute_empirical_p_value` jobs and `aggregate_all_p_value_outputs`. These are
cheap, and their outputs are identical. Without that option, Snakemake still wants to
rerun the whole pipeline, but that comes from earlier environment-file changes
("software environment definition has changed", e.g. `download_pretrained_llm`), not
from this change.

## Migration of existing results

- A one-off script (in the session scratchpad, not in the repository) rewrote each
  of the 300 all-k files. Before replacing each file, it checked every k of the
  compact file, read through `read_relabelled_alignment_scores()`, against the old
  per-k file: shuffle IDs, concepts, `common_neighbours` and `alignment_score` all
  matched exactly. The original modification times were kept.
- The 768 per-k files (35.6 GB) were then deleted.

## Verification

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

---

*This entry and the corresponding code edits were written by an AI coding assistant.*

- *Tool: Claude Code (Anthropic), VS Code extension, on the lab server.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Date: 2026-09-30.*
- *Basis: the developer (Jonas Salvalaggio) reported low disk space and asked for
  unneeded outputs to be found. This change implements TODO entry S23
  (`LLMmind/.claude/TODO/LLMmind_project.md`) at their request.*
- *Files changed: `workflow/Snakefile`, `workflow/llm_mind_alignment/Snakefile`,
  `workflow/llm_llm_alignment/Snakefile`, `workflow/visualisation/Snakefile`,
  `workflow/libraries/{aggregate_alignment_scores,compute_alignment,compute_alignment_enrichment,compute_relabelled_alignment}.py`,
  both `aggregate_all*_p_value_outputs.py`, both `relabel_*` scripts,
  `compute_empirical_p_value.py`, `compute_llm_mind_alignment_score.py`,
  `compute_llm_llm_alignment_score.py`, the two enrichment plot scripts and
  `README.md`. Deleted: `extract_relabelled_alignment_score_for_k.py`.*
- *Review status: not yet reviewed by the developer at the time of writing.*

*The user changelog entry of the same name gives a plain-language summary.*
