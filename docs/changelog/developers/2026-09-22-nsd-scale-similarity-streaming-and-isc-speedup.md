# 2026-09-22 — nsd_data at full scale: memory-safe similarity/nearest-neighbour computation, ISC vectorization

## Summary

`nsd_data`'s stimulus-eligibility threshold retains far more stimuli for
embedding/similarity purposes (~66,216) than for ISC/brain purposes (515,
capped by a stricter per-subject repetition requirement). Several scripts
implicitly assumed these two universes were the same size — true for every
other dataset, where `excluded_stimuli.txt` already trims the model side
down to exactly the ISC-eligible set, but false for `nsd_data`. As
`get_embeddings`/`compute_llm_similarity` outputs for `nsd_data` started
being regenerated at the new, full 66,216-stimulus scale this session, this
mismatch surfaced as a series of concrete failures:

- `compute_llm_nearest_neighbours.py` was OOM-killed (`SIGKILL`) computing
  top-k neighbours over a 66,216×66,216 (43.8GB Parquet) matrix — it made
  three full in-memory copies of the matrix (`pd.read_parquet`,
  `.to_numpy(copy=True)`, an internal `.copy()` for the diagonal fill),
  roughly 100+GB peak RSS for one job, with two such jobs running
  concurrently.
- `compute_spearman_alignment_with_empirical_p_value.py`,
  `relabel_llm_similarity_and_compute_relabelled_llm_alignment_score.py`,
  and `compute_llm_llm_empirical_p_value.py` all loaded the full model
  similarity matrix and then either crashed on a strict
  concept-set-equality check against the much smaller ISC/brain concept set
  (Spearman, relabel), or paid the same full-load cost even though the
  actual comparison plus permutation testing only ever needed
  ~500-concept-scale data (Spearman, relabel) or the shared subset between
  two matrices (llm_llm, which for `nsd_data` turned out to be capped by
  whichever side hadn't yet been regenerated to full scale).

Separately, `compute_nsd_isc`'s leave-one-out ISC (via
`fmri_processing.compute_leave_one_out_isc`) calls `scipy.stats.pearsonr`
once per `(subject, parcel)` pair in a Python double loop. Every other
dataset calls this a handful of times total; `nsd_data` calls it once per
stimulus across ~66k stimuli — tens of millions of individual `pearsonr`
calls, benchmarked at ~500x the cost of a vectorized equivalent.

This entry covers the fixes for all of the above, plus two smaller,
independently-motivated efficiency changes found during the same audit
(`get_embeddings.py`, `compute_llm_similarity.py`), a new (not yet wired in)
batch-size heuristic utility, and an unrelated operational fix to the
model-download permissions that was blocking a full pipeline launch.

## Changes

### `workflow/libraries/read_similarity_subset.py` (new)

- `read_similarity_subset(path, concepts, source)`: reads only the
  columns/rows needed for a given `concepts` list from a similarity
  Parquet file, via `pyarrow.parquet.read_table(columns=[...])` column
  projection, rather than loading the full square matrix. Raises a clear
  `ValueError` naming missing concepts (up to 5) instead of a bare
  `KeyError`/`ValueError` from a downstream equality check. Moved here
  from a local definition in `compute_spearman_alignment_with_empirical_p_value.py`
  (previously the only user) so `relabel_llm_similarity_and_compute_relabelled_llm_alignment_score.py`
  could reuse it.

### `workflow/libraries/compute_nearest_neighbours.py`

- `stream_nearest_neighbours_from_parquet(similarity_parquet_path,
  number_of_neighbours, column_block_size=4096)`: computes top-k nearest
  neighbours for every concept in a similarity Parquet file without ever
  materializing the full N×N matrix. Reads the file in blocks of
  `column_block_size` columns; by symmetry, a column-projected block for
  concepts already contains everything needed to rank those concepts'
  neighbours (a column equals the corresponding row). Self-similarity is
  masked to `-inf` before `argpartition`/`argsort`. Peak memory is
  `O(N × column_block_size)` instead of `O(N²)`. Used by
  `compute_llm_nearest_neighbours.py` (the script that was being
  OOM-killed).
- `stream_topk_indices_from_parquet(similarity_parquet_path, concepts,
  number_of_neighbours, column_block_size=4096)`: same streaming approach,
  but for a caller-supplied `concepts` list that need not be the file's
  full concept set or match its native column order (needed to compare two
  similarity matrices whose stimuli only partially overlap). Returns raw
  top-k index arrays (positions within `concepts`), matching what
  `compute_topk_indices` used to return, for drop-in use with
  `create_neighbour_mask`/`relabel_nearest_neighbours`.
- `compute_topk_indices`, `create_nearest_neighbours_dataframe`,
  `create_neighbour_mask`, `relabel_nearest_neighbours` are unchanged —
  still used at ISC scale (~515 concepts) by `isc_nearest_neighbours/`,
  `llm_llm_alignment/`, and `llm_mind_alignment/`'s internal permutation
  loops, where the full-matrix cost is small and not a risk.

### `workflow/llm_nearest_neighbours/scripts/compute_llm_nearest_neighbours.py`

- Replaced `pd.read_parquet(...)` + manual square/order validation +
  `create_nearest_neighbours_dataframe(...)` with a single call to
  `stream_nearest_neighbours_from_parquet(...)`. The square/order checks
  now happen cheaply against Parquet metadata inside the streaming
  function instead of after a full load.

### `workflow/spearman_alignment/scripts/compute_spearman_alignment_with_empirical_p_value.py`

- `concepts` is now taken from `brain_similarity_df.index` *before* the
  model similarity file is touched at all (previously both were loaded
  first, then checked for equality).
- Replaced `pd.read_parquet(args.model_similarity)` + a
  `set(concepts) != set(model_similarity_df.index)` equality check (which
  is false for `nsd_data` — 515 brain concepts vs. 66,216 model
  concepts — even though the 515 are a legitimate subset) with
  `read_similarity_subset(path=args.model_similarity, concepts=concepts,
  ...)`. The 66,216-column file is now read as a 515-column projection.
- Local `read_similarity_subset` definition removed in favour of the
  shared one in `libraries/read_similarity_subset.py`; `json` and
  `pyarrow.parquet` imports removed accordingly (no longer used directly
  in this file).
- No change to the ranking/relabelling/permutation logic itself.

### `workflow/llm_mind_alignment/scripts/relabel_llm_similarity_and_compute_relabelled_llm_alignment_score.py`

- `main()`: `concepts` is now `brain_nearest_neighbours_df["concept"].unique()`
  (the ISC-derived concept set) instead of being re-derived inside
  `compute_relabelled_alignment_scores` from the *model* similarity
  matrix's own (potentially much larger) index. The model similarity is
  read via `read_similarity_subset(path=args.llm_similarity,
  concepts=concepts, ...)` instead of `pd.read_parquet(args.llm_similarity)`.
- `compute_relabelled_alignment_scores(...)` itself is unchanged: it
  already re-derives and validates `concepts` from whatever
  `similarity_df` it's given, and already required (correctly) that every
  model concept have a matching brain-neighbour entry — that requirement
  was previously being checked against the wrong (much larger) concept
  set. With `concepts` now sourced from the brain side, this check is
  satisfied by construction for every dataset, including `nsd_data`.

### `workflow/llm_llm_alignment/scripts/compute_llm_llm_empirical_p_value.py`

- Added `read_parquet_concepts(path)`: returns a Parquet file's concept
  columns from schema metadata alone (no data read), raising if the file
  isn't square per its own row-count/column-count metadata.
- `select_shared_concepts` now takes the two file *paths* (not loaded
  DataFrames) and computes the shared concept list from schema alone.
- Replaced `pd.read_parquet` (both matrices) + `validate_similarity_dataframe`
  + `.to_numpy(copy=True)` + `compute_topk_indices` with
  `stream_topk_indices_from_parquet(similarity_parquet_path=...,
  concepts=shared_concepts, ...)` per matrix. Neither matrix is ever
  loaded in full; each is streamed independently and sequentially (one
  finishes and is discarded before the other starts), so peak memory is
  bounded by one streaming block, not by either matrix's full size — this
  matters because for `nsd_data` two models' matrices can each be
  43.8GB+, with no size reduction available from `select_shared_concepts`
  when both sides share the same (large) stimulus universe.
- `validate_similarity_dataframe` import removed (no longer used in this
  file); `compute_topk_indices` import replaced with
  `stream_topk_indices_from_parquet`.
- `number_of_shared_concepts` in the output now comes from
  `len(shared_concepts)` instead of `len(similarity_df_1)`.

### `workflow/libraries/fmri_processing.py`

- `compute_leave_one_out_isc(data)`: replaced the `for subject: for
  parcel: safe_pearsonr(...)` double loop (one `scipy.stats.pearsonr` call
  per parcel) with a single vectorized Pearson correlation per subject,
  computed across all parcels at once via centered sums
  (`(x_centered*y_centered).sum(axis=0)` etc.). The original's
  `np.allclose(x, x[0])` "is this vector constant" guard (which zeroes the
  correlation instead of dividing by ~0) is replicated exactly via
  `np.isclose` against each vector's first element, vectorized per
  parcel, followed by `np.nan_to_num` on the result — matching
  `safe_pearsonr`'s fallback behaviour column-wise instead of per-call.
  `safe_pearsonr` itself is unchanged and still used elsewhere (it's a
  small, general-purpose helper independent of this function; not
  removed).

### `workflow/llm_nearest_neighbours/scripts/get_embeddings.py`

- Replaced the per-stimulus accumulation pattern (one `dict` per
  stimulus, with one key per embedding dimension, appended to a `records`
  list, then a single `pd.DataFrame(records)` at the end) with three
  parallel lists (`stimuli`, `n_tokens_list`, `n_chunks_list`) plus an
  `embeddings` list of per-stimulus `float32` arrays, `np.stack`ed once
  into a single `(N, dim)` array after the loop, and the final DataFrame
  built via `pd.concat([metadata_df, pd.DataFrame(embedding_matrix,
  columns=range(dim))], axis=1)`. For a high-dimensional model over
  `nsd_data`'s ~66k stimuli, the previous approach built a ~66k-row list
  of wide dicts (one Python dict key per embedding dimension) before
  pandas could construct anything; this replaces it with array
  concatenation.
- The `unexpected_columns` validation step (previously needed because
  dict keys could in principle include anything) was removed as
  redundant: the new construction only ever produces the known metadata
  columns plus `range(dim)` integer columns, so there's nothing left to
  validate against.
- Per-item behavior (the embedding computation itself, per-item
  `torch.cuda.empty_cache()`, the per-item `print(...)`) is unchanged —
  this change is scoped to output *construction*, not the inference loop
  or its batching (see "Not done in this session" below).

### `workflow/llm_nearest_neighbours/scripts/compute_llm_similarity.py`

- Added `del cosine_result, cosine_similarity_df` immediately after the
  cosine similarity matrix is written to Parquet, before the Pearson
  similarity matrix is computed. Previously both the cosine result/frame
  and the embedding matrix were kept alive (via still-referenced local
  variables) while the Pearson matrix was computed the same way, so both
  full N×N matrices (43.8GB each at `nsd_data` scale) coexisted at peak.
  `compute_isc_similarity.py` has the identical structural pattern but was
  left as-is — harmless at ISC's ~515-concept scale.

### `workflow/libraries/estimate_batch_size.py` (new, not yet wired into any rule)

- `suggest_batch_size(parameters_millions, modality, sequence_length=None,
  quantization_method=None, available_vram_gb=24.0, min_batch_size=1,
  max_batch_size=256)`: heuristic starting `--batch_size` from model size
  (`batch_size ∝ 1/parameters`, calibrated so it reproduces
  ~64–256/32/8/8 for small/large/huge/giant vision models on a 24GB GPU),
  extended to language models by additionally scaling by
  `512/sequence_length` (longer chunks cost more activation memory per
  sample). Rounds down to a power of two. Added in response to an
  explicit preference for a parameter-count-derived heuristic over a
  hardcoded per-model table, so new models added to `config.yaml` get a
  sane default automatically. **Not called from any script or Snakemake
  rule yet** — `get_embeddings.py`'s inference loop is still
  single-item, unbatched (see "Not done in this session").

## Operational fix: model-download directories were not writable

Not a code change, but blocked a full pipeline launch and is worth
recording. `resources/models/{model}` is downloaded via
`huggingface_hub.snapshot_download(..., local_dir_use_symlinks=False)` in
`download_pretrained_llm.py`. This is **not** a Snakemake `protected()`
output (grepped: no `protected(` anywhere in any Snakefile) — `snapshot_download`
itself leaves the downloaded files (and, on this run, the containing
directories) read-only. Combined with Snakemake's own provenance tracking
flagging all 24 `download_pretrained_llm` outputs as needing a re-run
(`reason: Software environment definition has changed since last
execution` — `workflow/llm_nearest_neighbours/envs/llm_nearest_neighbours_environment.yaml`'s
recorded hash no longer matches what's on disk), a full `snakemake all`
would hit `ProtectedOutputException` on the very first
`download_pretrained_llm` job, before any of the fixes above are ever
exercised.

Fixed by `chmod -R u+w resources/models/` (confirmed: 0 remaining
non-writable files/directories under it afterward). This does not address
the underlying "software environment changed" provenance flag — a full
run will still attempt to re-run `download_pretrained_llm` for all 24
models unless launched with `--rerun-triggers mtime`, or the metadata is
cleared via `snakemake --cleanup-metadata`. Left as a decision for whoever
launches next, since it depends on whether the environment change
actually matters for these already-downloaded weights.

## Not done in this session

- `get_embeddings.py`'s inference loop is still single-item/unbatched.
  `estimate_batch_size.py` (above) exists but is not called anywhere.
  Batching the loop itself (a `Dataset`/`DataLoader`, `--batch_size`
  wiring, `num_workers`/`pin_memory`) was scoped out as a separate,
  larger change.
- `compute_llm_similarity.py` (and `compute_isc_similarity.py`) still
  compute and write the *full* dense N×N matrix — the fixes in this
  entry avoid loading that full matrix back into memory downstream, but
  don't avoid writing it in the first place. At `nsd_data` scale this is
  a real, currently binding disk-space constraint (each vision model's
  cosine+Pearson pair is a fixed ~87.6GB regardless of embedding
  dimension, since the matrix size depends only on N). Blockwise/on-disk
  (memmap/HDF5/Zarr) similarity computation was discussed but not
  implemented.
- `resources/datasets/nsd_data_dataset/stimuli/images` still stores one
  PNG per stimulus, decoded via PIL on every `get_embeddings.py` run,
  rather than reading directly from `nsd_stimuli.hdf5`.

## Verification

All of the following were run against real project data (not synthetic
fixtures) on this machine:

- `compute_llm_nearest_neighbours.py` / `stream_nearest_neighbours_from_parquet`:
  - Re-ran the exact job that was previously `SIGKILL`ed
    (`dinov2_s_pearson_similarity.parquet` → `5NN`, N=66,216, 43.8GB file):
    completed in 935s, peak RSS 16,184MB.
  - Regression check against the existing production output for
    `caption_scene`/`dinov2_s` (N=8,920, already-working scale before this
    change): `concept`, `neighbour`, `similarity` columns identical
    (`np.allclose`, exact `concept`/`neighbour` match) between old and new
    code paths.
- `compute_spearman_alignment_with_empirical_p_value.py`:
  - Ran against `nsd_data`/`dinov2_s` (515 brain concepts vs. 66,216 model
    concepts): completed in ~9.3s, ~1.5GB peak RSS, `number_of_concepts=515`,
    `number_of_pairs=132355` (matches `C(515,2)`, matches pre-mismatch
    historical runs for other models).
  - Regression check against `caption_scene`/`dinov2_g` (8,920 matching
    concepts, `number_of_relabellings=1000`, `random_seed=37`): exact
    match on `observed_spearman_coefficient` (`0.000606`) against the
    existing production output.
- `relabel_llm_similarity_and_compute_relabelled_llm_alignment_score.py`:
  - Ran against `nsd_data`/`dinov2_s` with real `isc_cosine_nearest_neighbours_5NN.parquet`:
    completed in 7s, ~1.25GB peak RSS, `515` unique concepts in the
    output, `2575` rows (`515 concepts × 5 relabellings`).
  - Regression check against `caption_scene`/`dinov2_s` (`number_of_relabellings=1000`,
    `random_seed=37`): `concept`, `common_neighbours`, `alignment_score`
    identical (8,920,000 rows) against the existing production output.
- `compute_llm_llm_empirical_p_value.py`:
  - Ran against `nsd_data` `dinov2_s`×`i21k_b` (one side at full 66,216
    scale): completed in 10s, ~1.2GB peak RSS.
  - Regression check against `caption_scene` `dinov2_s`×`i21k_b`
    (`number_of_relabellings=1000`, `random_seed=37`): exact match
    (`number_of_shared_concepts=8920`, `observed_alignment_score=0.28042600896860986`,
    `empirical_p_value=0.000999...`) against the existing production
    output.
- `fmri_processing.compute_leave_one_out_isc`:
  - Numerically validated against the original implementation across
    several `(n_subjects, n_timepoints, n_parcels)` shapes and an explicit
    constant-parcel edge case (both dataset-wide-constant and
    single-subject-constant): `np.allclose` within `1e-5` in all cases
    (max observed diff `~3e-8`, i.e. float32 rounding only).
  - Benchmarked at `nsd_data`-like scale (3 observations, 4 TRs, 200
    parcels): 182.9ms/call → 0.367ms/call (**~499x**); projected full
    `nsd_data` run (66,216 stimuli): ~12,109s → ~24.3s.
- `get_embeddings.py` output construction: validated old vs. new
  DataFrame construction produce identical columns, column types, index,
  and values, including through an actual Parquet round-trip
  (`to_parquet`/`read_parquet`).
- `estimate_batch_size.py`: ran `suggest_batch_size` against all 23
  models currently in `config.yaml`; outputs land within (or at the
  conservative edge of) the originally-proposed per-size-class ranges.
- All 8 touched/added files pass `python -m py_compile`.
- `snakemake --cores 4 -n --rerun-triggers mtime` against the three
  fixed-rule output types for `nsd_data`/`dinov2_s` (Spearman, llm_llm
  empirical p-value, relabelled alignment score): DAG builds cleanly,
  jobs listed with sensible `reason:` chains through the fixed rules.
- Not run: an actual `snakemake --use-conda --cores <N>` execution of the
  full pipeline (would take substantial wall-clock time and, per the
  disk-space note above, is not currently safe to run to completion for
  all models without a storage decision first).

## Files touched

- `workflow/libraries/read_similarity_subset.py` (new)
- `workflow/libraries/compute_nearest_neighbours.py`
- `workflow/libraries/fmri_processing.py`
- `workflow/libraries/estimate_batch_size.py` (new, unused so far)
- `workflow/llm_nearest_neighbours/scripts/compute_llm_nearest_neighbours.py`
- `workflow/llm_nearest_neighbours/scripts/compute_llm_similarity.py`
- `workflow/llm_nearest_neighbours/scripts/get_embeddings.py`
- `workflow/spearman_alignment/scripts/compute_spearman_alignment_with_empirical_p_value.py`
- `workflow/llm_mind_alignment/scripts/relabel_llm_similarity_and_compute_relabelled_llm_alignment_score.py`
- `workflow/llm_llm_alignment/scripts/compute_llm_llm_empirical_p_value.py`
- `resources/models/*` (permissions only, `chmod -R u+w`, no content change)

---

*This changelog entry was drafted by an AI coding assistant (Claude Code,
model Claude Sonnet 5, `claude-sonnet-5`) based on the session's code
changes and the verification steps run during that session, and reviewed
by the developer before being committed.*
