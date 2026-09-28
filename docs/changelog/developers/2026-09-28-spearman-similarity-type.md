# 2026-09-28 — Spearman similarity type

## Summary

- Added `spearman` as a third similarity type, next to `cosine` and
  `pearson`. It is Pearson computed on the per-row ranks of the
  concepts × dimensions matrix.
- The two nearest-neighbour rules now write a third output. Every other
  step already looped over `config["similarity_types"]` or used
  `normalize_fn_for_similarity_type`, so none of them changed.

## Changes

- `libraries/compute_similarity.py`:
  - New `spearman_normalize(x)`: `rankdata(x, method="average", axis=1)`,
    then `pearson_normalize`. It raises on non-2D input, like
    `pearson_normalize`.
  - New `spearman_similarity(x)`, mirroring `cosine_similarity` and
    `pearson_similarity`.
  - Registered as `"spearman"` in `NORMALIZE_FUNCTIONS_BY_SIMILARITY_TYPE`.
  - The module now imports `scipy.stats.rankdata` at the top, so **every
    env that imports it needs scipy**. See "Environments" below.
- `config/config.yaml`: `- "spearman"` added to `similarity_types`.
- `llm_nearest_neighbours/`: `compute_llm_nearest_neighbours.py` has a new
  `--spearman_nearest_neighbours` argument and a `##### SPEARMAN
  SIMILARITY #####` block, a copy of the Pearson block. The rule
  `compute_llm_nearest_neighbours` has a new output,
  `results/{stimuli_type}_models/{dataset}/spearman_nearest_neighbours/{model}_spearman_nearest_neighbours.parquet`.
  The Pearson block now ends with `del pearson_indices, pearson_scores`,
  like the cosine block.
- `isc_nearest_neighbours/`: the same changes in
  `compute_isc_nearest_neighbours.py` (`--isc_spearman_nearest_neighbours`)
  and in the rule `compute_isc_nearest_neighbours` (output
  `results/mind/{dataset}/isc_spearman_nearest_neighbours.parquet`).
- `README.md`:
  - "cosine or Pearson" became "cosine, Pearson or Spearman" in the
    overview, `isc_nearest_neighbours/` and `llm_nearest_neighbours/`.
  - `spearman_alignment/` now says what that step computes when
    `similarity_type=spearman`.
  - "Running the pipeline": a one-line description of each
    `similarity_types` value, and a usage example that leaves out a
    metric for one run with
    `--config 'similarity_types=["cosine","pearson"]'`.
  - "Troubleshooting": a new entry on the rerun cascade after adding a
    metric.
  - "Outputs": per-configuration file names carry the metric; the summary
    tables have a `similarity_type` column.

## Environments

The envs that import `compute_similarity` are those of
`llm_nearest_neighbours`, `isc_nearest_neighbours`, `llm_llm_alignment`,
`llm_mind_alignment` and `spearman_alignment`. Visualisation imports only
`compute_alignment_enrichment`, which does not import it.

- `isc_nearest_neighbours_environment.yaml` and
  `llm_llm_alignment_environment.yaml`: `scipy` added.
- `llm_mind_alignment` and `spearman_alignment` already listed scipy.
- `llm_nearest_neighbours_environment.yaml` was **left unchanged on
  purpose**. scipy comes in through `scikit-learn`; it is present in the
  built `.snakemake/conda/` envs. `download_pretrained_llm` and
  `get_embeddings` share this env file, so editing it would trigger a
  software-env rerun of all model downloads and embedding jobs (GPU).
  List scipy explicitly the next time that env has to change anyway.

## Rerun behaviour

- `compute_llm_nearest_neighbours` (58 jobs) and
  `compute_isc_nearest_neighbours` (4 jobs) have a new output file, so
  they rerun for every model/dataset. They rewrite the cosine and Pearson
  files too, with identical content, and **every downstream cosine/Pearson
  job reruns as well, under either trigger setting**.
- `snakemake -n --cores 8 --rerun-triggers mtime`: 11,893 jobs, with no
  `get_embeddings` or `download_pretrained_llm`. The only Spearman-alignment
  jobs are the 58 new `similarity_type=spearman` ones; that step reads
  embeddings, not neighbour files, so its cosine/Pearson jobs are not
  affected.
- `snakemake -n --cores 8` (default triggers): about 12,100 jobs, against
  about 8,100 before this change. The ~8,100 come from provenance
  triggers that were there before this change (see the 2026-09-25 entry),
  and include 58 `get_embeddings` jobs that this change does not cause.
- For a run without Spearman, override the config:
  `--config 'similarity_types=["cosine","pearson"]'` with
  `--rerun-triggers mtime` plans nothing on the current `results/`. The
  nearest-neighbour jobs are not needed, because only their cosine and
  Pearson outputs are requested and those exist.
- To avoid the cosine/Pearson cascade, split each nearest-neighbour rule
  into one rule per similarity type (a `{similarity_type}` wildcard in the
  output). That is a larger change and was not made.
- The two env edits trigger a software-env rerun of
  `compute_isc_nearest_neighbours` (already rerunning, see above) and of
  every `llm_llm_alignment` job. Those jobs rerun anyway because of the
  cascade above.

## Verification

- `spearman_similarity` against `scipy.stats.spearmanr(x, axis=1)` on a
  50 × 30 matrix with 8 all-zero columns (ties) and one cubed row
  (monotone distortion): max abs difference 2.2e-16.
- `compute_blockwise_topk_from_embeddings(..., spearman_normalize,
  row_block_size=7)` returns the same top-5 scores as the dense
  `spearmanr` matrix with the diagonal masked.
- `snakemake -n --quiet rules --cores 8`: the DAG resolves, including the
  new `spearman` wildcard values across all downstream rules.
- `snakemake -n --quiet rules --cores 8 --rerun-triggers mtime --config
  'similarity_types=["cosine","pearson"]'`: "Nothing to be done".
- `results/all_alignment_scores.tsv` and
  `results/all_spearman_alignment_scores.tsv` both have a
  `similarity_type` column, as the README now states.
- Not run: no real Spearman outputs have been produced yet. No automated
  tests exist for these steps.

## Follow-ups

- `rankdata` allocates a second N × D float64 array while
  `spearman_normalize` runs. The largest embedding matrices (NSD) might
  need more `mem_mb` on `compute_llm_nearest_neighbours`. Check the first
  runs.
- A concept whose ISC vector is all zeros ranks as a constant and ends up
  as a zero vector, just as with Pearson.
- A useful diagnostic, not implemented: the overlap between the Pearson
  and Spearman neighbourhoods within the same space, to see whether
  Spearman changes the neighbour sets at all.

---
*AI disclosure: this changelog entry, together with the code changes it
describes and the related README edits, was written by an AI coding
assistant.*

- *Tool: Claude Code (Anthropic), VS Code extension, run inside the
  developer's workspace on the lab server.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Date: 2026-09-28.*
- *Basis: explicit instructions from the developer (Jonas Salvalaggio) in
  the same session. The developer first had the assistant review a
  written rationale for adding Spearman, then asked for Spearman as a
  similarity metric with the new code kept as close as possible to the
  existing code, and finally asked for this documentation. The assistant
  chose to copy the Pearson blocks rather than refactor them into a loop,
  to use average ranks for ties, and not to edit the
  `llm_nearest_neighbours` env.*
- *Verification: limited to the checks listed under "Verification". The
  assistant's first draft of this entry wrongly claimed that
  `--rerun-triggers mtime` would avoid the cosine/Pearson reruns; that was
  corrected after a dry-run.*
- *Temporary files: none were left in the workspace. The verification
  scripts ran from stdin, and the one `git stash` used for a before/after
  dry-run was popped.*
- *Review status: not yet reviewed by the developer at the time of writing.
  Review it before committing.*
