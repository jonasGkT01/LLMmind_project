# LLMmind

> *Written with AI assistance (Claude Code). See the [AI attribution](#ai-attribution) note at the end.*

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
   chosen similarity metric (cosine, Pearson or Spearman).
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
config/                     Snakemake configuration (config.yaml)
workflow/
  Snakefile                 Top-level Snakefile: wires up all modules and the `all` rule
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
  one representative brain-response vector per concept. ISC is leave-one-out
  (each observation against the mean of the others) and is averaged per
  parcel. A parcel whose time series is (near-)constant gets an ISC of 0:
  its range over time must be at most about 1e-6 of its magnitude
  (`is_constant_signal()` in `libraries/fmri_processing.py`). This is a
  small tolerance, not an exact test, so a real but tiny fluctuation is
  zeroed too.
- cleans/prepares the matching stimuli (transcripts for the language
  datasets, images for the vision datasets) so they line up 1:1 with the ISC
  output and can be fed to the model embedding step

Because the four raw datasets are organised very differently, most of the
module-specific logic is manifest-building: matching scan files to
stimuli/concepts and excluding unusable subjects/runs/stimuli before the
shared parcel-extraction/ISC rules run.

Every dataset applies the same final inclusion rule: a stimulus is kept only
if it was presented to at least `minimum_subjects_per_stimulus` different
subjects (set at the top of `config.yaml`, default 2). Nature Stories is
stricter: it requires every subject for every story. Each stimulus that
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
similarity (cosine, Pearson or Spearman), and builds the brain-side
nearest-neighbour graphs.

### `llm_nearest_neighbours/`

Downloads each configured pretrained model (`download_pretrained_llm`),
extracts its embeddings for the same stimuli, computes embedding-embedding
similarity (cosine, Pearson or Spearman), and builds the model-side
nearest-neighbour graphs.

Text stimuli longer than one chunk are split into overlapping
token chunks (`--chunk_overlap`, default 256 tokens). The stimulus embedding
is the mean of the chunk embeddings, weighted by chunk length, so tokens in
an overlap contribute to two chunks. Every text stimulus goes through this
path, whatever its length. Chunking stops at the first chunk that reaches
the end of the text, so a text that fits in one chunk gets exactly one.
Each embeddings file records `n_tokens` and `n_chunks` per stimulus.

**Chunk length: `max_chunk_length` in `config/config.yaml`.** This one
top-level key sets the chunk length for every language model. Its value
decides whether `get_embeddings` passes `--chunk_max_length` to
`get_embeddings.py` at all:

| `max_chunk_length` | What `get_embeddings.py` receives | Chunk length used |
|---|---|---|
| an integer, e.g. `2048` (default) | `--chunk_max_length 2048` | exactly that value, for **every** language model |
| `null`, `"none"`, `"null"`, `""`, or the key left out | **no** `--chunk_max_length` argument | inferred per model by `get_safe_max_length()`: the smaller of the tokenizer's `model_max_length` and the config's `max_position_embeddings`, ignoring values above 100,000 and falling back to 2048 when none are left |

> **Watch out:** with `null`/`"none"`, the chunk length is **not the same
> across models**. Gemma 1/2 get 8192 (their `max_position_embeddings`),
> BLOOM and OpenLLaMA 2048, and Gemma 3/3n/4 fall back to 2048 because
> their context lengths exceed 100,000. Since chunk length changes the
> embeddings, models are then compared under different conditions. Longer
> chunks also need much more GPU memory. At 8192 tokens, gemma2_27b runs out
> of memory on node5's 24 GB GPU (see [Troubleshooting](#troubleshooting)).
> Use `null` only if you want each model's native context on purpose.

The setting applies only to `language` models. Vision models never receive
`--chunk_max_length`, because images are not chunked. The value is
recorded per stimulus in the `chunk_max_length` column of each embeddings
file. Changing it reruns every language model's `get_embeddings` job and
everything downstream.

Image stimuli are embedded by `vision` encoders (ViT, CLIP, DINOv2), which
take their first (CLS) token (`--pool` overrides this).

### `llm_mind_alignment/`

Scores brain-model alignment as the overlap between the brain and model
nearest-neighbour graphs, with empirical (permutation-based) and
hypergeometric significance testing.

### `llm_llm_alignment/`

Scores model-model alignment — how similar two models' representational
geometries are to each other — with the same tests as `llm_mind_alignment/`:
a per-concept empirical and hypergeometric p-value, and a model-pair-level
empirical p-value. The second model of each pair is relabelled against the
first, as the model is relabelled against the brain there. The rules reuse the
`llm_mind_alignment/` p-value scripts and the shared `libraries/` modules.

Pairs are formed between *(model, stimulus type)* entries, so on a dataset
with both text and image stimuli a language model is also compared with a
vision model (for example `bloom_560m-language` vs `clip_b-vision`).

### `spearman_alignment/`

A complementary alignment metric using Spearman rank-correlation instead of
nearest-neighbour overlap, computed at both model- and concept-level, again
with empirical significance testing. It runs once per similarity type, so with
`similarity_type=spearman` it is a Spearman correlation between two Spearman
similarity structures: the first one compares stimuli, the second compares the
brain and model similarity structures.

### `visualisation/`

Produces the summary plots described under [Outputs](#outputs): alignment
heatmaps, p-value heatmaps, per-concept alignment scatterplots, line plots,
alignment-enrichment plots (model- and concept-level), and Spearman plots.

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
least `minimum_subjects_per_stimulus` different subjects; every presentation (including repeats by the
same subject) then counts as one fMRI observation in its ISC. Stimuli that
fail this or any other dataset-specific check are listed in that dataset's
`excluded_stimuli` file, which both the ISC side and the model-embedding
side read, so the two always cover the same stimuli. The value must be at
least 2 (ISC needs two observations) and at most 8 (the number of subjects
in `caption_scene` and `nsd_data`). In `narratives` it drops a story only
from 15 upwards, and `nature_stories` ignores it. Changing it rebuilds that
dataset's brain inputs *and* its model embeddings. See
[Running the pipeline](#running-the-pipeline) to preview the effect. For `nsd_data` and
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

## Models

Supported models are declared under `models:` in `config/config.yaml`, each
with a Hugging Face identifier, modality (`language` or `vision`), optional
quantization method, and parameter count. Currently configured: the BLOOMZ,
OpenLLaMA, and Gemma (Gemma, Gemma 2, Gemma 3, Gemma 3n, Gemma 4) language
model families; CLIP, DINOv2, and ImageNet-21K ViT vision model families.
Models are downloaded on demand by the `llm_nearest_neighbours` module.

A model runs on the stimulus type of a dataset that matches its modality:
`language` models on text, `vision` models on images. Every output file
names a model together with its stimulus type, as `<model>-<stimuli_type>`
(for example `clip_b-vision`). Plots show only the model name, coloured by
stimulus type (see "Conventions shared by all plots" under "Outputs").

Multimodal models are not supported. Gemma 3n and Gemma 4 can read images,
but their processor requires a text prompt with an image placeholder token,
and the pipeline passes images alone. They are therefore configured as
`modality: "language"` and embedded from text only.

Mixture-of-experts (MoE) models are not supported on node5's 24 GB GPU.
In Transformers, their experts are stored as fused `nn.Parameter` tensors
rather than `nn.Linear` layers, and bitsandbytes quantizes only
`nn.Linear`. The experts therefore stay in bf16 whatever
`quantization_method` says. Gemma 4 26B A4B (`gemma4_26ba4b`) is commented
out in `config/config.yaml` for this reason: about 22.8B of its 25B
parameters are experts (~46 GB in bf16). Loading fails with `ValueError:
Some modules are dispatched on the CPU or the disk`. Before adding a model,
check its `config.json` for `num_experts`, `num_local_experts` or
`enable_moe_block`.

To add a model, add its block to `config/config.yaml` and rerun the
pipeline. Snakemake runs only the jobs that involve
the new model: its embeddings, its alignment with the brain and with every
other model. It then rebuilds the summary tables and plots. To list the rules
that would run before starting them:

```bash
snakemake --use-conda --cores <N> -n --quiet rules
```

## Setup

The project uses conda environments managed per pipeline stage under
`workflow/*/envs/*.yaml`, plus a base environment for running Snakemake
itself at `workflow/envs/LLMmind_project`, specified by
`workflow/envs/LLMmind_project_environment.yaml` (just Python and the full
`snakemake` package, which brings in pandas and numpy).

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

### Pinned versions

Every package listed in an environment file is pinned to an exact version
(`- numpy=2.5.3`; pip packages as `netneurotools==0.3.0`, and `nsdcode` at a
fixed git commit), so a rebuilt environment gets the same versions. Packages
that are not listed (dependencies of dependencies) are not pinned and can
still move. The versions were chosen on 2026-10-01 as the latest available
release of each package, with Python 3.14.7 in every environment. The
base environment pins `snakemake=9.27.0`, which requires `pandas <3`, so it
has pandas 2.x while the rule environments use pandas 3.
`llm_nearest_neighbours` also lists `cuda-cudart-dev`: it provides `cuda.h`,
which triton needs to compile a small CUDA helper the first time PyTorch runs
a triton kernel on the GPU (the Gemma models do). Without it, a freshly built
environment crashes there.

To upgrade a package:

1. Find the latest version on the environment's channels, e.g.
   `mamba search -c conda-forge <package>` (`-c bioconda` for snakemake).
2. For a new major or minor release, read its release notes and search the
   code for the APIs it changes.
3. Edit the pin. If another package caps it (e.g. `pandas <3`), use the
   highest version the cap allows, and write the cap in a comment next to
   the pin.
4. Changing an environment file makes Snakemake rebuild that environment and
   rerun every job that uses it. Before that, run one representative job in
   the new environment and compare its outputs with the current results.

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
snakemake --use-conda --cores <N> results/all_model_brain_alignment_scores.tsv

# preview what a config change would rebuild, without editing config.yaml;
# the rerun triggers leave out conda-env changes, so only the setting's own effect is listed
snakemake --use-conda --cores <N> -n --quiet rules \
    --rerun-triggers mtime params input code \
    --config minimum_subjects_per_stimulus=3

# run only some of the similarity metrics (here: skip Spearman) for this run,
# without editing config.yaml
snakemake --use-conda --cores <N> --config 'similarity_types=["cosine","pearson"]'

# redraw every plot after the plotting code changed: the scripts run from shell
# rules and are not declared inputs, so Snakemake does not notice edits to them
# (or to the workflow/libraries/ modules they import) on its own
snakemake --use-conda --cores <N> --rerun-triggers mtime \
    --forcerun plot_brain_model_alignment_lineplot plot_concept_alignment_scatterplot \
               plot_brain_model_alignment_enrichment_lineplot \
               plot_concept_alignment_enrichment_scatterplot plot_spearman_alignment \
               plot_alignment_heatmap plot_empirical_p_value_heatmap
```

The similarity metrics are listed under `similarity_types` in
`config/config.yaml`: `cosine` (angle between two vectors), `pearson` (linear
correlation of their values) and `spearman` (correlation of the ranks of their
values, so only the order of the values counts). Every analysis and plot is
produced once per listed metric.

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
The Caption Scene T1w-to-MNI registration (`register_caption_scene_t1w`, one job per subject,
about 2 min each) uses 8 threads (`threads: 8`).
The two summary-table steps (`aggregate_all_p_value_outputs` and
`aggregate_all_llm_llm_p_value_outputs`) each use 4 worker processes (`threads: 4`), so they
need `--cores 4` or more to run at full speed.

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
- **A rule fails with `exit status 126` and `message: None`**: usually
  the command line was longer than Linux allows (`getconf ARG_MAX`, 2 MB
  on frontend and node5), so the program never started ("Argument list
  too long"). This happens when a rule passes thousands of input paths.
  Pass them through an argument file instead, as
  `aggregate_all_llm_llm_p_value_outputs` does: write them one per line
  with the `printf '%s\n'` builtin, call the script with `@file`, and give
  its `argparse.ArgumentParser` `fromfile_prefix_chars = "@"`.
- **`get_embeddings` crashes on a large language model (GPU out of
  memory)**: the attention memory grows with the square of the chunk
  length. With 8192-token chunks, gemma2_27b (4-bit) needs more than the
  24 GB of node5's GPU: Gemma 2 must use eager attention, and one fp32
  attention matrix is about 8.6 GB per layer. Keep `max_chunk_length` at
  2048 (see [`llm_nearest_neighbours/`](#llm_nearest_neighbours)). Don't
  switch such a model from 4-bit to 8-bit: that shrinks only the weights,
  and 27B parameters at 8-bit (~27 GB) don't fit on the GPU at all.
  If loading fails with `ValueError: Some modules are dispatched on the CPU
  or the disk`, the quantized model doesn't fit even before any text is
  read. For mixture-of-experts models this is expected (see
  [Models](#models)).
- **A long rerun after adding a similarity metric**: the nearest-neighbour
  rules (`compute_llm_nearest_neighbours`, `compute_isc_nearest_neighbours`)
  write one file per metric in a single job. Adding a metric to
  `similarity_types` therefore reruns them and rewrites the existing metrics'
  files as well, and everything downstream of those files reruns too, even
  with `--rerun-triggers mtime`. Preview the size with `-n --quiet rules`
  first. Adding `spearman` (2026-09-28) plans about 11,900 jobs.
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
  read and can be deleted. Since 2026-10-02 the same holds for
  `results/mind/caption_scene/intermediate_files/single_stimulus_bold/` (about
  121 GB of cropped Caption Scene volumes, now warped and cut in memory) and
  for the old copy of `csd_events_manifest.tsv` in
  `results/mind/caption_scene/intermediate_files/manifest/` (the manifest now
  lives in `results/mind/caption_scene/manifests/`).
- **Results don't change after editing a dataset's inclusion rules**: the
  manifest scripts are called from `shell:` rules, so Snakemake doesn't
  notice when their code changes. After changing them, force the manifest
  step and let everything downstream rebuild, e.g.
  `snakemake --use-conda --cores <N> --forcerun make_nsd_manifest make_caption_scene_manifest`.
  If you skip this step, `create_isc_manifest` can stop with
  `FileNotFoundError: N of M eligible stimuli have no ISC file`. That error
  means the dataset's `excluded_stimuli` file is older than its ISC outputs,
  and the same forced rerun fixes it.
  The same applies to the embedding and ISC code, including the shared
  `libraries/` modules. After the 2026-09-23 chunking and constant-signal
  fixes, for example, rerun
  `--forcerun get_embeddings compute_narratives_isc compute_nature_stories_isc`.
- **`MissingOutputException` in `compute_narratives_isc` after lowering
  `minimum_subjects_per_stimulus`**: this only happens once the value is
  15 or more. The Narratives parcel and ISC manifests are `run:` rules
  without params, so Snakemake doesn't rebuild them when a story comes back
  into the analysis. Add `--forcerun write_narratives_parcel_manifest`.
  Raising the value doesn't need this: the stale manifests only cost extra
  compute.
- **A rule fails with only `CalledProcessError … returned non-zero exit
  status 1`**: the Snakemake log doesn't include the script's own error
  message. Copy the rule's `shell:` command from the log and re-run it
  inside the conda env the log names:
  `source /opt/conda/miniconda3/bin/activate .snakemake/conda/<hash>_`, then
  `export PYTHONPATH="$PWD/workflow:$PYTHONPATH"`. That prints the full
  Python traceback. For a quicker test, lower `--number_of_relabellings`
  and point the output at a scratch path. After fixing the problem, restart
  with `--rerun-incomplete`, so that the half-written outputs left by the
  crash are rebuilt. Rule envs don't pin library versions, so a rebuilt env
  can pull in a new major version. pandas 3, for example, broke
  `groupby(...).agg(list)` on the categorical neighbour columns (fixed
  2026-09-23).
- **`plot_spearman_alignment` stops with a missing
  `empirical_null_standard_deviation_spearman_coefficient` column**: the
  model-level Spearman TSVs predate the null SD column added on 2026-09-24
  (drawn as the grey null interval). Rebuild them
  once with
  `snakemake --use-conda --cores <N> --forcerun compute_spearman_alignmentwith_empirical_p_value`.
- **Nothing under `results/spearman_alignment/`**: since 2026-09-25 the
  Spearman tables sit in `results/spearman_alignment_scores/` and the plots
  in `results/pictures/` (see [Outputs](#outputs)). Point any script that
  still reads the old folder there.
- **Plot folders directly under `results/`** (for example
  `results/alignment_heatmaps/`): these are left over from before plots moved
  to `results/pictures/` on 2026-09-25. Move them into `results/pictures/`
  to keep the existing plots without redrawing them, or delete them.
- **"Requested k neighbours, but only n candidates"**: a dataset's
  `number_of_neighbours` must be smaller than its number of included
  stimuli (about 1,000 for `nsd_data` and `caption_scene`).

## Outputs

Key outputs land under `results/`. Per-configuration files carry the
similarity metric (`cosine`, `pearson` or `spearman`) in their name; the
combined summary tables have a `similarity_type` column instead.

- `results/alignment_scores/` — per-(dataset, model, similarity, k) alignment
  scores and significance tests. Brain-model and model-model results both get
  a per-concept empirical and hypergeometric p-value plus a model-level
  (model-pair-level) empirical p-value, built with the same random-shuffling
  method. The shuffled scores are kept as one compact all-k file per
  configuration in `relabelled_common_neighbours/`: the shuffled number of
  common neighbours for every relabelling, concept and k (the alignment score
  is that number divided by k). Consumers read the k they need from it.
- `results/spearman_alignment_scores/` — per-(dataset, model, similarity)
  Spearman alignment with its empirical p-value, one `_model_level` and one
  `_concept_level` TSV per configuration.
- `results/all_model_brain_alignment_scores.tsv`, `results/all_spearman_alignment_scores.tsv`
  — combined summary tables across all configurations
- `results/mind/all_isc_reliability.tsv` — one row per dataset: how reliable the per-stimulus
  ISC vectors (the brain representations) are, as the median and interquartile range of their
  split-half reliability (`config.yaml`: `isc_reliability_number_of_splits` random splits of the
  subjects) and its Spearman-Brown correction, plus the median |ISC| and the share of |ISC| ≥ 0.9.
  The per-stimulus values are in `results/mind/{dataset}/isc_reliability.tsv`. See
  [`fmri_preprocessing.md`](docs/reference/fmri_preprocessing.md), step 7.
- `results/all_model_model_alignment_scores.tsv` — the model-model
  counterpart of `all_model_brain_alignment_scores.tsv`, in the same long format and with
  the same statistics. The `model`/`stimuli_type` pair is replaced by one
  column per side: `dataset | similarity_type | number_of_neighbours |
  model_1 | stimuli_type_1 | model_2 | stimuli_type_2 | statistic | value`.
  Each pair appears once, with `model_1` earlier than `model_2` in the
  `models:` order of `config/config.yaml`. The p-values are not corrected
  for multiple testing in the TSV. The p-value heatmap corrects them as their
  own Benjamini-Hochberg family, separate from the brain-model family (see
  the [statistics reference](docs/reference/2026-10-02_0925_statistics.md)).
  The six `*_p_value_across_concepts` statistics in both summary TSVs are
  descriptive summaries of the per-concept p-values, not tests; the
  model-level test is `model_level_empirical_p_value`.
- `results/pictures/` — every plot and heatmap, one subfolder per plot type:
  `alignment_heatmaps/`, `alignment_p_value_heatmaps/`,
  `alignment_lineplots/`, `concept_alignment_scatterplots/`,
  `alignment_enrichment_lineplots/`,
  `concept_alignment_enrichment_scatterplots/`,
  `spearman_alignment_lineplots/`,
  `concept_spearman_alignment_scatterplots/`. In the
  concept-level alignment and Spearman boxplots, a model whose per-concept
  scores show no spread renders as a flat, easy-to-miss box; those are
  marked with a black diamond rather than left looking like missing data.
  The model-level line plots and concept-level scatterplots for a given
  dataset/similarity/k share the same y-axis range (scores on `[0, 1]`, with
  empty space above 1 for the legend), so the two can be compared directly
  side by side. Both draw the hypergeometric null expectation k/(n−1)
  (k neighbours, n concepts) as a grey dashed line, so a model or concept
  above it aligns better than chance.

  Conventions shared by all plots:

  - Titles read `<level> <quantity>` (for example "Model-level brain-model
    alignment enrichment"), with `dataset: …, similarity: …, neighbours: …`
    on the second line. Y-axis labels read `<quantity> ± <error>`, or just
    `<quantity>` when the plot has no error bars. Both come from constants
    in `libraries/visualisation_utils.py`.
  - The legend sits inside the plot, in its top-left corner. The top quarter
    of every plot's y-range is left empty so the legend never hides data.
    The heatmaps are the exception: their only legend (the stimulus-type
    colours) sits in the figure's bottom-left corner.
  - Models appear in the same order in every plot: model family
    (alphabetical), then number of parameters (each model's `parameters_millions` in
    `config/config.yaml`), then model name, then stimulus type. The order of
    the `models:` block in the config does not matter. In the heatmaps the
    brain comes after all models. The rule is `model_sort_key()` in
    `libraries/manage_model_metadata.py`.
  - Every non-heatmap plot draws dashed vertical lines between model
    families.
  - Brain-model plots (not heatmaps) mark each model's model-level
    significance with two rows of asterisks just below the x-axis, above
    the model name: black for the empirical p-value, blue below it for the
    Benjamini-Hochberg q-value (`*` < 0.05, `**` < 0.01, `***` < 0.001).
    The p-value heatmap writes the q-value asterisks in each cell; its
    brain cells use the same family as the brain-model plots, so the
    asterisks agree, and its model-model cells form a family of their own.
  - The heatmaps leave the diagonal (each model or the brain with itself)
    blank: those cells are 1 by definition, not computed scores.
  - Error bars only show the uncertainty of the plotted value (the standard
    error in the model-level alignment line plot). The spread of a null
    distribution is drawn as a grey "Null ± 1 SD" interval on the reference
    line, where the null is centred, not around the observed point.
  - Model names show the model only (for example `clip_b`, not
    `clip_b-vision`) and are coloured by stimulus
    type: dark orange (`#A84800`) for language, dark green (`#007A5A`) for
    vision. The brain stays black. This applies to both axes of the heatmaps.
    In the model-level line plots, the points also take the colour, as
    circles (language) or squares (vision). Boxes are not coloured. The
    colours are set in `STIMULI_TYPE_COLOURS` in
    `libraries/visualisation_utils.py`.
  - Concept-level plots colour each concept the same way for every model in
    the plot. Concept names are never listed in the legend.
  - Colour-vision deficiency: the stimulus-type pair was checked with a
    colour-blindness simulation (protan, deutan, tritan) and passes, with
    ≥ 5:1 contrast on white. The heatmaps use `viridis`. Red is avoided for
    the q-value asterisks and the degenerate-box marker. The per-concept
    colours are the exception: with 11 to 1,000 concepts, no palette keeps
    them distinguishable for colourblind readers.

  The enrichment plots divide the observed alignment score by the expected
  one, taken as the mean relabelled score of that model (over every
  relabelling and concept). A dashed line marks enrichment = 1. The
  model-level plot draws, at each model, a grey interval of 1 ± the SD of
  that model's relabelling null in the same units; the observed points have
  no error bars. The concept-level plot shows no null interval, to stay
  readable. The
  concept-level plot uses the same expected score as the model-level one,
  so the model-level enrichment is the mean of the concept-level ones.
  Both plots for a given dataset/similarity/k share one y-axis range,
  computed from both (`enrichment_ylim()` in
  `libraries/compute_alignment_enrichment.py`), which fits every concept,
  every model-level value and every null interval. The y-axis is linear from 0 to 1 and log10
  above 1 (matplotlib `symlog`, set by `set_enrichment_y_scale()`), and
  [0, 1] is as tall as one decade. This way a few very high concepts don't
  squash the rest, and every point is still drawn. The model-level Spearman
  plot likewise draws a grey interval of 0 ± the SD of each model's
  permutation null (`empirical_null_standard_deviation_spearman_coefficient`);
  the concept-level Spearman plot has none. The statistics behind all plots
  (null distributions, p-values, Benjamini-Hochberg families) are described
  in the [statistics reference](docs/reference/2026-10-02_0925_statistics.md).

## Code conventions

All code under `workflow/`, the Snakefiles, `config/config.yaml` and `parquet2tsv.sh` follow the
layout rules in section 4 of `LLMmind/.claude/CLAUDE.md` (applied to the whole project on
2026-10-02). The main points:

- **Python:** 4-space indentation, code lines of at most 88 characters (long strings are split
  into adjacent literals; comments and `argparse` calls may be longer), one blank line between
  top-level functions, spaces around `=` (also in keyword arguments and defaults), `+`, `-` and
  comparisons, no spaces around `*` and `/`, and one space after every comma, including a comma
  that ends a line. Long calls use a 4-space hanging indent with one argument per line;
  `argparse` arguments put each keyword on its own line, aligned with the opening parenthesis.
- **Imports** come in three groups separated by one blank line: standard library, third-party,
  then the project's own `libraries.*`.
- **Comments** go on the line above the code, in lowercase and the imperative, with no final
  full stop. Triple-quoted strings are kept for docstrings only.
- **Snakefiles:** every input and output is named; `shell:` blocks are `r"""` strings with the
  command at 12 spaces and each `--flag {value}` on its own line at 16. The main `Snakefile`
  defines its helpers before the `include:` lines, because the included Snakefiles use them.
- **Bash:** `#!/usr/bin/env bash`, `set -euo pipefail`, `[[ ... ]]` tests and quoted variables.

Example import block:

```python
import argparse
from pathlib import Path

import nibabel as nib
from nilearn import datasets, image
import numpy as np
import pandas as pd

from libraries.fmri_processing import compute_leave_one_out_isc
```

These rules are not enforced by a linter. Please follow them by hand when adding or editing
code.

## Documentation

- [`docs/reference/fmri_preprocessing.md`](docs/reference/fmri_preprocessing.md)
  — what each dataset's authors did to the BOLD data before this workflow, and
  what the workflow itself does (a source for the methods section)
- [`docs/reference/2026-10-02_0925_statistics.md`](docs/reference/2026-10-02_0925_statistics.md)
  — alignment scores, the relabelling and Spearman nulls, the empirical and
  hypergeometric tests, enrichment, the Benjamini-Hochberg families and what
  every figure's points, error bars and grey intervals show (a source for
  the methods section)
- [`docs/reference/model_embeddings.md`](docs/reference/model_embeddings.md)
  — how each model turns a stimulus into one vector: chunking, pooling
  (including the BOS token) and the CLS token of vision models (a source for
  the methods section)
- [`docs/reference/2026-10-01_0926_clean_run_duration.md`](docs/reference/2026-10-01_0926_clean_run_duration.md)
  — how long a clean run takes on node5 (about 25 h), with the per-job and
  total time of every rule
- [`docs/changelog/developers/`](docs/changelog/developers/) — technical
  changelog entries for contributors
- [`docs/changelog/users/`](docs/changelog/users/) — plain-language changelog
  entries describing what changed for anyone running the pipeline

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Sonnet 5 (`claude-sonnet-5`, until 2026-09-22); Claude Opus 5.5 (`claude-opus-5-5`, from 2026-09-23).*
- *Latest AI edit: 2026-10-02, Claude Opus 5.5: documented the ISC reliability table (TODO S30), after the developer asked to proceed with S30.*
- *Edit history: see [`docs/changelog/`](docs/changelog/).*
- *Review status: not yet reviewed by the developer.*
