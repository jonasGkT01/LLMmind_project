# 2026-09-21 — Document required input data and per-module breakdown in README

## Summary

`README.md` previously described the repository layout only at the
one-line-per-directory level (see `2026-09-21-add-project-readme.md`) and
said nothing about which raw files must exist under `resources/datasets/`
before a first run, nor how they get there. Added two new sections —
`## Subprojects` and `## Input data` — with content verified against the
current on-disk state rather than inferred from code alone.

## Source material / verification method

- **Required raw file paths**: verified directly against the populated
  `resources/datasets/{caption_scene_dataset,narratives_dataset,
  nature_stories_dataset,nsd_data_dataset}/` trees (`find`/`ls` for exact
  filename patterns and counts — e.g. 1600 BOLD runs + 1600 matching CSD
  event tables for `caption_scene_dataset`, 811 `afni-smooth` BOLD files for
  `narratives_dataset`, S01–S11 `_BOLD.hdf`/`_mappers.hdf` pairs for
  `nature_stories_dataset`, per-subject `design_session*_run*.tsv` /
  `timeseries_session*_run*.nii.gz` counts for `nsd_data_dataset` subj01–08).
- **NSD functional→MNI mapping requirement**: traced instead of assumed.
  `workflow/dataset_processing/nsd_data_dataset/scripts/assemble_nsd_bold.py`
  calls `nsdcode.nsd_mapdata.NSDmapdata(dataset_dir)`. Read the installed
  package source under
  `.snakemake/conda/b8a4553242f8148bf6c43764ef8548a2_/lib/python3.14/
  site-packages/nsdcode/` (`nsd_datalocation.py` + `nsd_mapdata.py`) to
  confirm it resolves to exactly `<dataset_dir>/nsddata/ppdata/subjXX/
  transforms/`, which matches what's present on disk (86 files/subject).
- **Directory-linking mechanism**: read the sibling `public_datasets/`
  project's `workflow/Snakefile` (a separate Snakemake pipeline, not part of
  this repo) — its `rule all` targets write to
  `results_molilab_cold_back/<dataset>/.*_complete` markers, where
  `results_molilab_cold_back` is a symlink to
  `/mnt/molilab_cold_bak/LLMmind/downloaded_datasets`. Confirmed via `ls -la`
  that `resources/datasets/<dataset>` in *this* repo are themselves symlinks
  into `public_datasets/results_molilab_cold_back/<dataset>` (with an extra
  `/dataset` path segment for `narratives_dataset`, since `public_datasets`
  also keeps a `cloned_dataset/` datalad working copy alongside the fetched
  files). No rule in either repo creates these symlinks automatically — they
  were made by hand in the current checkout.

## Changes

### `README.md`

- New `## Subprojects` section, inserted after `## Repository layout`: one
  subsection per `workflow/*` module (`dataset_processing/<dataset>/`,
  `isc_nearest_neighbours/`, `llm_nearest_neighbours/`,
  `llm_mind_alignment/`, `llm_llm_alignment/`, `spearman_alignment/`,
  `visualisation/`, `libraries/`), each describing its role and mapping back
  to the numbered pipeline overview at the top of the file. Rule names were
  cross-checked against each module's `Snakefile` (`grep -n "^rule "`) to
  keep the descriptions accurate.
- New `## Input data` section, inserted after `## Datasets` and before
  `## Models`:
  - Per-dataset lists of the exact raw file paths/glob patterns required
    under `resources/datasets/<dataset>/` (see verification method above).
  - Explicit callout that `resources/models/` and `resources/atlases/` do
    *not* need to be populated manually (`download_pretrained_llm` rule and
    `nilearn.datasets.fetch_atlas_schaefer_2018` respectively handle those on
    demand), and that `resources/` internal generated files (`.stimuli_ready`,
    `excluded_stimuli.txt`, renamed transcripts, etc.) must not be supplied
    by hand.
  - New `### Organising the input data on disk` subsection documenting the
    expected `resources/datasets/<dataset>/` layout and, specific to this
    lab's setup, the `ln -s` commands needed to link `public_datasets/`
    output into place (since that pipeline's outputs land in a different
    physical location and are not wired up automatically).

## Notes / caveats for future edits

- The `ln -s` commands in the README hard-code the assumption that
  `public_datasets/` is checked out as a sibling of this repository — true
  in the current environment (`/home/molinerislab/LLMmind/{public_datasets,
  LLMmind_project}`) but not guaranteed elsewhere; the README already flags
  this as an assumption to adjust.
- If `public_datasets/workflow/Snakefile` changes its output paths (e.g.
  the `results_molilab_cold_back` root or the `narratives_dataset/dataset`
  subdirectory), the symlink commands and the "Organising the input data on
  disk" prose in `README.md` will need updating to match — nothing enforces
  this link automatically.
- The exact required-file lists are a manual transcription of what was
  observed on disk; if a dataset module's manifest logic changes to expect
  additional/renamed raw files (e.g. a new exclusion input), update both the
  `## Input data` section here and, if relevant, the corresponding
  `dataset_processing/<dataset>/Snakefile`.

## Files touched

- `README.md` (modified — two new sections added, no existing content
  removed or reordered)
