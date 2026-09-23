# LLMmind

A Snakemake pipeline that measures how well the internal representations of
pretrained language and vision models ("LLMs") align with human brain
activity, using nearest-neighbour structure in representational space as the
basis for comparison.

For each (dataset, model, similarity metric, neighbourhood size) combination,
the pipeline:

1. Extracts per-concept/per-stimulus brain response patterns from fMRI data
   (inter-subject correlation, or "mind" representations) for each dataset.
2. Extracts model embeddings for the same stimuli from a set of pretrained
   language/vision models.
3. Computes nearest-neighbour graphs in both spaces (brain and model) under a
   chosen similarity metric (cosine or Pearson).
4. Scores brain-model alignment as the overlap between the two
   nearest-neighbour graphs, with empirical (permutation-based) and
   hypergeometric significance testing.
5. Also computes model-model alignment (how similar two models' representational
   geometries are to each other) and Spearman rank-correlation alignment as a
   complementary metric.
6. Produces summary tables and plots (heatmaps, line plots, boxplots) across
   models, datasets, and similarity metrics.

## Repository layout

```
config/                   Snakemake configuration (config.yaml)
workflow/
  Snakefile                Top-level Snakefile: wires up all modules and the `all` rule
  libraries/                Shared Python helper modules (similarity, alignment,
                             nearest-neighbours, statistics, plotting utilities)
  dataset_processing/       Per-dataset rules: turn raw fMRI + stimuli into
                             "mind" representations (one subdirectory per dataset)
    caption_scene_dataset/
    narratives_dataset/
    nature_stories_dataset/
    nsd_data_dataset/
  isc_nearest_neighbours/   Nearest-neighbour graphs over brain (ISC) representations
  llm_nearest_neighbours/   Model download + embedding extraction + nearest-neighbour graphs
  llm_mind_alignment/       Brain-model alignment scoring and significance testing
  llm_llm_alignment/        Model-model alignment scoring
  spearman_alignment/       Spearman rank-correlation alignment (model- and concept-level)
  visualisation/            Plotting rules (heatmaps, line plots, boxplots)
  envs/                     Base environment for running Snakemake itself
                             (LLMmind_project_environment.yaml spec + the
                             materialized LLMmind_project/ conda prefix)
resources/
  atlases/                  Brain parcellation atlas used to extract ROI-level signal
  datasets/                 Raw dataset inputs (fMRI + stimuli) — not tracked in git
  models/                   Downloaded pretrained model weights — not tracked in git
results/                    Pipeline outputs — not tracked in git
docs/changelog/             Developer- and user-facing changelogs
```

## Subprojects

The pipeline is split into independent Snakemake modules under `workflow/`,
each included from the top-level `Snakefile` and each corresponding to one
step of the process described above.

### `dataset_processing/<dataset>/`

One subdirectory per dataset (`caption_scene_dataset`, `narratives_dataset`,
`nature_stories_dataset`, `nsd_data_dataset`). Each turns that dataset's raw
BOLD + stimuli into per-concept "mind" representations:

- extracts ROI-level (parcel) signal from the BOLD data using the Schaefer
  atlas
- computes inter-subject correlation (ISC) per concept/stimulus, producing
  one representative brain-response vector per concept
- cleans/prepares the matching stimuli (transcripts for the language
  datasets, images for the vision datasets) so they line up 1:1 with the ISC
  output and can be fed to the model embedding step

Because the four raw datasets are organised very differently, most of the
module-specific logic is manifest-building: matching scan files to
stimuli/concepts and excluding unusable subjects/runs/stimuli before the
shared parcel-extraction/ISC rules run.

Every dataset applies the same final inclusion rule: a stimulus is kept only
if it was presented to at least two different subjects. Each stimulus that
is dropped, by this rule or by a dataset-specific check, is written to that
dataset's `excluded_stimuli` file (path set in `config.yaml`). That file is
the single list of stimuli left out of the analysis:

- `get_embeddings` does not embed the stimuli it lists;
- `create_isc_manifest` (`isc_nearest_neighbours/`) does not use their ISC
  files, even if old ones are still on disk.

NSD's `assemble_nsd_bold` maps each kept presentation to MNI space and
reduces it straight to parcel time series, without writing full-brain
volumes to disk.

### `isc_nearest_neighbours/`

Takes the per-dataset ISC "mind" representations, computes concept-concept
similarity (cosine or Pearson), and builds the brain-side nearest-neighbour
graphs.

### `llm_nearest_neighbours/`

Downloads each configured pretrained model (`download_pretrained_llm`),
extracts its embeddings for the same stimuli, computes embedding-embedding
similarity, and builds the model-side nearest-neighbour graphs.

### `llm_mind_alignment/`

Scores brain-model alignment as the overlap between the brain and model
nearest-neighbour graphs, with empirical (permutation-based) and
hypergeometric significance testing.

### `llm_llm_alignment/`

Scores model-model alignment — how similar two models' representational
geometries are to each other — with empirical significance testing.

### `spearman_alignment/`

A complementary alignment metric using Spearman rank-correlation instead of
nearest-neighbour overlap, computed at both model- and concept-level, again
with empirical significance testing.

### `visualisation/`

Produces the summary plots described under [Outputs](#outputs): alignment
heatmaps, p-value heatmaps, per-concept alignment scatterplots, line plots,
and Spearman boxplots.

### `libraries/`

Shared Python helper modules (similarity, alignment, nearest-neighbours,
statistics, plotting) used across all of the above.

## Datasets

The pipeline currently supports four naturalistic fMRI datasets, configured
under their own key in `config/config.yaml`:

- `caption_scene` — image/caption viewing task (language + vision stimuli)
- `narratives` — spoken story listening (language stimuli, multiple tasks/runs)
- `nature_stories` — spoken story listening (language stimuli)
- `nsd_data` — Natural Scenes Dataset (vision stimuli)

Each dataset entry in `config.yaml` defines its stimuli directories (by
modality), subject count, exclusion lists, and dataset-specific acquisition
parameters (TR, event duration, etc.), plus the neighbourhood sizes
(`number_of_neighbours`) to evaluate for that dataset.

In every dataset, a stimulus is included only if it was presented to at
least two different subjects; every presentation (including repeats by the
same subject) then counts as one fMRI observation in its ISC. Stimuli that
fail this or any other dataset-specific check are listed in that dataset's
`excluded_stimuli` file, which both the ISC side and the model-embedding
side read, so the two always cover the same stimuli. For `nsd_data` and
`caption_scene` this leaves about 1,000 stimuli each (the images shown to
several subjects), so their `number_of_neighbours` values must stay below
that. The similarity and
nearest-neighbour computation steps (`llm_nearest_neighbours/`,
`isc_nearest_neighbours/`, `llm_llm_alignment/`, `llm_mind_alignment/`,
`spearman_alignment/`) never build or store a full stimulus × stimulus
similarity matrix at all: similarity is computed in blocks directly from
embeddings and immediately reduced to each concept's top-ranked
neighbours, capped at the largest neighbourhood size configured for that
dataset (`number_of_neighbours`, below) — the only thing any downstream
step actually needs. At the current dataset sizes this makes no practical difference to
the results, only to how much disk and memory computing them uses.

## Input data

None of the raw fMRI/stimuli datasets are tracked in git — they must be
present under `resources/datasets/` before the first run. `resources/models/`
(pretrained model weights) and `resources/atlases/` (the Schaefer
parcellation) do **not** need to be supplied manually: they are downloaded
automatically by the `download_pretrained_llm` rule and by
`nilearn.datasets.fetch_atlas_schaefer_2018` respectively, the first time
they're needed (internet access is required on first run). `results/` is
fully generated by the pipeline and can be empty/absent.

The four datasets need the following raw files, at these exact paths
relative to `resources/datasets/`:

**Caption Scene dataset** (`caption_scene_dataset/`)

- Preprocessed BOLD:
  `V1/derivatives/pp_data/sub-*/func/sub-*_ses-*_task-CSD_run-*.nii.gz`
- Run/event tables:
  `V1/stimuli/CSD/sub-{subject}/subject{subject}_run{run}.txt`
- Stimulus images:
  `V1/stimuli/COCO_CN/All_images_480/`
- Caption table:
  `V1/stimuli/COCO_CN/Translated_Image_Caption_pairs.tsv`

**Narratives dataset** (`narratives_dataset/`)

- Preprocessed BOLD:
  `derivatives/afni-smooth/sub-{subject}/func/sub-{subject}_task-{task}{run_tag}_space-MNI152NLin2009cAsym_res-native_desc-clean_bold.nii.gz`
- Original transcripts:
  `stimuli/transcripts/*_transcript.txt`
- Scan exclusion metadata:
  `scan_exclude.json`

**Nature Stories dataset** (`nature_stories_dataset/`)

- Subject BOLD responses:
  `responses/S01_BOLD.hdf` … `responses/S11_BOLD.hdf`
- Subject mapper files:
  `mappers/S01_mappers.hdf` … `mappers/S11_mappers.hdf`
- Run/story onset metadata:
  `responses/new_run_onsets.json`
- Source TextGrid stimulus files:
  `stimuli/textgrids/<story>.TextGrid`

**NSD dataset** (`nsd_data_dataset/`)

- Functional design files, subjects `subj01`–`subj08`:
  `nsddata_timeseries/ppdata/subjXX/func1pt8mm/design/design_session*_run*.tsv`
- Matching BOLD timeseries:
  `nsddata_timeseries/ppdata/subjXX/func1pt8mm/timeseries/timeseries_session*_run*.nii.gz`
- Stimulus images:
  `nsddata_stimuli/stimuli/nsd/nsd_stimuli.hdf5`
- Functional-to-MNI mapping data, used internally (via the `nsdcode`
  package) to register each subject's BOLD data into MNI space:
  `nsddata/ppdata/subjXX/transforms/`

Everything else under a dataset directory (e.g. `.stimuli_ready`,
`excluded_stimuli.txt`, renamed/derived transcripts) is generated by the
pipeline itself and must **not** be supplied manually. In particular,
`excluded_stimuli.txt` is rewritten from the stimulus-inclusion rules
(see [`dataset_processing/<dataset>/`](#dataset_processingdataset)); do
not edit it by hand to exclude stimuli.

### Organising the input data on disk

`resources/datasets/` is expected to contain one directory per dataset,
named exactly as above:

```
resources/datasets/
├── caption_scene_dataset/
├── narratives_dataset/
├── nature_stories_dataset/
└── nsd_data_dataset/
```

In this lab, these are not populated by hand: the sibling `public_datasets`
Snakemake project downloads/clones the raw data for all four datasets. Its
outputs land under `public_datasets/results_molilab_cold_back/<dataset>/`
(itself a symlink into cold storage,
`/mnt/molilab_cold_bak/LLMmind/downloaded_datasets`), **not** directly inside
this repository — after running it, link each dataset directory into place
here:

```bash
ln -s ../public_datasets/results_molilab_cold_back/caption_scene_dataset resources/datasets/caption_scene_dataset
ln -s ../public_datasets/results_molilab_cold_back/narratives_dataset/dataset resources/datasets/narratives_dataset
ln -s ../public_datasets/results_molilab_cold_back/nature_stories_dataset resources/datasets/nature_stories_dataset
ln -s ../public_datasets/results_molilab_cold_back/nsd_data_dataset resources/datasets/nsd_data_dataset
```

(paths above assume `public_datasets/` is checked out as a sibling of this
repository; adjust if yours lives elsewhere.) Note the extra `/dataset`
suffix for `narratives_dataset` — `public_datasets` also keeps a
`cloned_dataset/` working copy alongside the fetched files, which should
not be linked.

If you're sourcing the raw data some other way, just make sure the files
listed above end up at the same relative paths under
`resources/datasets/<dataset>/`.

## Models

Supported models are declared under `models:` in `config/config.yaml`, each
with a Hugging Face identifier, modality (`language`, `vision`, or
`multimodal`), optional quantization method, and parameter count. Currently
configured: the BLOOMZ, OpenLLaMA, and Gemma language model families; CLIP,
DINOv2, and ImageNet-21K ViT vision model families. Models are downloaded
on demand by the `llm_nearest_neighbours` module.

## Setup

The project uses conda environments managed per pipeline stage under
`workflow/*/envs/*.yaml`, plus a base environment for running Snakemake
itself at `workflow/envs/LLMmind_project`, specified by
`workflow/envs/LLMmind_project_environment.yaml` (just Python and
`snakemake-minimal`).

```bash
# create the base environment from its spec (first time only)
conda env create -f workflow/envs/LLMmind_project_environment.yaml -p workflow/envs/LLMmind_project

# activate it (see .envrc for the expected path)
conda activate workflow/envs/LLMmind_project
```

If you use [direnv](https://direnv.net/), `.envrc` activates this environment
automatically when you `cd` into the project.

Individual rules declare their own `conda:` environment
(`workflow/*/envs/*.yaml`), which Snakemake creates automatically when run
with `--use-conda`.

## Running the pipeline

From the project root, with the base environment active:

```bash
snakemake --use-conda --cores <N>
```

Useful variations:

```bash
# dry run to see what would be executed
snakemake --use-conda --cores <N> -n

# build a specific target only, e.g. one dataset's alignment scores
snakemake --use-conda --cores <N> results/all_alignment_scores.tsv
```

Pipeline behavior (datasets, models, similarity metrics, neighbourhood sizes,
number of permutations for significance testing) is controlled entirely
through `config/config.yaml` — no code changes are needed to add a model or
adjust a dataset's parameters.

Most rules are single-threaded and get their parallelism from Snakemake
running independent jobs concurrently, but a few instead parallelize
internally across whatever `--cores <N>` is given — notably NSD's
functional-to-MNI registration step (`assemble_nsd_bold`), which maps
stimulus presentations to MNI space and extracts their parcel time series
using up to `<N>` worker processes at once. For that step, a higher `--cores` value directly speeds it up.

### Troubleshooting

- **`ProtectedOutputException` / write-protected files under
  `resources/models/`**: pretrained models are downloaded via
  `huggingface_hub`, which can leave downloaded files (and sometimes their
  containing directory) read-only. If Snakemake refuses to (re)build a
  model directory because of this, run `chmod -R u+w resources/models/`
  and retry. If Snakemake also reports that a model's software
  environment definition has changed since it was last downloaded, either
  launch with `--rerun-triggers mtime` to ignore that check, or run
  `snakemake --cleanup-metadata <path>` for the affected outputs if you're
  confident the already-downloaded weights don't actually need
  re-fetching.
- **Disk space for `nsd_data`**: similarity computation never writes a full
  stimulus × stimulus matrix (see [Datasets](#datasets) above), so
  per-model disk use is now driven by the dataset's largest configured
  neighbourhood size rather than a fixed ~88GB regardless of it. If you
  have result directories from before 2026-09-22 containing
  `*_similarity.parquet` files or neighbour files with a `_<k>NN` suffix,
  those are stale — the pipeline no longer produces or reads either, and
  they're safe to delete. Likewise,
  `results/mind/nsd_data/single_stimulus_bold_mni/` (full-brain MNI volumes
  per NSD presentation, written before 2026-09-23) is no longer produced or
  read and can be deleted.
- **Results don't change after editing a dataset's inclusion rules**: the
  manifest scripts are called from `shell:` rules, so Snakemake doesn't
  notice when their code changes. After changing them, force the manifest
  step and let everything downstream rebuild, e.g.
  `snakemake --use-conda --cores <N> --forcerun make_nsd_manifest make_caption_scene_manifest`.
- **"Requested k neighbours, but only n candidates"**: a dataset's
  `number_of_neighbours` must be smaller than its number of included
  stimuli (about 1,000 for `nsd_data` and `caption_scene`).

## Outputs

Key outputs land under `results/`:

- `results/alignment_scores/` — per-(dataset, model, similarity, k) alignment
  scores and significance tests. Brain-model results get a per-concept
  empirical and hypergeometric p-value plus a model-level empirical p-value;
  model-model results get a single model-pair-level empirical p-value (no
  per-concept or hypergeometric test). Both use the same random-shuffling
  method to build their null distributions.
- `results/all_alignment_scores.tsv`, `results/all_spearman_alignment_scores.tsv`
  — combined summary tables across all configurations
- `results/alignment_heatmaps/`, `results/alignment_p_value_heatmaps/`,
  `results/alignment_lineplots/`, `results/concept_alignment_scatterplots/`,
  `results/spearman_alignment/*_plots/` — summary visualisations. In the
  concept-level alignment and Spearman boxplots, a model whose per-concept
  scores show no spread renders as a flat, easy-to-miss box; those are
  marked with a red diamond rather than left looking like missing data.
  The model-level line plots and concept-level scatterplots for a given
  dataset/similarity/k share the same `[0, 1]` y-axis range, so the two can
  be compared directly side by side.

## Documentation

- [`docs/changelog/developers/`](docs/changelog/developers/) — technical
  changelog entries for contributors
- [`docs/changelog/users/`](docs/changelog/users/) — plain-language changelog
  entries describing what changed for anyone running the pipeline

Parts of this README and of the changelog entries were drafted with AI
coding assistants: Claude Code with Claude Sonnet 5 and, from 2026-09-23,
Claude Opus 5.5. Each changelog entry ends with a note saying which model
was used and whether the entry has been reviewed.
