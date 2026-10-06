# 2026-09-22 — developer changelog

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../../AI_USAGE.md).*

Changes made on this day, in order:

- Plot raw concept-level alignment scores instead of enrichment ratios (new_feature)
- NSD: cache the func1pt8→MNI transform per subject and parallelize `assemble_nsd_bold` (optimisation)
- Pin model-level and concept-level alignment plots to a shared [0, 1] y-axis (new_feature)
- nsd_data at full scale: memory-safe similarity/nearest-neighbour computation, ISC vectorization (optimisation)
- Stop writing dense N×N similarity matrices; compute-once max-k neighbours instead (optimisation)

---

## Plot raw concept-level alignment scores instead of enrichment ratios

Kind: `new_feature`

### Summary

The model-level plot (`plot_brain_model_alignment_lineplot.py`) plots the
raw mean `alignment_score`. The concept-level boxplot
(`plot_concept_alignment_enrichment.py`) instead plotted a derived
`enrichment` ratio (`alignment_score / hypergeometric_expected_alignment_score`),
so the two plots were not showing the same underlying quantity. Changed the
concept-level plot to show the raw `alignment_score` per concept, matching
the model-level plot, and renamed the script and its output accordingly
(including making explicit that it is a scatter/boxplot, not a lineplot).

### Changes

#### `workflow/visualisation/scripts/plot_concept_alignment_enrichment.py` → `workflow/visualisation/scripts/plot_concept_alignment_scatterplot.py`

- Renamed the script.
- `read_model_enrichments()` → `read_model_alignment_scores()`: still
  validates path metadata, required columns, duplicated concepts, score
  range, and `number_of_neighbours <= population_size`, and still computes
  the hypergeometric `expected_alignment_score` for the file (`k /
  (number_of_concepts - 1)`), but now returns the raw `alignment_score`
  column instead of dividing by `expected_alignment_score` to produce an
  `enrichment` column. Also returns `expected_alignment_score` to the
  caller instead of embedding it in the ratio.
- `main()`: collects `expected_alignment_score` across all input files and
  raises `ValueError` if they are inconsistent (they are expected to be
  equal within one plot, since all models in a plot share the same
  concept set and `k`). The boxplot/scatter now plot `alignment_score`
  directly; the `ax.axhline(...)` reference line is now drawn at the
  (raw-score) `expected_alignment_score` value instead of a fixed `1.0`,
  since `1.0` was only meaningful for the enrichment ratio.
- Updated plot title (`"Concept-level LLM-brain alignment"`) and y-axis
  label (`"Alignment score"`, was `"Observed alignment / hypergeometric
  expected alignment"`).

#### `workflow/visualisation/Snakefile`, `workflow/Snakefile`

- Renamed rule `plot_concept_alignment_enrichment` → `plot_concept_alignment_scatterplot`.
- Renamed its output directory `results/alignment_enrichment_plots/` →
  `results/concept_alignment_scatterplots/`, and the output filename
  fragment `concept_alignment_enrichment` → `concept_alignment`.
- Updated the `shell:` invocation to call the renamed script.

#### `README.md`

- Updated the `Outputs` and `visualisation/` sections to reference
  `results/concept_alignment_scatterplots/` and "per-concept alignment
  scatterplots" instead of the enrichment naming.

### Verification

- `python3 -m py_compile workflow/visualisation/scripts/plot_concept_alignment_scatterplot.py`.
- Grepped the repository (excluding `results/` and historical changelog
  entries) for `concept_alignment_enrichment`, `alignment_enrichment_plots`,
  `read_model_enrichments`, and the intermediate `plot_concept_alignment.py`
  name — no remaining references.

### Files touched

- `workflow/visualisation/scripts/plot_concept_alignment_enrichment.py` (deleted)
- `workflow/visualisation/scripts/plot_concept_alignment_scatterplot.py` (added)
- `workflow/visualisation/Snakefile`
- `workflow/Snakefile`
- `README.md`

---

## NSD: cache the func1pt8→MNI transform per subject and parallelize `assemble_nsd_bold`

Kind: `optimisation`

### Summary

`workflow/dataset_processing/nsd_data_dataset/scripts/assemble_nsd_bold.py`
calls the functional-to-MNI mapping once per stimulus occurrence — currently
208,650 times across the full manifest (`results/mind/nsd_data/manifests/nsd_occurrence_manifest.tsv`).
Previously this was one call to `NSDmapdata.fit()` per occurrence, and
`NSDmapdata.fit()` reloads the subject's `func1pt8-to-MNI.nii.gz`
deformation field (~50MB compressed) from disk and rebuilds the flattened
`(3, 7221032)` interpolation coordinate array from it on **every single
call**, even though both only depend on the subject (8 total), not the
occurrence. Benchmarked on this machine: `nib.load` ≈0.16s + `get_fdata()`
≈3.25s + coordinate construction ≈1.83s ≈ 5.2s of pure, redundant overhead
per call. At 208,650 calls that alone is ≈12 days of wall-clock time spent
reloading and rebuilding identical data, before any interpolation happens —
this was the dominant cost of the step, not the interpolation math.

Separately, the whole step ran single-threaded in one Snakemake job despite
being embarrassingly parallel across occurrences, on a machine with 128
cores.

This change addresses both, without altering the mapping itself.

### Changes

#### `workflow/dataset_processing/nsd_data_dataset/scripts/assemble_nsd_bold.py`

- Replaced the per-occurrence `NSDmapdata.fit()` call with a local,
  narrower reimplementation of its volume-to-volume (`func1pt8` → `MNI`)
  path, built directly from `nsdcode`'s own public functions
  (`nsd_datalocation`, `parse_case`, `load_transform`, `interp_wrapper`,
  `nsd_write_vol`) rather than `nsdcode.nsd_mapdata.NSDmapdata`. This was
  necessary because `NSDmapdata.fit()` has no way to accept a
  pre-loaded transform — the reload is internal to the call, so avoiding it
  meant not calling `fit()` at all for this fixed, single use case.
- `get_subject_mni_transform(dataset_dir, subject)`: loads the transform and
  builds the interpolation coordinates once per subject, cached in a
  module-level dict (`_subject_mni_transform_cache`). Reused, unmodified,
  across all of that subject's occurrences.
  - `interp_wrapper()` mutates invalid (non-finite / `9999`-sentinel)
    coordinates in place on first use, which would silently stop flagging
    those locations as invalid on a second reuse of the same array — a
    correctness risk specific to sharing this array across calls. Checked
    all 8 subjects' `func1pt8-to-MNI.nii.gz` files directly: none contain
    `9999` or `NaN` values, so sharing the array is safe today. The cache
    still detects this per subject (`reusable = not np.any(~np.isfinite(coords))`)
    and falls back to a per-occurrence `coords.copy()` if it's ever not the
    case, rather than assuming it always holds.
- `map_occurrence_to_mni(...)`: the per-occurrence interpolation loop,
  copied from `nsdcode.transform_data`'s case-1/`n_dims==4`/`targetspace ==
  'MNI'` branch verbatim (same `interp_wrapper` call, badval handling,
  Fortran-order reshape, axis-0 flip for LPI output, MNI origin
  `[183-91, 127, 73] - 1`), just with `coords`/`target_shape` passed in
  instead of rebuilt inline. `outputclass` is hardcoded to `np.float64`
  to match the original pipeline's actual output dtype (see Compatibility
  note).
- Removed the temp-file round trip: the cropped BOLD array no longer gets
  written to a temporary NIfTI and immediately read back just to satisfy
  `fit()`'s path-based `sourcedata` argument. `map_occurrence_to_mni` takes
  the in-memory `cropped_bold_data` array directly.
- Added `process_group(dataset_dir, subject, source_bold, occurrences,
  interptype, badval)`: the per-`(subject, source_bold)` unit of work
  (unchanged grouping rationale — avoid reloading the same BOLD run
  repeatedly), now also the parallelization unit.
- Added a `--jobs` CLI argument (default `1`, preserving serial behavior
  when unset). When `--jobs > 1`, groups are dispatched to a
  `concurrent.futures.ProcessPoolExecutor(max_workers=jobs)`; each worker
  process keeps its own `_subject_mni_transform_cache`, so a worker only
  pays the per-subject transform load once across however many groups it's
  assigned. Groups are sorted by subject before dispatch as a scheduling
  heuristic to increase the odds that a given worker's groups share a
  subject (not a guarantee — `ProcessPoolExecutor` doesn't expose control
  over which worker gets which task).
- Per-occurrence `print(...)` replaced with a per-group summary print
  (`n_occurrences`, `n_volumes`), since the parallel path can't
  interleave 208,650 individual prints from separate processes usefully.

#### `workflow/dataset_processing/nsd_data_dataset/Snakefile`

- `assemble_nsd_bold` rule: added `threads: workflow.cores` and
  `--jobs {threads}` to the shell command. This rule now claims however
  many cores the pipeline was invoked with (`snakemake --cores <N>`) rather
  than a fixed/configured number — per explicit preference (this runs on a
  shared lab server; the user wants it to scale with whatever `--cores`
  value is chosen at launch time, not a hardcoded default baked into
  `config.yaml`).

### Compatibility note

No change to scientific output. Verified bit-exact:
`np.array_equal(old_result, new_result)` is `True` (`max abs diff: 0.0`)
comparing the original `NSDmapdata.fit()` path against the new cached path
on a real subj03 occurrence (3 volumes, cubic interpolation). This holds
because:

- float32→float64 widening (source data was always upcast to float64 for
  interpolation either way — `interp_wrapper` does
  `.astype(np.float64)` internally regardless of input dtype) is lossless,
  so skipping the temp-file round trip changes nothing numerically.
- `outputclass` is still forced to `float64`, matching what the original
  code produced (via `nib.load(...).get_fdata()`'s default `float64`
  upcast on the temp file it read back — the original script's `outputclass
  = sourceclass` was float64 in practice, not float32, even though the
  cropped array had been cast to float32 before being written to the temp
  file).
- The transform/coordinates themselves are unmodified; only *when* they're
  computed changed (once per subject instead of once per call).

No manifest, config, or output-path changes. `results/mind/nsd_data/single_stimulus_bold_mni/`
outputs do not need to be regenerated for correctness — this is a pure
performance change — but will naturally be regenerated on the next full
run since `assemble_nsd_bold.py`'s content hash changed.

### Verification

- Benchmarked `nib.load` / `get_fdata()` / coordinate construction on
  `subj01`'s real `func1pt8-to-MNI.nii.gz` (`(182, 218, 182, 3)`, 51.7MB on
  disk): confirmed the ≈5.2s/call redundant cost driving the original
  runtime estimate.
- Checked all 8 subjects' `func1pt8-to-MNI.nii.gz` for `9999` sentinel /
  `NaN` values directly (`np.sum(data == 9999)`, `np.sum(np.isnan(data))`):
  zero in all 8, confirming the shared-coordinate-array reuse is safe.
- Correctness: ran both the original (`NSDmapdata.fit()` via temp file) and
  new (cached) code paths on a real subj03 occurrence
  (`timeseries_session19_run05.nii.gz`, volumes 141:144) and diffed the
  outputs — exact match (see Compatibility note).
- End-to-end: ran the updated script against a 4-row manifest spanning two
  subjects (subj01, subj03) with `--jobs 4`, real BOLD/transform data,
  output paths redirected to a scratch directory. All 4 groups completed
  and produced `(182, 218, 182, 3)` float64 NIfTI outputs as expected.
- `snakemake -n -j 4 --snakefile workflow/dataset_processing/nsd_data_dataset/Snakefile
  assemble_nsd_bold`: dry-run confirms `threads: workflow.cores` resolves
  to `4` (the `-j` value) and the rendered shell command includes
  `--jobs 4`.
- Not measured: end-to-end wall-clock time on the full 208,650-row
  manifest (would itself take a long time and require the full dataset).
  The per-call overhead and per-volume interpolation cost were benchmarked
  individually instead (see Summary and the "Known remaining cost" note
  below).

### Known remaining cost

Removing the redundant reload does not remove the actual interpolation
cost. Benchmarked cubic (`order=3`) interpolation via
`scipy.ndimage.map_coordinates` at ≈3.5–4.7s per volume (mapping an
≈81×106×82 source volume onto the ≈7.2M-voxel MNI target grid). With
≈626,000 volumes total across the manifest (208,650 occurrences × ~3
volumes each), that's still tens of hours of unavoidable interpolation
compute — which is now the actual bottleneck, addressed here by
parallelizing across occurrences (`--jobs`/`threads: workflow.cores`)
rather than by changing the interpolation itself. Switching
`config["nsd_data"]["map_interpolation"]` from `"cubic"` to `"linear"` (or
`"nearest"`) would reduce this further, but that's a precision/quality
tradeoff, not a pure performance change, and was intentionally left as-is.

### Files touched

- `workflow/dataset_processing/nsd_data_dataset/scripts/assemble_nsd_bold.py`
- `workflow/dataset_processing/nsd_data_dataset/Snakefile`

---

## Pin model-level and concept-level alignment plots to a shared [0, 1] y-axis

Kind: `new_feature`

### Summary

`plot_brain_model_alignment_lineplot.py` (model-level line plot) and
`plot_concept_alignment_scatterplot.py` (concept-level scatter/boxplot) are
meant to be viewed side by side for the same `(dataset, similarity_type,
number_of_neighbours)` combination — they are listed adjacently in `rule
all_visualisation` and plot the same underlying `[0, 1]`-bounded
`alignment_score` quantity (see
`2026-09-22_new_feature_optimisation.md`). Both scripts previously
called `ax.set_ylim(bottom=0)` with no explicit top, leaving matplotlib to
autoscale the top independently for each plot. Because the line plot's data
is a small number of per-model means (low variance, small vertical spread)
while the scatter plot's data is every individual concept's raw score
(much higher variance), the two plots' autoscaled tops diverged
substantially: the line plot's points/errorbars ended up crowded near the
top of its own canvas even though both plots represent values in the same
`[0, 1]` range. There is no shared-figure/report code that composites the
two plots (each is an independent script/rule producing its own PNG), so
the fix is a fixed, hardcoded y-limit rather than a computed shared bound.

Both scripts already validate that `alignment_score` lies in `[0, 1]`
before plotting (`((alignment_scores < 0) | (alignment_scores >
1)).any()` checks), so `(0, 1)` is a safe, always-correct bound for both.

### Changes

#### `workflow/visualisation/scripts/plot_brain_model_alignment_lineplot.py`

- `ax.set_ylim(bottom=0)` → `ax.set_ylim(0, 1)` (was line 205). `figsize`
  was already `(fig_width, 7)`, matching the concept-level script, so plot
  height was not changed.

#### `workflow/visualisation/scripts/plot_concept_alignment_scatterplot.py`

- `ax.set_ylim(bottom=0,)` → `ax.set_ylim(0, 1,)` (was line 165).

### Verification

- `python3 -m py_compile` on both scripts.
- Not re-run against pipeline output in this session (no runtime dependency
  changed; the edit only replaces an autoscaled top bound with a fixed one
  already within the scripts' own validated data range).

### Files touched

- `workflow/visualisation/scripts/plot_brain_model_alignment_lineplot.py`
- `workflow/visualisation/scripts/plot_concept_alignment_scatterplot.py`
- `README.md`
- `docs/changelog/developers/2026-09-22_new_feature_optimisation.md` (this file)
- `docs/changelog/users/2026-09-22_new_feature_optimisation.md`

---

## nsd_data at full scale: memory-safe similarity/nearest-neighbour computation, ISC vectorization

Kind: `optimisation`

### Summary

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

### Changes

#### `workflow/libraries/read_similarity_subset.py` (new)

- `read_similarity_subset(path, concepts, source)`: reads only the
  columns/rows needed for a given `concepts` list from a similarity
  Parquet file, via `pyarrow.parquet.read_table(columns=[...])` column
  projection, rather than loading the full square matrix. Raises a clear
  `ValueError` naming missing concepts (up to 5) instead of a bare
  `KeyError`/`ValueError` from a downstream equality check. Moved here
  from a local definition in `compute_spearman_alignment_with_empirical_p_value.py`
  (previously the only user) so `relabel_llm_similarity_and_compute_relabelled_llm_alignment_score.py`
  could reuse it.

#### `workflow/libraries/compute_nearest_neighbours.py`

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

#### `workflow/llm_nearest_neighbours/scripts/compute_llm_nearest_neighbours.py`

- Replaced `pd.read_parquet(...)` + manual square/order validation +
  `create_nearest_neighbours_dataframe(...)` with a single call to
  `stream_nearest_neighbours_from_parquet(...)`. The square/order checks
  now happen cheaply against Parquet metadata inside the streaming
  function instead of after a full load.

#### `workflow/spearman_alignment/scripts/compute_spearman_alignment_with_empirical_p_value.py`

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

#### `workflow/llm_mind_alignment/scripts/relabel_llm_similarity_and_compute_relabelled_llm_alignment_score.py`

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

#### `workflow/llm_llm_alignment/scripts/compute_llm_llm_empirical_p_value.py`

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

#### `workflow/libraries/fmri_processing.py`

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

#### `workflow/llm_nearest_neighbours/scripts/get_embeddings.py`

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

#### `workflow/llm_nearest_neighbours/scripts/compute_llm_similarity.py`

- Added `del cosine_result, cosine_similarity_df` immediately after the
  cosine similarity matrix is written to Parquet, before the Pearson
  similarity matrix is computed. Previously both the cosine result/frame
  and the embedding matrix were kept alive (via still-referenced local
  variables) while the Pearson matrix was computed the same way, so both
  full N×N matrices (43.8GB each at `nsd_data` scale) coexisted at peak.
  `compute_isc_similarity.py` has the identical structural pattern but was
  left as-is — harmless at ISC's ~515-concept scale.

#### `workflow/libraries/estimate_batch_size.py` (new, not yet wired into any rule)

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

### Operational fix: model-download directories were not writable

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

### Not done in this session

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

### Verification

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

### Files touched

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

## Stop writing dense N×N similarity matrices; compute-once max-k neighbours instead

Kind: `optimisation`

### Summary

The previous entry in this changelog
([`2026-09-22_new_feature_optimisation.md`](2026-09-22_new_feature_optimisation.md))
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
[`2026-09-21_new_feature_bugfix_refactor_removal_documentation.md`](2026-09-21_new_feature_bugfix_refactor_removal_documentation.md))
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

### Design notes worth preserving

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

### Changes

#### `workflow/libraries/compute_nearest_neighbours.py`

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

#### `workflow/libraries/compute_similarity.py`

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

#### `workflow/libraries/read_similarity_subset.py` — deleted

Dead code: nothing reads a persisted similarity matrix to take a subset of
any more (introduced in the previous session's entry; superseded here).

#### `workflow/llm_nearest_neighbours/scripts/compute_llm_similarity.py` — deleted

The full-matrix writer. Superseded by the rewritten
`compute_llm_nearest_neighbours.py` below.

#### `workflow/llm_nearest_neighbours/scripts/compute_llm_nearest_neighbours.py`

Rewritten: takes `--embedding_dataframe` and one `--number_of_neighbours`
(the dataset's max configured `k`) and computes both `--cosine_nearest_neighbours`
and `--pearson_nearest_neighbours` in one call via
`compute_blockwise_topk_from_embeddings`, embeddings loaded once. Replaces
both the old `compute_llm_similarity.py` and the old per-`k`
`compute_llm_nearest_neighbours.py` in one script.

#### `workflow/isc_nearest_neighbours/scripts/compute_isc_similarity.py` — deleted

Same role as `compute_llm_similarity.py`, mind side. Deleted for the same
reason.

#### `workflow/isc_nearest_neighbours/scripts/compute_isc_nearest_neighbours.py`

Rewritten analogously to the LLM-side script: takes `--isc_dataframe` +
`--number_of_neighbours`, uses `dataframe_to_embedding_matrix` to handle
the ISC dataframe's array-column shape, writes both similarity types via
`compute_blockwise_topk_from_embeddings`.

#### `workflow/llm_mind_alignment/scripts/compute_llm_mind_alignment_score.py`

Added `require_stored_number_of_neighbours` + `slice_top_k_neighbours` on
both inputs before calling the unchanged `compute_alignment_scores` — both
input files now hold the dataset's max `k`, not exactly the `k` this job
needs.

#### `workflow/llm_llm_alignment/scripts/compute_llm_llm_alignment_score.py`

Same addition (`require_stored_number_of_neighbours` +
`slice_top_k_neighbours` in `read_nearest_neighbours`) — this consumer of
the LLM-side neighbour file was easy to miss since it wasn't part of the
originally-scoped consumer list, but has the identical "file now holds
more neighbours than this job's `k`" issue; caught during implementation,
not design.

#### `workflow/llm_llm_alignment/scripts/compute_llm_llm_empirical_p_value.py`

Rewritten: `select_shared_concepts` now reads each model's *embeddings*
file's index (`read_embedding_concepts`, a single-column Parquet read) via
`--llm_embeddings_1`/`--llm_embeddings_2` instead of a similarity matrix's
column names. `compute_shared_subset_topk_indices` restricts each model's
embeddings to the shared-concept subset and calls
`compute_blockwise_topk_from_embeddings` directly — replaces
`stream_topk_indices_from_parquet`. New required `--similarity_type` arg
(previously implicit in which matrix file was passed) selects the
normalize function via `normalize_fn_for_similarity_type`.

#### `workflow/llm_mind_alignment/scripts/relabel_llm_similarity_and_compute_relabelled_llm_alignment_score.py`

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

#### `workflow/llm_mind_alignment/scripts/extract_relabelled_alignment_score_for_k.py` (new)

Filters the combined `--relabelled_common_neighbours` file to one
`--number_of_neighbours` value, drops that column, and writes it out in
the exact schema (`shuffle_id`, `model`, `concept`, `common_neighbours`,
`alignment_score`, `alignment_score_percentage`) every existing downstream
consumer already expects.

#### `workflow/spearman_alignment/scripts/compute_spearman_alignment_with_empirical_p_value.py`

Takes `--brain_embeddings`/`--model_embeddings` instead of
`--brain_similarity`/`--model_similarity`. `compute_similarity_dataframe`
computes the (always small — bounded by the brain-eligible concept count)
subset similarity matrix in-process via
`normalize_fn_for_similarity_type(args.similarity_type)` + a matmul,
equivalent to `cosine_similarity`/`pearson_similarity` from
`libraries/compute_similarity.py`. Ranking/relabelling/permutation logic
unchanged.

#### Snakefiles

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

### Disk cleanup

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

### Not done in this session

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

### Verification

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

### Files touched

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
