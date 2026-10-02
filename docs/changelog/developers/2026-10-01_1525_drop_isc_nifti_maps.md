# 2026-10-01 — The ISC rules no longer write NIfTI maps

## Change

`compute_caption_scene_isc.py`, `compute_narratives_isc.py` and `compute_nsd_isc.py` projected each
per-parcel ISC vector back onto the 182×218×182 Schaefer atlas and saved it as
`*_isc_mean.nii.gz` (2018 files, 1.3 GB). No rule or script read these files; everything downstream
uses the `.npy` vectors. Removed:

- in the three scripts: the NIfTI writer (`save_isc_outputs()`/`save_isc()`/inline code), the
  `fetch_atlas_schaefer_2018()` + `load_img()` atlas loading, the `nibabel`/`nilearn` imports and
  the arguments only the NIfTI used (`--isc_nii`, `--yeo_networks`, `--atlas_dir`; NSD:
  `--number_of_yeo_networks`, `--atlas_dir`). The remaining arguments are `--manifest --n_rois`
  (Narratives), `--parcel_ts --isc_npy --n_rois` (Caption Scene) and `--manifest
  --number_of_regions` (NSD);
- in `caption_scene_dataset/Snakefile`, rule `compute_caption_scene_isc`: the `isc_nii` output, its
  shell argument and the `yeo_networks`/`atlas_dir` params;
- in `narratives_dataset/Snakefile`: `NARRATIVES_ISC_NII_OUTPUTS` (and its use in
  `rule all_narratives_dataset` and `compute_narratives_isc`), the `isc_nii` column written by
  `write_narratives_isc_manifest()`, and the `yeo_networks`/`atlas_dir` params of
  `compute_narratives_isc`;
- in `nsd_data_dataset/Snakefile`: the `isc_nifti_file` column written by
  `write_nsd_isc_manifest()` and the `number_of_yeo_networks`/`atlas_dir` params of
  `compute_nsd_isc`.

The parcel-extraction rules keep their atlas params. Nature Stories never wrote NIfTIs. The
changed lines follow the layout of `LLMmind/.claude/CLAUDE.md` section 4.

## Rerun cost and merge plan

The ISC values do not change, but the three ISC rules' shell commands and params change, so
Snakemake reruns them and everything downstream: a dry run on 2026-10-01 listed 3,745 jobs,
including all relabelling jobs. This commit is therefore held on its own branch, `s7-isc-nifti` (based on `todo-fixes`), and merged
into `main` only together with the batched full rerun (TODO S22). The existing
`results/mind/*/isc/*_isc_mean.nii.gz` files are deleted at that point.

## Verification

For Narratives `merlin`, Caption Scene `COCO_train2014_000000434623` and NSD `nsd-60457`, the
`.npy` written by the new scripts is byte-identical (`cmp`) to that of the original scripts
(`d3db409`). A dry run of the changed workflow parsed without errors.

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-01, Claude Opus 5.5: written for TODO entry S7 (option B, approved by the developer on 2026-09-30); on 2026-10-01 the developer approved implementing it now and merging it only with the batched full rerun ("go on with S6, S7, S28, and S32").*
- *Files changed: `workflow/dataset_processing/narratives_dataset/Snakefile`, `workflow/dataset_processing/caption_scene_dataset/Snakefile`, `workflow/dataset_processing/nsd_data_dataset/Snakefile`, `workflow/dataset_processing/narratives_dataset/scripts/compute_narratives_isc.py`, `workflow/dataset_processing/caption_scene_dataset/scripts/compute_caption_scene_isc.py`, `workflow/dataset_processing/nsd_data_dataset/scripts/compute_nsd_isc.py`.*
- *Review status: not yet reviewed by the developer.*
