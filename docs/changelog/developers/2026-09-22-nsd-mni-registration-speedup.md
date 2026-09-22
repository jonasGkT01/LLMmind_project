# 2026-09-22 — NSD: cache the func1pt8→MNI transform per subject and parallelize `assemble_nsd_bold`

## Summary

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

## Changes

### `workflow/dataset_processing/nsd_data_dataset/scripts/assemble_nsd_bold.py`

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

### `workflow/dataset_processing/nsd_data_dataset/Snakefile`

- `assemble_nsd_bold` rule: added `threads: workflow.cores` and
  `--jobs {threads}` to the shell command. This rule now claims however
  many cores the pipeline was invoked with (`snakemake --cores <N>`) rather
  than a fixed/configured number — per explicit preference (this runs on a
  shared lab server; the user wants it to scale with whatever `--cores`
  value is chosen at launch time, not a hardcoded default baked into
  `config.yaml`).

## Compatibility note

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

## Verification

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

## Known remaining cost

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

## Files touched

- `workflow/dataset_processing/nsd_data_dataset/scripts/assemble_nsd_bold.py`
- `workflow/dataset_processing/nsd_data_dataset/Snakefile`
