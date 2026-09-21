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
  envs/                     Conda environments, one per pipeline stage
resources/
  atlases/                  Brain parcellation atlas used to extract ROI-level signal
  datasets/                 Raw dataset inputs (fMRI + stimuli) — not tracked in git
  models/                   Downloaded pretrained model weights — not tracked in git
results/                    Pipeline outputs — not tracked in git
docs/changelog/             Developer- and user-facing changelogs
```

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
itself at `workflow/envs/LLMmind_project`.

```bash
# create/activate the base environment (see .envrc for the expected path)
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

## Outputs

Key outputs land under `results/`:

- `results/alignment_scores/` — per-(dataset, model, similarity, k) brain-model
  and model-model alignment scores and p-values (empirical + hypergeometric)
- `results/all_alignment_scores.tsv`, `results/all_spearman_alignment_scores.tsv`
  — combined summary tables across all configurations
- `results/alignment_heatmaps/`, `results/alignment_p_value_heatmaps/`,
  `results/alignment_lineplots/`, `results/alignment_enrichment_plots/`,
  `results/spearman_alignment/*_plots/` — summary visualisations

## Documentation

- [`docs/changelog/developers/`](docs/changelog/developers/) — technical
  changelog entries for contributors
- [`docs/changelog/users/`](docs/changelog/users/) — plain-language changelog
  entries describing what changed for anyone running the pipeline
