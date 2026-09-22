# 2026-09-22 — Stop writing dense N×N similarity matrices; compute-once max-k neighbours instead

## Summary

The previous entry in this changelog
([`2026-09-22-nsd-scale-similarity-streaming-and-isc-speedup.md`](2026-09-22-nsd-scale-similarity-streaming-and-isc-speedup.md))
fixed the OOM crashes caused by loading `nsd_data`'s full similarity matrix
back into memory, but explicitly left the underlying disk problem open: each
model's cosine+Pearson matrix pair was (and, until this entry, still is) a
fixed ~87.6GB at `nsd_data` scale (N=66,216), regardless of embedding size,
because the matrix size depends only on the number of stimuli squared. With
14 vision models configured, a full sweep would consume roughly 1.15TB —
against a filesystem that was at 98% capacity with ~1.2TB free at the start
of this session. One model (`dinov2_s`) had already produced its matrix
pair at 41GB each.

Separately, a repetition constraint removed from `nsd_data`'s ISC
processing in commit `817a212` (2026-09-21,
[`2026-09-21-nsd-observation-level-isc.md`](2026-09-21-nsd-observation-level-isc.md))
means the ISC/brain-eligible stimulus count for this dataset is no longer a
small, cheap subset (previously capped at 515 by a now-removed
all-subjects-≥3-repetitions rule) — it now uses the same ≥2-pooled-
observations rule as every other dataset, so it's expected to end up close
to the model side's full stimulus count once the ISC pipeline is re-run at
scale (not yet done — `results/mind/nsd_data/manifests/isc_inputs.tsv`
still only lists 516 of the manifest's 66,216 retained stimuli).
`compute_isc_similarity.py` used the identical one-shot dense-matrix
approach as the LLM side, so it was about to hit the same wall.

This entry removes the dense matrix from the pipeline entirely — it is
never computed or written, not merely avoided on the read side. Similarity
is computed in row-blocks directly from embeddings and immediately reduced
to each concept's top-`max(k)` neighbours (`k` = the largest
`number_of_neighbours` configured for that dataset), which is the only
thing any downstream consumer actually needed. Every smaller configured `k`
is a prefix slice of that one stored file at read time, so only one
neighbour file is kept per (dataset, model, stimuli_type, similarity_type)
on the LLM side, and per (dataset, similarity_type) on the mind/ISC side —
unversioned by `k` in the filename, so a future change to a dataset's
configured neighbourhood sizes doesn't leave stale, differently-sized files
sitting alongside the current one. This also merges relabelling's
previously-independent per-`k` Monte Carlo runs into one shared-permutation
pass per dataset.

## Design notes worth preserving

- **Relabelling cannot reuse a differently-scoped top-k file.** An earlier
  version of this change tried to have relabelling read the LLM side's
  global max-k-over-everything neighbour file and filter it down to the
  brain-eligible concept subset. This is wrong even where the two concept
  sets happen to coincide in membership: `relabel_nearest_neighbours`/
  `create_neighbour_mask` require neighbour values to be positional indices
  within the *same closed set being permuted* (0..n_concepts-1 over the
  brain-eligible subset only), and reconstructing that from a
  larger-universe file requires exactly as much filter-and-reindex work as
  computing it directly — with no correctness benefit and a dependency on
  an unverified assumption about the two concept sets matching. Fixed by
  having relabelling compute its own top-k directly from the model's
  embeddings restricted to the brain-eligible subset (same pattern
  Spearman already used). The LLM–LLM empirical p-value script has an
  analogous but genuinely different situation — two *different* models'
  concept universes only partially overlapping — where filtering a
  large-enough stored ranking down to the shared subset **is** exact (order
  among the shared members is preserved by filtering); that script computes
  fresh from embeddings anyway, since no matrix exists to filter from any
  more, but the same "filter is exact, given enough stored candidates"
  argument is why its `len(filtered) >= k` guard is sufficient rather than
  a correctness gap.
- **Snakemake `output:` cannot be a function of wildcards** (only `input:`
  can — hit as an actual `RuleException: Only input files can be specified
  as functions` against the project's own Snakemake,
  `workflow/envs/LLMmind_project/bin/snakemake`, 9.21.0; note this is a
  different, correct environment from an unrelated 8.11.3 binary found
  under another user's home directory during investigation, which should
  not have been used and wasn't for anything beyond an initial version
  check). This meant a single relabelling rule instance can't directly
  emit "one file per `k` in this dataset's list" the way a first draft of
  this change assumed. Fixed by splitting into two rules (see below): one
  computes every configured `k` together and writes a single combined
  file; a second, cheap rule slices out the specific `k` each existing
  downstream consumer already expects, so `compute_empirical_p_value`,
  `compute_hypergeometric_p_value`, and `aggregate_all_p_value_outputs`
  needed no changes at all.

## Changes

### `workflow/libraries/compute_nearest_neighbours.py`

- Added `compute_blockwise_topk_from_embeddings(embedding_matrix,
  number_of_neighbours, normalize_fn, row_block_size=4096)`: normalizes the
  full embedding matrix once, then for each row-block computes
  `block @ normalized.T`, masks self-similarity, and reduces to top-k via
  the same `argpartition`/`argsort` pattern the now-removed streaming
  readers used — but from embeddings, so the full N×N matrix is never
  materialized, on disk or in memory, at any point.
- Added `write_nearest_neighbours_parquet(concepts, neighbour_indices,
  neighbour_scores, number_of_neighbours, output_path)`: writes
  `concept`/`neighbour` as `pd.Categorical` (dictionary-encoded in
  Parquet, sharing one category list) instead of the old plain repeated
  strings, and stamps the realized `number_of_neighbours` as Parquet
  file-level metadata.
- Added `read_stored_number_of_neighbours(path)` /
  `require_stored_number_of_neighbours(path, requested_number_of_neighbours)`:
  the staleness safety net for unversioned-by-`k` filenames — every
  consumer asserts the stored file actually has at least the `k` it needs
  before slicing, raising a specific, actionable error otherwise (protects
  against a manual file copy or a `--rerun-triggers mtime`-only invocation
  bypassing Snakemake's normal `params`-change detection).
- Added `slice_top_k_neighbours(neighbours_df, number_of_neighbours)`:
  `groupby("concept").head(k)` — exact, not an approximation, because
  every writer here produces rank-sorted-descending rows per concept.
- Removed `stream_nearest_neighbours_from_parquet`,
  `stream_topk_indices_from_parquet`, `compute_topk_indices`,
  `create_nearest_neighbours_dataframe` — all read a persisted similarity
  matrix, which no longer exists anywhere in the pipeline. `json` import
  removed accordingly (no longer used).

### `workflow/libraries/compute_similarity.py`

- Added `extract_embedding_matrix(embedding_df)` (wide numeric-column
  embeddings, e.g. `{model}_embeddings.parquet`) and
  `dataframe_to_embedding_matrix(embedding_df)` (also accepts the ISC
  dataframe's single array-valued column shape) — consolidated from three
  near-identical local copies previously living in
  `compute_llm_nearest_neighbours.py`, the old `compute_isc_similarity.py`,
  and (implicitly) duplicated logic that would otherwise have been needed
  in the new relabelling/p-value/Spearman code.
- Added `normalize_fn_for_similarity_type(similarity_type)`: maps
  `"cosine"`/`"pearson"` to `normalize_l2`/`pearson_normalize`, used
  everywhere a script now needs to pick the right normalization from a
  `--similarity_type` CLI arg instead of reading an already-typed matrix.

### `workflow/libraries/read_similarity_subset.py` — deleted

Dead code: nothing reads a persisted similarity matrix to take a subset of
any more (introduced in the previous session's entry; superseded here).

### `workflow/llm_nearest_neighbours/scripts/compute_llm_similarity.py` — deleted

The full-matrix writer. Superseded by the rewritten
`compute_llm_nearest_neighbours.py` below.

### `workflow/llm_nearest_neighbours/scripts/compute_llm_nearest_neighbours.py`

Rewritten: takes `--embedding_dataframe` and one `--number_of_neighbours`
(the dataset's max configured `k`) and computes both `--cosine_nearest_neighbours`
and `--pearson_nearest_neighbours` in one call via
`compute_blockwise_topk_from_embeddings`, embeddings loaded once. Replaces
both the old `compute_llm_similarity.py` and the old per-`k`
`compute_llm_nearest_neighbours.py` in one script.

### `workflow/isc_nearest_neighbours/scripts/compute_isc_similarity.py` — deleted

Same role as `compute_llm_similarity.py`, mind side. Deleted for the same
reason.

### `workflow/isc_nearest_neighbours/scripts/compute_isc_nearest_neighbours.py`

Rewritten analogously to the LLM-side script: takes `--isc_dataframe` +
`--number_of_neighbours`, uses `dataframe_to_embedding_matrix` to handle
the ISC dataframe's array-column shape, writes both similarity types via
`compute_blockwise_topk_from_embeddings`.

### `workflow/llm_mind_alignment/scripts/compute_llm_mind_alignment_score.py`

Added `require_stored_number_of_neighbours` + `slice_top_k_neighbours` on
both inputs before calling the unchanged `compute_alignment_scores` — both
input files now hold the dataset's max `k`, not exactly the `k` this job
needs.

### `workflow/llm_llm_alignment/scripts/compute_llm_llm_alignment_score.py`

Same addition (`require_stored_number_of_neighbours` +
`slice_top_k_neighbours` in `read_nearest_neighbours`) — this consumer of
the LLM-side neighbour file was easy to miss since it wasn't part of the
originally-scoped consumer list, but has the identical "file now holds
more neighbours than this job's `k`" issue; caught during implementation,
not design.

### `workflow/llm_llm_alignment/scripts/compute_llm_llm_empirical_p_value.py`

Rewritten: `select_shared_concepts` now reads each model's *embeddings*
file's index (`read_embedding_concepts`, a single-column Parquet read) via
`--llm_embeddings_1`/`--llm_embeddings_2` instead of a similarity matrix's
column names. `compute_shared_subset_topk_indices` restricts each model's
embeddings to the shared-concept subset and calls
`compute_blockwise_topk_from_embeddings` directly — replaces
`stream_topk_indices_from_parquet`. New required `--similarity_type` arg
(previously implicit in which matrix file was passed) selects the
normalize function via `normalize_fn_for_similarity_type`.

### `workflow/llm_mind_alignment/scripts/relabel_llm_similarity_and_compute_relabelled_llm_alignment_score.py`

Rewritten:

- Takes `--embedding_dataframe` + `--similarity_type` instead of
  `--llm_similarity`; `concepts` (the brain-eligible subset, same source as
  before — `brain_nearest_neighbours_df["concept"].unique()`) is used to
  restrict the embeddings (`embedding_df.loc[concepts]`) before computing
  `observed_llm_neighbours` via `compute_blockwise_topk_from_embeddings` at
  `max(numbers_of_neighbours)`.
- `--number_of_neighbours` is now `nargs="+"` (a list, one per configured
  `k` for the dataset). `compute_relabelled_alignment_scores_for_all_k`
  loops `shuffle_i` once per relabelling (not once per `k` × relabelling as
  before — `create_relabelling_rng(random_seed, shuffle_i)` was already
  independent of `k`, so the separate per-`k` runs were already generating
  identical permutation sequences; this just stops recomputing them),
  relabels the max-`k` neighbour array once per shuffle, then for every
  configured `k` slices the first `k` columns and accumulates that `k`'s
  `common_neighbours` against that `k`'s own `brain_neighbour_mask` (masks
  built once per `k`, outside the shuffle loop, same as before — just now
  `len(numbers_of_neighbours)` masks coexist in one process instead of one
  per separate job; see "Not done" below).
- `create_relabelled_alignment_dataframe` gained a `number_of_neighbours`
  int column, and `main()` now writes **one** combined
  `--relabelled_common_neighbours` output (`pd.concat` across all
  configured `k`) instead of one file per `k` — see "Snakemake `output:`
  cannot be a function of wildcards" above.

### `workflow/llm_mind_alignment/scripts/extract_relabelled_alignment_score_for_k.py` (new)

Filters the combined `--relabelled_common_neighbours` file to one
`--number_of_neighbours` value, drops that column, and writes it out in
the exact schema (`shuffle_id`, `model`, `concept`, `common_neighbours`,
`alignment_score`, `alignment_score_percentage`) every existing downstream
consumer already expects.

### `workflow/spearman_alignment/scripts/compute_spearman_alignment_with_empirical_p_value.py`

Takes `--brain_embeddings`/`--model_embeddings` instead of
`--brain_similarity`/`--model_similarity`. `compute_similarity_dataframe`
computes the (always small — bounded by the brain-eligible concept count)
subset similarity matrix in-process via
`normalize_fn_for_similarity_type(args.similarity_type)` + a matmul,
equivalent to `cosine_similarity`/`pearson_similarity` from
`libraries/compute_similarity.py`. Ranking/relabelling/permutation logic
unchanged.

### Snakefiles

- `workflow/Snakefile`: added `dataset_numbers_of_neighbours(dataset)` /
  `max_number_of_neighbours(dataset)` helpers (the scalar/list
  normalization previously duplicated across `pairings()`,
  `llm_llm_pairings()`, and `HEATMAP_PAIRINGS` now goes through the first
  one); added `LLM_NEIGHBOUR_GENERATION_PAIRINGS` /
  `MIND_NEIGHBOUR_GENERATION_PAIRINGS` — deduplicated pairing lists (no
  `number_of_neighbours` dimension) that drive the two neighbour-generation
  rules, while `PAIRINGS` itself is unchanged and still drives every
  `k`-specific consumer rule.
- `workflow/llm_nearest_neighbours/Snakefile`: `compute_llm_similarity` +
  the old `compute_llm_nearest_neighbours` merged into one rule; output
  path drops the `{number_of_neighbours}` wildcard; `params:
  number_of_neighbours = lambda wc: max_number_of_neighbours(wc.dataset)`
  — this is also what makes Snakemake correctly invalidate the output when
  a dataset's configured neighbourhood sizes change, via the `params`
  rerun-trigger (part of Snakemake's default `rerun-triggers`, confirmed
  against the installed 9.21.0).
- `workflow/isc_nearest_neighbours/Snakefile`: same merge/wildcard-drop,
  mind side.
- `workflow/llm_mind_alignment/Snakefile`: `relabel_llm_similarity_and_compute_relabelled_llm_alignment_score`
  rule rewritten per above (single combined output); new
  `extract_relabelled_alignment_score_for_k` rule added.
- `workflow/llm_llm_alignment/Snakefile`: `compute_llm_llm_alignment_score`
  and `compute_llm_llm_empirical_p_value` rules' inputs point at the new
  unversioned neighbour files / embeddings instead of the deleted
  similarity matrices.
- `workflow/spearman_alignment/Snakefile`: rule input renamed to
  `brain_embeddings`/`model_embeddings`, pointing at `isc_dataframe.parquet`
  / `{model}_embeddings.parquet` instead of the deleted similarity
  matrices.

## Disk cleanup

With the user's explicit confirmation, the now-orphaned outputs of the
deleted rules were deleted from this machine's `results/`, measured before
deletion:

| Category | Size |
|---|---|
| Dense LLM similarity matrices (`{cosine,pearson}_similarity/` dirs, all datasets) | 116.4GB |
| Dense ISC similarity matrices (`isc_{cosine,pearson}_similarity.parquet`, all datasets) | 1.46GB |
| Old per-k LLM neighbour files (`*_nearest_neighbours_<k>NN.parquet`) | 10.5GB |
| Old per-k ISC neighbour files (`isc_*_nearest_neighbours_<k>NN.parquet`) | 0.44GB |
| **Total** | **~128.8GB** |

Confirmed via `df -h` before/after: 1.2TB → 1.3TB free on the `/home`
filesystem. Verified no new-style (unversioned-by-`k`) files existed yet
before deleting, so this was unambiguous — nothing current was at risk.

## Not done in this session

- No actual pipeline run against real model embeddings at `nsd_data`'s
  full scale with the new code path — verification (below) is synthetic/
  unit-level plus a full dry-run, not a production run like the previous
  session's entry. Real wall-clock/memory/output-size numbers for the new
  neighbour-generation scripts are not yet measured.
- `create_neighbour_mask` still builds a dense `n_concepts × n_concepts`
  boolean matrix; the merged relabelling script now holds one such mask
  per configured `k` simultaneously in one process (previously one mask
  per separate job/process). At `nsd_data`'s expected post-817a212 ISC
  scale (likely tens of thousands of concepts, not yet confirmed by an
  actual full ISC regeneration) this could be a meaningful peak-memory
  increase versus the old per-`k`-job structure; not addressed here.
- `nsd_data`'s ISC pipeline has not been re-run to completion at its new,
  much larger scale (`isc_inputs.tsv` still lists 516 of 66,216 manifest
  rows), so the "brain-eligible subset is now much larger" claim above is
  based on the manifest change, not yet confirmed by an end-to-end ISC run.

## Verification

- `compute_blockwise_topk_from_embeddings`: checked against a brute-force
  dense-matrix computation (`np.argsort` over the full similarity matrix)
  on synthetic random embeddings, for both cosine and Pearson, across
  block sizes smaller than, larger than, and exactly equal to N — exact
  index match, scores matching to `1e-10`.
- Merged multi-`k` relabelling: checked bit-for-bit against an independent
  reference implementation that computes each `k` separately (its own
  `compute_blockwise_topk_from_embeddings` call, its own relabelling loop)
  — identical `common_neighbours` matrices for every shuffle/concept at
  two different `k` values.
- Subset-restricted top-k (used by both relabelling and the LLM–LLM
  p-value script): checked against brute-force top-k computed strictly
  within a synthetic strict subset (22 of 60 concepts) — confirmed this
  differs in general from filtering a full-universe ranking down to the
  subset (the rejected design), and that the implementation used here
  matches the correct, subset-native ranking exactly. Also confirmed
  relabelling's result concept set equals the brain-eligible subset, not
  the full embedding universe, when the two differ.
- `write_nearest_neighbours_parquet` / `read_stored_number_of_neighbours` /
  `require_stored_number_of_neighbours` / `slice_top_k_neighbours`: round-
  tripped through actual Parquet I/O; confirmed the too-small-`k` case
  raises with the expected message; confirmed per-concept rows are rank-
  sorted descending (a precondition `slice_top_k_neighbours`'s `head(k)`
  relies on) and that slicing reproduces the correct prefix.
- `extract_relabelled_alignment_score_for_k.py`: run as an actual
  subprocess against a small synthetic combined file; confirmed it
  produces the correct sliced rows with the `number_of_neighbours` column
  dropped.
- Full-workflow dry run (`snakemake -n --cores 4`) against the real
  `config/config.yaml`, real project Snakemake
  (`workflow/envs/LLMmind_project/bin/snakemake`, 9.21.0): the complete
  9,889-job DAG across all four datasets builds with no wiring errors, no
  ambiguous rule matches, no missing inputs; job counts for every touched
  rule match expectations (e.g. `compute_llm_nearest_neighbours`: 58,
  matching `LLM_NEIGHBOUR_GENERATION_PAIRINGS`;
  `extract_relabelled_alignment_score_for_k`: 420, matching `PAIRINGS`).
- All touched/added Python files pass `python -m py_compile`.
- Disk reclamation confirmed via `df -h` before/after and an explicit
  post-deletion re-scan showing zero remaining files matching any of the
  four deleted-category patterns.

## Files touched

- `workflow/libraries/compute_nearest_neighbours.py`
- `workflow/libraries/compute_similarity.py`
- `workflow/libraries/read_similarity_subset.py` (deleted)
- `workflow/llm_nearest_neighbours/scripts/compute_llm_similarity.py` (deleted)
- `workflow/llm_nearest_neighbours/scripts/compute_llm_nearest_neighbours.py`
- `workflow/isc_nearest_neighbours/scripts/compute_isc_similarity.py` (deleted)
- `workflow/isc_nearest_neighbours/scripts/compute_isc_nearest_neighbours.py`
- `workflow/llm_mind_alignment/scripts/compute_llm_mind_alignment_score.py`
- `workflow/llm_mind_alignment/scripts/relabel_llm_similarity_and_compute_relabelled_llm_alignment_score.py`
- `workflow/llm_mind_alignment/scripts/extract_relabelled_alignment_score_for_k.py` (new)
- `workflow/llm_llm_alignment/scripts/compute_llm_llm_alignment_score.py`
- `workflow/llm_llm_alignment/scripts/compute_llm_llm_empirical_p_value.py`
- `workflow/spearman_alignment/scripts/compute_spearman_alignment_with_empirical_p_value.py`
- `workflow/Snakefile`
- `workflow/llm_nearest_neighbours/Snakefile`
- `workflow/isc_nearest_neighbours/Snakefile`
- `workflow/llm_mind_alignment/Snakefile`
- `workflow/llm_llm_alignment/Snakefile`
- `workflow/spearman_alignment/Snakefile`
- `results/` (data only, not tracked in git): ~128.8GB of stale dense-matrix
  and old per-k neighbour files deleted, see "Disk cleanup" above

---

*This changelog entry was drafted by an AI coding assistant (Claude Code,
model Claude Sonnet 5, `claude-sonnet-5`) based on the session's code
changes and the verification steps run during that session, and reviewed
by the developer before being committed.*
