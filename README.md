# LLMmind

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](docs/AI_USAGE.md).*

A Snakemake pipeline that measures how well the internal representations of
pretrained language and vision models align with human brain activity, using
nearest-neighbour structure in representational space as the basis for
comparison. (Directory and rule names say `llm` for any model, language or
vision.)

For each (dataset, model, similarity metric, neighbourhood size) combination,
the pipeline:

1. Extracts per-stimulus brain representations from fMRI data: for each
   stimulus, the inter-subject correlation (ISC) of 200 brain parcels.
2. Extracts model embeddings for the same stimuli from a set of pretrained
   language and vision models.
3. Computes nearest-neighbour graphs in both spaces (brain and model) under a
   chosen similarity metric (cosine, Pearson or Spearman).
4. Scores brain-model alignment as the overlap between the two
   nearest-neighbour graphs, with empirical (permutation-based) and
   hypergeometric significance testing.
5. Also computes model-model alignment (how similar two models'
   representational geometries are) and Spearman rank-correlation alignment as
   a complementary metric.
6. Produces summary tables and plots (heatmaps, line plots, boxplots) across
   models, datasets and similarity metrics.

## Documentation

- [`docs/guides/running_and_troubleshooting.md`](docs/guides/running_and_troubleshooting.md)
  — how to run parts of the pipeline, when Snakemake reruns a job, the
  settings that change many results, the software environments, model
  limitations and what to do when a run fails
- [`docs/reference/fmri_preprocessing.md`](docs/reference/fmri_preprocessing.md)
  — what each dataset's authors did to the BOLD data before this workflow, and
  what the workflow itself does, up to the ISC (a source for the methods
  section)
- [`docs/reference/model_embeddings.md`](docs/reference/model_embeddings.md)
  — how each model turns a stimulus into one vector: chunking, pooling
  (including the BOS token) and the CLS token of vision models (a source for
  the methods section)
- [`docs/reference/statistics.md`](docs/reference/statistics.md)
  — alignment scores, the relabelling and Spearman nulls, the empirical and
  hypergeometric tests, enrichment, the Benjamini-Hochberg families, and what
  every figure shows and how it is laid out (a source for the methods section)
- [`docs/reference/clean_run_duration.md`](docs/reference/clean_run_duration.md)
  — how long a clean run takes on node5 (about 31 h), rule by rule
- [`docs/changelog/developers/`](docs/changelog/developers/) and
  [`docs/changelog/users/`](docs/changelog/users/) — one file per day with
  changes, technical and plain-language. Each file name lists the kinds of
  change made that day (`new_feature`, `bugfix`, `optimisation`, `refactor`,
  `removal`, `documentation`)
- [`docs/AI_USAGE.md`](docs/AI_USAGE.md) — how AI coding assistants were used
  in this project, and the date and model of the latest AI edit of every file

## Repository layout

```
config/                     Snakemake configuration (config.yaml)
workflow/
  Snakefile                 Top-level Snakefile: wires up all modules and the `all` rule
  libraries/                Shared Python helper modules (similarity, alignment,
                             nearest-neighbours, statistics, plotting utilities)
  dataset_processing/       Per-dataset rules: turn raw fMRI + stimuli into
                             brain representations (one subdirectory per dataset)
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
docs/
  guides/                   How to run the pipeline and fix failed runs
  reference/                Methods: fMRI processing, embeddings, statistics; run duration
  changelog/                Developer- and user-facing changelogs, one file per day
  AI_USAGE.md               AI assistance policy and per-file AI edit list
```

## Modules

The pipeline is split into Snakemake modules under `workflow/`, each included
from the top-level `Snakefile` and each corresponding to one step above.

### `dataset_processing/<dataset>/`

One subdirectory per dataset. Each builds manifests that match scan files to
stimuli and exclude unusable subjects, runs and stimuli; extracts the mean
signal of each Schaefer parcel; and computes the leave-one-subject-out ISC per
stimulus and parcel. It also prepares the matching stimuli (transcripts for
the language datasets, images for the vision datasets) for the embedding step.
The details, dataset by dataset, are in
[`fmri_preprocessing.md`](docs/reference/fmri_preprocessing.md).

Each stimulus that is dropped is written to that dataset's `excluded_stimuli`
file (path set in `config.yaml`). That file is the single list of stimuli left
out of the analysis: `get_embeddings` does not embed them, and
`create_isc_manifest` (`isc_nearest_neighbours/`) does not use their ISC
files, so the brain and model sides always cover the same stimuli.

### `isc_nearest_neighbours/`

Takes the per-dataset ISC vectors, computes stimulus-stimulus similarity and
builds the brain-side nearest-neighbour graphs.

### `llm_nearest_neighbours/`

Downloads each configured model (`download_pretrained_llm`), extracts its
embeddings for the same stimuli (`get_embeddings`, see
[`model_embeddings.md`](docs/reference/model_embeddings.md)), computes
embedding-embedding similarity and builds the model-side nearest-neighbour
graphs.

### `llm_mind_alignment/`

Scores brain-model alignment as the overlap between the brain and model
nearest-neighbour graphs, with empirical (permutation-based) and
hypergeometric significance testing.

### `llm_llm_alignment/`

Scores model-model alignment with the same tests, reusing the
`llm_mind_alignment/` p-value scripts. Pairs are formed between
*(model, stimulus type)* entries, so on a dataset with both text and image
stimuli a language model is also compared with a vision model.

### `spearman_alignment/`

A complementary alignment metric: the Spearman rank correlation between the
brain's and the model's similarity structures, at model and concept level,
with empirical significance testing.

### `visualisation/`

Produces the plots listed under [Outputs](#outputs).

### `libraries/`

Shared Python helper modules used across all of the above.
`code_version.py` is used by the Snakefiles themselves, so that some rules
rerun when their code changes (see the
[guide](docs/guides/running_and_troubleshooting.md#2-when-snakemake-reruns-a-job)).

None of the similarity and nearest-neighbour steps builds or stores a full
stimulus × stimulus similarity matrix: similarity is computed in blocks and
immediately reduced to each stimulus's top-ranked neighbours, up to the
largest neighbourhood size configured for that dataset.

## Datasets

Four naturalistic fMRI datasets, each configured under its own key in
`config/config.yaml`:

- `caption_scene` — image/caption viewing task (language + vision stimuli)
- `narratives` — spoken story listening (language stimuli)
- `nature_stories` — spoken story listening (language stimuli)
- `nsd_data` — Natural Scenes Dataset (vision stimuli)

Each entry defines the stimuli directories (by modality), subject count,
exclusion lists, acquisition parameters (TR, event duration, etc.) and the
neighbourhood sizes (`number_of_neighbours`) to evaluate. A stimulus is kept
only if at least `minimum_subjects_per_stimulus` different subjects saw it
(default 2), which leaves about 1,000 stimuli each in `nsd_data` and
`caption_scene`. Nature Stories requires every subject for every story.

## Input data

None of the raw fMRI/stimuli datasets are tracked in git — they must be
present under `resources/datasets/` before the first run. `resources/models/`
(pretrained model weights) and `resources/atlases/` (the Schaefer
parcellation and the MNI152NLin6Asym template) do **not** need to be supplied
manually: they are downloaded automatically by the `download_pretrained_llm`
rule, by `nilearn.datasets.fetch_atlas_schaefer_2018` and by the
`fetch_mni_template` rule (from TemplateFlow) respectively, the first time
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
- T1w scans, used to register each subject to MNI:
  `V1/sub-{subject}/anat/sub-{subject}_ses-01_run-001_T1w.nii.gz`

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

### Input files not produced by the download

`public_datasets` does not produce every input file listed above. The
files below come from the public datasets but must be extracted, copied or
corrected by hand:

- **`caption_scene_dataset/V1/stimuli/CSD/`**: extracted from the downloaded
  archive `V1/stimuli/CSD.rar` of the Caption Scene dataset, with
  `unrar x CSD.rar` inside `V1/stimuli/`.
- **`narratives_dataset/scan_exclude.json`**: a copy of
  `code/scan_exclude.json` from the Narratives DataLad dataset
  (`https://datasets.datalad.org/labs/hasson/narratives`), where it is
  tracked in git and needs no `datalad get`.
- **`nature_stories_dataset/responses/new_run_onsets.json`**: a corrected
  copy of `responses/run_onsets.json` from the Nature Stories archive (G-Node
  GIN, DOI `10.12751/g-node.t4wew2`). The dataset README states that each
  story in `zRresp` was z-scored on its own before concatenation, but with the
  original boundaries 7 of the 10 training stories are not z-scored. The
  corrected file shifts six boundaries by 1–2 TRs (the total, 3737 TRs, is
  unchanged):

  | Story | Original onset, length | Corrected onset, length |
  |---|---|---|
  | alternateithicatom | 0, 345 | 0, 343 |
  | avatar | 345, 366 | 343, 367 |
  | howtodraw | 711, 353 | 710, 354 |
  | naked | 2252, 421 | 2252, 422 |
  | odetostepfather | 2673, 406 | 2674, 404 |
  | souls | 3079, 355 | 3078, 355 |
  | undertheinfluence | 3434, 303 | 3433, 304 |

  With these boundaries every story segment of `zRresp` has, voxel by voxel,
  mean 0 and standard deviation 1 to machine precision (about 1e-14) in all
  11 subjects, and moving any boundary by one TR breaks this, so the
  corrected values can be re-derived from the public `*_BOLD.hdf` files.

## Models

Models are declared under `models:` in `config/config.yaml`, each with a
Hugging Face identifier, modality (`language` or `vision`), optional
quantization method and parameter count. Currently configured: the BLOOMZ,
OpenLLaMA and Gemma (Gemma, Gemma 2, Gemma 3, Gemma 3n, Gemma 4) language
model families; the CLIP, DINOv2 and ImageNet-21K ViT vision model families.
Models are downloaded on demand by the `llm_nearest_neighbours` module.

A model runs on the stimulus type of a dataset that matches its modality:
`language` models on text, `vision` models on images. Every output file names
a model together with its stimulus type, as `<model>-<stimuli_type>` (for
example `clip_b-vision`). To add a model, add its block to the config and
rerun; multimodal and mixture-of-experts models are not supported (see the
[guide](docs/guides/running_and_troubleshooting.md#5-model-limitations)).

## Setup

The project uses a base environment for running Snakemake itself at
`workflow/envs/LLMmind_project`, specified by
`workflow/envs/LLMmind_project_environment.yaml` (Python and `snakemake`).

```bash
# create the base environment from its spec (first time only)
conda env create -f workflow/envs/LLMmind_project_environment.yaml -p workflow/envs/LLMmind_project

# activate it (see .envrc for the expected path)
conda activate workflow/envs/LLMmind_project
```

If you use [direnv](https://direnv.net/), `.envrc` activates this environment
automatically when you `cd` into the project. Every rule declares its own
pinned `conda:` environment (`workflow/*/envs/*.yaml`), which Snakemake
creates automatically with `--use-conda`.

## Running the pipeline

From the project root, with the base environment active:

```bash
# dry run to see what would be executed
snakemake --use-conda --cores <N> -n

# run everything
snakemake --use-conda --cores <N>
```

All pipeline behaviour (datasets, models, similarity metrics, neighbourhood
sizes, number of permutations) is set in `config/config.yaml`; no code changes
are needed to add a model or adjust a dataset. The main values (model
modality, quantization, model-key format, similarity types, minimum subjects
per stimulus, neighbourhood sizes) are checked when the pipeline starts, and a
wrong value stops it at once with a message naming the key. Partial runs, rerun behaviour,
the settings that rebuild many results and the fixes for common failures are
in [`running_and_troubleshooting.md`](docs/guides/running_and_troubleshooting.md).

## Outputs

Key outputs land under `results/`. Per-configuration files carry the
similarity metric (`cosine`, `pearson` or `spearman`) in their name; the
combined summary tables have a `similarity_type` column instead.

- `results/alignment_scores/` — per-(dataset, model, similarity, k) alignment
  scores and significance tests, brain-model and model-model: a per-concept
  empirical and hypergeometric p-value plus a model-level (model-pair-level)
  empirical p-value. The shuffled scores are kept as one compact all-k file per
  configuration in `relabelled_common_neighbours/`: the shuffled number of
  common neighbours for every relabelling, concept and k.
- `results/spearman_alignment_scores/` — per-(dataset, model, similarity)
  Spearman alignment with its empirical p-value, one `_model_level` and one
  `_concept_level` TSV per configuration.
- `results/all_model_brain_alignment_scores.tsv`,
  `results/all_model_model_alignment_scores.tsv`,
  `results/all_spearman_alignment_scores.tsv` — combined summary tables
  across all configurations, in long format. In the model-model table the
  `model`/`stimuli_type` pair becomes `model_1 | stimuli_type_1 | model_2 |
  stimuli_type_2`, each pair once, with `model_1` earlier than `model_2` in the
  `models:` order of the config. The p-values are not corrected for multiple
  testing. The model-level test is `model_level_empirical_p_value`; the six
  `*_p_value_across_concepts` statistics are descriptive summaries of the
  per-concept p-values, not tests (see
  [`statistics.md`](docs/reference/statistics.md)).
- `results/pictures/` — every plot and heatmap, one subfolder per plot type:
  `alignment_heatmaps/`, `alignment_p_value_heatmaps/`,
  `alignment_lineplots/`, `concept_alignment_scatterplots/`,
  `alignment_enrichment_lineplots/`,
  `concept_alignment_enrichment_scatterplots/`,
  `spearman_alignment_lineplots/`, `concept_spearman_alignment_scatterplots/`.
  The "scatterplots" are concept-level boxplots with one point per concept.
  What each figure shows and the conventions shared by all plots (model
  order, colours, asterisks, null intervals, axes) are in section 7 of
  [`statistics.md`](docs/reference/statistics.md).
