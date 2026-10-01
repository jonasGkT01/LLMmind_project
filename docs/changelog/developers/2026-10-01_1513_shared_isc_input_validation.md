# 2026-10-01 — One shared loader and validator for the four ISC scripts

## Change

`workflow/libraries/fmri_processing.py` gains two helpers:

- `compute_isc_from_files(paths, n_rois, truncate_to_shortest = False)`: loads the (time × parcel)
  `.npy` files and checks that there are at least 2, that each is 2-D with `n_rois` columns and
  that all time lengths are equal. Unequal lengths raise a `ValueError` listing every file's
  length; with `truncate_to_shortest = True` the arrays are truncated to the shortest instead,
  and the truncated files and their original lengths are printed. It then stacks the arrays as
  float32 and returns `compute_leave_one_out_isc()`.
- `single_value(df, column, group)`: returns the only value of `column` in `df`, or raises a
  `ValueError` naming `group`. It replaces the hand-written "exactly one output path per group"
  checks.

The four `compute_*_isc.py` scripts use them:

| Script | Before | After |
|---|---|---|
| `compute_narratives_isc.py` | own `compute_isc()`; no 2-D/`n_rois` check; **silent** truncation to the shortest run | helper with `truncate_to_shortest = True`: gains the shape check, truncation is printed to the job log |
| `compute_caption_scene_isc.py` | own `compute_isc()`; dead `parcel_output_path()` and `pandas` import | helper; dead code removed |
| `compute_nature_stories_isc.py` | own `compute_isc()` with a redundant file-exists check, a redundant output-shape check and a second float32 cast | helper; `expected_subjects` and duplicate-subject checks kept in `main()` |
| `compute_nsd_isc.py` | inline loading and checks | helper; grouping per presentation unchanged (TODO P10) |

The NIfTI writers are unchanged here (removed separately by TODO S7). Every command-line argument
is unchanged, so no shell command changes and nothing reruns. The edited lines follow the layout of
`LLMmind/.claude/CLAUDE.md` section 4.

## Verification

All parcel files are float32 (checked on a sample of every dataset), so the float32 cast is a
no-op for the two scripts that did not cast before. The original scripts (`d3db409`) and the new ones
were run on one item per dataset, with outputs redirected to a scratch directory: Narratives
`merlin` (35 subjects, 613–657 TRs, so truncation is exercised), Caption Scene
`COCO_train2014_000000434623`, Nature Stories `souls` and NSD `nsd-60457`. All four `.npy` and
three `.nii.gz` outputs were byte-identical (`cmp`). The error paths (fewer than 2 files, wrong
shape, unequal lengths, several values in `single_value`) were exercised on small test arrays.

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-01, Claude Opus 5.5: written for TODO entry S6, approved by the developer on 2026-09-30; the implementation plan was approved on 2026-10-01 ("go on with S6, S7, S28, and S32").*
- *Files changed: `workflow/libraries/fmri_processing.py`, `workflow/dataset_processing/narratives_dataset/scripts/compute_narratives_isc.py`, `workflow/dataset_processing/caption_scene_dataset/scripts/compute_caption_scene_isc.py`, `workflow/dataset_processing/nature_stories_dataset/scripts/compute_nature_stories_isc.py`, `workflow/dataset_processing/nsd_data_dataset/scripts/compute_nsd_isc.py`.*
- *Review status: not yet reviewed by the developer.*
