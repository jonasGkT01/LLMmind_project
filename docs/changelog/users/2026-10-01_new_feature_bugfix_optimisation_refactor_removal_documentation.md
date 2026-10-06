# 2026-10-01 — changes for users

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../../AI_USAGE.md).*

Changes made on this day, in order:

- Fixed: the model-model summary table step crashed (bugfix)
- Python cache folders no longer show up in git (refactor)
- Unused ISC helper removed (removal)
- Model download fixed for the installed `huggingface_hub` (bugfix)
- ISC scripts share one input check; Narratives reports truncation (refactor)
- Snakemake commands no longer rewrite Narratives files (refactor)
- ISC NIfTI maps are no longer produced (removal)
- Two methods details written down (documentation)
- Nearest-neighbour code simplified (refactor)
- Models are ordered the same way in every figure (refactor)
- Old, disabled pipeline steps removed from the code (removal)
- The two summary tables are built faster (optimisation)
- Shorter model names in the plots (new_feature)
- The model download script takes named options (refactor)
- Fixed software versions for every pipeline step (new_feature)

---

## 09:37 — Fixed: the model-model summary table step crashed

Kind: `bugfix`

### What happened

The step that combines all model-model results into
`results/all_model_model_alignment_scores.tsv` crashed with "exit status 126" and no other message.
It handed the program the names of more than 26,000 files at once. That list (about 4 MB) is
longer than Linux lets any program receive when it starts (2 MB), so the program never started.
Your data and results were not affected.

### What changed

The step now writes the list of files into a temporary file and gives the program that file
instead. The results are exactly the same, and nothing else has to be recomputed.

### What to do

Restart the pipeline as usual on node5. Only this one step runs, and it creates
`results/all_model_model_alignment_scores.tsv` and then the plots that need it.

### Context

- Request: the developer asked why the project crashed.
- Files changed: `workflow/llm_llm_alignment/Snakefile`, `workflow/llm_llm_alignment/scripts/aggregate_all_llm_llm_p_value_outputs.py`.

---

## 14:59 — Python cache folders no longer show up in git

Kind: `refactor`

The `__pycache__/` folders that Python creates when you run a script are now ignored by git
wherever they appear, not only in `workflow/libraries/`. They no longer appear as untracked
files in `git status`. Nothing else changes.

### Context

- Request: Written for TODO entry S5, approved by the developer on 2026-09-30 and confirmed on 2026-10-01 ("start solving the problems that do not involve the aggregation code").
- Files changed: `.gitignore`.

---

## 14:59 — Unused ISC helper removed

Kind: `removal`

An unused helper function (`safe_pearsonr()`) was removed from the fMRI code, and the description
of the ISC function now says plainly what it computes. The ISC values are exactly the same and
nothing needs to be rerun.

### Context

- Request: Written for TODO entry S8, approved by the developer on 2026-09-30 and confirmed on 2026-10-01 ("start solving the problems that do not involve the aggregation code").
- Files changed: `workflow/libraries/fmri_processing.py`.

---

## 14:59 — Model download fixed for the installed `huggingface_hub`

Kind: `bugfix`

Downloading a new model (rule `download_pretrained_llm`) would have crashed with the installed
version of `huggingface_hub`, because the script passed an option that no longer exists. The option
is removed. Models already in `resources/models/` are not affected and nothing is re-downloaded.

### Context

- Request: Written for TODO entry S25, approved by the developer on 2026-09-30 and confirmed on 2026-10-01 ("start solving the problems that do not involve the aggregation code").
- Files changed: `workflow/llm_nearest_neighbours/scripts/download_pretrained_llm.py`.

---

## 15:13 — ISC scripts share one input check; Narratives reports truncation

Kind: `refactor`

The four scripts that compute the inter-subject correlation (ISC) for Narratives, Caption Scene,
Nature Stories and NSD now load and check their input files with the same code. In practice:

- The ISC values are exactly the same as before, and nothing needs to be rerun.
- Narratives used to shorten all subjects of a story to the shortest run without saying so. It now
  writes to the job log which files were shortened and from which length.
- Narratives now also stops with an error if a parcel file has the wrong shape, as the other
  datasets already did.

### Context

- Request: Written for TODO entry S6, approved by the developer on 2026-09-30; the implementation plan was approved on 2026-10-01 ("go on with S6, S7, S28, and S32").
- Files changed: `workflow/libraries/fmri_processing.py`, `workflow/dataset_processing/narratives_dataset/scripts/compute_narratives_isc.py`, `workflow/dataset_processing/caption_scene_dataset/scripts/compute_caption_scene_isc.py`, `workflow/dataset_processing/nature_stories_dataset/scripts/compute_nature_stories_isc.py`, `workflow/dataset_processing/nsd_data_dataset/scripts/compute_nsd_isc.py`.

---

## 15:19 — Snakemake commands no longer rewrite Narratives files

Kind: `refactor`

Every Snakemake command, even a dry run, used to rewrite 18 length-check files in
`results/mind/narratives/qc/` and a list of excluded scans in `resources/datasets/narratives_dataset/`.
Nothing used them, so they are no longer written, and the existing ones are deleted.

- Which Narratives runs are shortened, and from which length, now appears in the log of the
  `compute_narratives_isc` job.
- Which Narratives tasks are excluded, and why, is in `config/config.yaml` (`tasks`,
  `schema_subtasks`, `notthefall_variants`).
- `docs/reference/fmri_preprocessing.md` (step 5) explains why shortening the runs is safe.

Nothing needs to be rerun.

### Context

- Request: Written for TODO entries S28 and S32, approved by the developer on 2026-09-30; the implementation plan was approved on 2026-10-01 ("go on with S6, S7, S28, and S32").
- Files changed: `workflow/dataset_processing/narratives_dataset/Snakefile`, `config/config.yaml`, `docs/reference/fmri_preprocessing.md`.

---

## 15:25 — ISC NIfTI maps are no longer produced

Kind: `removal`

The workflow used to save every stimulus's ISC values also as a brain map
(`results/mind/*/isc/*_isc_mean.nii.gz`, 2018 files, 1.3 GB). Nothing used these maps, so they are
no longer written. The ISC values themselves (`*_isc_mean.npy`) are exactly the same.

This change becomes active together with the next full rerun of the pipeline, because Snakemake
would otherwise recompute the whole downstream analysis just for it. The existing maps are deleted
at that point.

### Context

- Request: Written for TODO entry S7 (option B, approved by the developer on 2026-09-30); on 2026-10-01 the developer approved implementing it now and merging it only with the batched full rerun ("go on with S6, S7, S28, and S32").
- Files changed: `workflow/dataset_processing/narratives_dataset/Snakefile`, `workflow/dataset_processing/caption_scene_dataset/Snakefile`, `workflow/dataset_processing/nsd_data_dataset/Snakefile`, `workflow/dataset_processing/narratives_dataset/scripts/compute_narratives_isc.py`, `workflow/dataset_processing/caption_scene_dataset/scripts/compute_caption_scene_isc.py`, `workflow/dataset_processing/nsd_data_dataset/scripts/compute_nsd_isc.py`.

---

## 15:32 — Two methods details written down

Kind: `documentation`

- `docs/reference/fmri_preprocessing.md` (step 6) now says that the ISC is averaged over subjects
  as a plain mean of correlation values, without a Fisher z-transform, and why. Use it for the
  methods section.
- `config/config.yaml` now explains how model names must be built: `<family>_<size>`, where the
  size has no underscore (for example `clip_i21k_ft_b` is family `clip_i21k_ft`, size `b`). Follow
  it when you add a model, because the figures group and order models by this family.

Nothing changes in the results.

### Context

- Request: Written for TODO entries S11 (option b) and S14 (option B), approved by the developer on 2026-09-30; implemented on 2026-10-01 after the developer asked which solutions could be done while the S34 check was running ("proceed").
- Files changed: `docs/reference/fmri_preprocessing.md`, `config/config.yaml`.

---

## 15:34 — Nearest-neighbour code simplified

Kind: `refactor`

The two scripts that find the nearest neighbours of every concept, one for the model embeddings
and one for the brain (ISC) vectors, now share the same code. Their results are exactly the same
as before, and nothing needs to be rerun.

### Context

- Request: Written for TODO entries S18 and S20 (item 1), approved by the developer on 2026-09-30; implemented on 2026-10-01 after the developer asked which solutions could be done while the S34 check was running ("proceed").
- Files changed: `workflow/libraries/compute_nearest_neighbours.py`, `workflow/llm_nearest_neighbours/scripts/compute_llm_nearest_neighbours.py`, `workflow/isc_nearest_neighbours/scripts/compute_isc_nearest_neighbours.py`.

---

## 15:46 — Models are ordered the same way in every figure

Kind: `refactor`

Every figure that lists models now uses the same order: model family in alphabetical order, then
model size, then model name, then stimulus type, with the brain last in the heatmaps. Before, the
heatmaps and the other figures each sorted in their own way, and the order of the models in
`config/config.yaml` could change some figures.

Today's figures do not change (checked: they are identical). From now on, adding a model anywhere
in `config/config.yaml` does not change where it appears in a figure.

### Context

- Request: Written for TODO entry S1, modified and approved by the developer on 2026-09-30; implemented on 2026-10-01 after the developer asked which solutions could be done while the S34 check was running ("proceed").
- Files changed: `workflow/libraries/manage_model_metadata.py`, `workflow/visualisation/scripts/plot_empirical_p_value_heatmap.py`, `workflow/visualisation/scripts/plot_alignment_heatmap.py`, `workflow/visualisation/scripts/plot_brain_model_alignment_lineplot.py`, `workflow/visualisation/scripts/plot_concept_alignment_scatterplot.py`, `workflow/visualisation/scripts/plot_spearman_alignment.py`, `workflow/visualisation/scripts/plot_brain_model_alignment_enrichment_lineplot.py`, `workflow/visualisation/scripts/plot_concept_alignment_enrichment_scatterplot.py`.

---

## 16:18 — Old, disabled pipeline steps removed from the code

Kind: `removal`

Two pipeline steps had been switched off long ago but were still in the Snakefiles as comments:
one that built `results/tsv_summary.tsv` and one that built `…observed.tsv` files. Both have been
replaced by `results/all_model_brain_alignment_scores.tsv`. Their leftover code is now deleted.

Nothing changes when you run the pipeline: no step reruns and no result changes.

### Context

- Request: Written for TODO entry S29 item 3 (Snakefile part), approved by the developer on 2026-09-30; implemented after the developer asked to do the parts of S29 that do not interfere with the running S34 check.
- Files changed: `workflow/Snakefile`, `workflow/llm_mind_alignment/Snakefile`.

---

## 16:40 — The two summary tables are built faster

Kind: `optimisation`

The steps that build `results/all_model_brain_alignment_scores.tsv` and
`results/all_model_model_alignment_scores.tsv` now use 4 processor cores instead of one, and skip
a check that could never fail. The model-model table took 4 h 10 min on node5; it should now take
about 1 h. The model-brain table should drop from about 16 min to about 5 min.

The tables themselves are exactly the same (checked byte for byte).

**What to do:** nothing special. The next time you run the pipeline, these two steps (and the plots
that use the tables) run once more. Give Snakemake at least `--cores 4`, as usual, so they run at
full speed.

### Context

- Request: Written for TODO entry S34, approved by the developer on 2026-10-01 and revised after measurement, after the developer asked to start addressing the TODO problems while the pipeline was running.
- Files changed: `workflow/libraries/aggregate_alignment_scores.py`, `workflow/llm_mind_alignment/Snakefile`, `workflow/llm_mind_alignment/scripts/aggregate_all_p_value_outputs.py`, `workflow/llm_llm_alignment/Snakefile`, `workflow/llm_llm_alignment/scripts/aggregate_all_llm_llm_p_value_outputs.py`, `README.md`, `docs/reference/clean_run_duration.md`.

---

## 19:00 — Shorter model names in the plots

Kind: `new_feature`

The plots now label each model with its name only, for example `clip_b` instead of
`clip_b-vision`. Whether a model ran on text or on images is still shown by the colour of its
name (orange for language, green for vision) and by the legend. File names do not change.

**What to do:** existing figures keep the old labels until they are redrawn. To redraw them now,
run once:

```bash
snakemake --use-conda --cores 4 --rerun-triggers mtime --forcerun plot_alignment_heatmap plot_empirical_p_value_heatmap plot_concept_alignment_scatterplot plot_brain_model_alignment_lineplot plot_concept_alignment_enrichment_scatterplot plot_brain_model_alignment_enrichment_lineplot plot_spearman_alignment
```

This redraws only the plots (193 jobs). Keep `--rerun-triggers mtime`: without it, Snakemake would
also rerun almost the whole pipeline (about 41,000 jobs), because it sees older conda environment
definitions recorded for the upstream steps. Otherwise the figures are redrawn with the next full
run.

### Context

- Request: Written for TODO entry S36, raised and approved by the developer on 2026-10-01.
- Files changed: `workflow/visualisation/scripts/plot_alignment_heatmap.py`, `workflow/visualisation/scripts/plot_empirical_p_value_heatmap.py`, `workflow/visualisation/scripts/plot_brain_model_alignment_lineplot.py`, `workflow/visualisation/scripts/plot_concept_alignment_scatterplot.py`, `workflow/visualisation/scripts/plot_brain_model_alignment_enrichment_lineplot.py`, `workflow/visualisation/scripts/plot_concept_alignment_enrichment_scatterplot.py`, `workflow/visualisation/scripts/plot_spearman_alignment.py`, `README.md`.

---

## 19:24 — The model download script takes named options

Kind: `refactor`

The script that downloads the pretrained models now takes named options and has a working
`--help`, like the other scripts:

```bash
python3 workflow/llm_nearest_neighbours/scripts/download_pretrained_llm.py \
    --model_name bigscience/bloomz-560m \
    --save_dir resources/models/bloom_560m
```

Before, it took the two values without names, and its help message pointed to a folder that no
longer exists. The pipeline calls it for you, so you only need this when downloading a model by
hand.

This change is kept apart and will be added together with the next full rerun of the pipeline,
because it makes Snakemake want to redo every model download and everything after it.

### Context

- Request: Written for TODO entry S37, option (b) chosen by the developer on 2026-10-01.
- Files changed: `workflow/llm_nearest_neighbours/scripts/download_pretrained_llm.py`, `workflow/llm_nearest_neighbours/Snakefile`.

---

## 22:24 — Fixed software versions for every pipeline step

Kind: `new_feature`

Every software package the pipeline installs now has a fixed version, so rebuilding the
environments (on another machine, or after deleting `.snakemake/conda/`) gives the same
software and the same results. The versions are the latest available on 2026-10-01, with
Python 3.14 everywhere. The README section "Pinned versions" lists the rules and explains how to
upgrade a package safely.

This also fixes a hidden problem: a newly built model-embedding environment would have crashed on
the GPU for the Gemma models. It only worked so far thanks to a file cached from an earlier run.

The new versions were checked against the current ones: the brain data processing, the
statistics, the embeddings (including the 8-bit and 4-bit Gemma models on node5) and a plot gave
the same results.

**What to do:** nothing yet. This change is kept apart and will be added for the next full rerun of
the pipeline, because changing the environments makes Snakemake redo every step. At that time the
Snakemake environment itself has to be rebuilt once by hand (see the README).

### Context

- Request: Written for TODO entry S22, approved by the developer.
- Files changed: all 11 `*_environment.yaml` files (`workflow/envs/`, `workflow/*/envs/`, `workflow/dataset_processing/*/envs/`), `README.md`.
