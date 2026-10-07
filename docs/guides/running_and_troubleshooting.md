# Running the pipeline and troubleshooting

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../AI_USAGE.md).*

This guide covers what you need once the pipeline is set up (see the [README](../../README.md)):
how to run parts of it, when Snakemake reruns a job, the settings that change many results, the
software environments, and what to do when a run fails. How the results are computed is described
in the [reference pages](../../README.md#documentation).

## 1. Running

From the project root, with the base environment active:

```bash
snakemake --use-conda --cores <N>
```

On node5, the usual command is `snakemake --use-conda --cores 4 --resources gpu=1`
(`resources: gpu=1` makes the embedding jobs run one at a time on the GPU).

Useful variations:

```bash
# dry run to see what would be executed
snakemake --use-conda --cores <N> -n

# list only the rules that would run, with their job counts
snakemake --use-conda --cores <N> -n --quiet rules

# build a specific target only, e.g. the brain-model summary table
snakemake --use-conda --cores <N> results/all_model_brain_alignment_scores.tsv

# preview what a config change would rebuild, without editing config.yaml;
# the rerun triggers leave out conda-env changes, so only the setting's own effect is listed
snakemake --use-conda --cores <N> -n --quiet rules \
    --rerun-triggers mtime params input code \
    --config minimum_subjects_per_stimulus=3

# run only some of the similarity metrics (here: skip Spearman) for this run,
# without editing config.yaml
snakemake --use-conda --cores <N> --config 'similarity_types=["cosine","pearson"]'

# redraw every plot after the plotting code changed (see section 2)
snakemake --use-conda --cores <N> --rerun-triggers mtime \
    --forcerun plot_brain_model_alignment_lineplot plot_concept_alignment_scatterplot \
               plot_brain_model_alignment_enrichment_lineplot \
               plot_concept_alignment_enrichment_scatterplot plot_spearman_alignment \
               plot_alignment_heatmap plot_empirical_p_value_heatmap
```

A clean run of everything takes about 32 h on node5; see
[`clean_run_duration.md`](../reference/clean_run_duration.md).

**Parallelism.** No rule declares `threads:`, so Snakemake counts every job as one core and
`--cores <N>` runs up to `<N>` jobs at once. A few steps also parallelize internally, with
`number_of_workers` worker processes or threads (`config/config.yaml`, default 4): NSD's
functional-to-MNI registration (`assemble_nsd_bold`), the Caption Scene T1w-to-MNI registration
(`register_caption_scene_t1w`, one job per subject, about 2 min each) and the two summary-table
steps (`aggregate_all_p_value_outputs` and `aggregate_all_llm_llm_p_value_outputs`). Snakemake
does not reserve cores for these workers, so these steps never wait for free cores, but while one
runs alongside other jobs the run briefly uses more CPUs than `--cores`. Lower
`number_of_workers` if that is a problem.

## 2. When Snakemake reruns a job

Snakemake reruns a job when its inputs, params or the rule's own code change. It does not see
edits to a Python script called from `shell:`, or to a helper function defined outside a rule's
`run:` block.

**Covered by `code_version()`.** These rules have a `code` param, `code_version(...)`
(`workflow/libraries/code_version.py`), that holds a hash of their helper functions, or of their
script and the `workflow/libraries/` modules it imports. Editing that code reruns the rule and
everything downstream of it (comments and blank lines do not count):

- the dataset manifests: `make_nsd_manifest`, `make_caption_scene_manifest`,
  `write_narratives_parcel_manifest`, `write_narratives_isc_manifest`,
  `write_nature_stories_parcel_manifest`, `write_nature_stories_isc_manifest`,
  `write_nsd_parcel_manifest`, `write_nsd_isc_manifest`, `write_caption_scene_isc_manifest`;
- the summary tables: `aggregate_all_p_value_outputs`, `aggregate_all_llm_llm_p_value_outputs`,
  `aggregate_all_spearman_alignment_scores`, `aggregate_isc_reliability`.

This relies on the `params` rerun trigger, so a run with `--rerun-triggers mtime` misses such
edits.

**Not covered.** For every other rule, force the rerun yourself with `--forcerun <rule>` after
changing its code. This includes:

- the plots (see the command in section 1);
- the embedding and ISC code, including the shared `libraries/` modules, for example
  `--forcerun get_embeddings compute_narratives_isc compute_nature_stories_isc`;
- `create_isc_manifest`, `write_narratives_problematic_stimuli` and
  `write_nature_stories_excluded_stimuli` (the last two write the excluded-stimuli lists);
- the data the `write_*_manifest` rules are written from. Their hash covers the functions' code,
  not the values those functions read from `config/config.yaml` or from files such as
  `scan_exclude.json`, so a change there does not rebuild them (see the Narratives entry in
  section 6).

## 3. Settings that change many results

**`similarity_types`** lists the similarity metrics: `cosine` (angle between two vectors),
`pearson` (linear correlation of their values) and `spearman` (correlation of the ranks of their
values, so only the order counts). Every analysis and plot is produced once per listed metric.
Adding a metric reruns the nearest-neighbour rules (`compute_llm_nearest_neighbours`,
`compute_isc_nearest_neighbours`), which write one file per metric in a single job. The existing
metrics' files are rewritten too, and everything downstream of them reruns, even with
`--rerun-triggers mtime`. Adding `spearman` planned about 11,900 jobs.

**`minimum_subjects_per_stimulus`** (default 2) keeps a stimulus only if at least that many
different subjects saw it. It must be at least 2 (ISC needs two observations) and at most 8 (the
number of subjects in `caption_scene` and `nsd_data`). In `narratives` it drops a story only from
15 upwards, and `nature_stories` ignores it (it requires every subject for every story). Changing it
rebuilds that dataset's brain inputs *and* its model embeddings; preview the effect with the
`--config` dry run of section 1. With the default, `nsd_data` and `caption_scene` keep about 1,000
stimuli each, so their `number_of_neighbours` values must stay below that.

**`max_chunk_length`** sets the chunk length, in tokens, for every language model. Its value
decides whether `get_embeddings` passes `--chunk_max_length` to `get_embeddings.py` at all:

| `max_chunk_length` | What `get_embeddings.py` receives | Chunk length used |
|---|---|---|
| an integer, e.g. `2048` (default) | `--chunk_max_length 2048` | exactly that value, for **every** language model |
| `null`, `"none"`, `"null"`, `""`, or the key left out | **no** `--chunk_max_length` argument | inferred per model by `get_safe_max_length()`: the smaller of the tokenizer's `model_max_length` and the config's `max_position_embeddings`, ignoring values above 100,000 and falling back to 2048 when none are left |

> **Watch out:** with `null`/`"none"`, the chunk length is **not the same across models**. Gemma
> 1/2 get 8192 (their `max_position_embeddings`), BLOOM and OpenLLaMA 2048, and Gemma 3/3n/4 fall
> back to 2048 because their context lengths exceed 100,000. Since chunk length changes the
> embeddings, models are then compared under different conditions. Longer chunks also need much
> more GPU memory (see section 6). Use `null` only if you want each model's native context on
> purpose.

Vision models never receive `--chunk_max_length`, because images are not chunked. The value is
recorded per stimulus in the `chunk_max_length` column of each embeddings file. Changing it reruns
every language model's `get_embeddings` job and everything downstream. How the chunks are embedded
is described in [`model_embeddings.md`](../reference/model_embeddings.md).

**Adding a model.** Add its block under `models:` in `config/config.yaml` and rerun the pipeline.
Snakemake runs only the jobs that involve the new model (its embeddings, its alignment with the
brain and with every other model), then rebuilds the summary tables and plots. Before adding one,
check the two limitations of section 5.

## 4. Software environments

Every rule declares its own `conda:` environment (`workflow/*/envs/*.yaml`), which Snakemake
creates automatically with `--use-conda`. Every package listed in an environment file is pinned
to an exact version (`- numpy=2.5.3`; pip packages as `netneurotools==0.3.0`, and `nsdcode` at a
fixed git commit), so a rebuilt environment gets the same versions. Packages that are not listed
(dependencies of dependencies) are not pinned and can still move. The versions were chosen on
2026-10-01 as the latest release of each package, with Python 3.14.7 in every environment. The
base environment pins `snakemake=9.27.0`, which requires `pandas <3`, so it has pandas 2.x while
the rule environments use pandas 3. `llm_nearest_neighbours` also lists `cuda-cudart-dev`: it
provides `cuda.h`, which triton needs to compile a small CUDA helper the first time PyTorch runs a
triton kernel on the GPU (the Gemma models do). Without it, a freshly built environment crashes
there.

To upgrade a package:

1. Find the latest version on the environment's channels, e.g.
   `mamba search -c conda-forge <package>` (`-c bioconda` for snakemake).
2. For a new major or minor release, read its release notes and search the code for the APIs it
   changes.
3. Edit the pin. If another package caps it (e.g. `pandas <3`), use the highest version the cap
   allows, and write the cap in a comment next to the pin.
4. Changing an environment file makes Snakemake rebuild that environment and rerun every job that
   uses it. Before that, run one representative job in the new environment and compare its
   outputs with the current results.

**Removing old environments.** Every edit of an environment file creates a new environment under
`.snakemake/conda/` (a folder named after a hash, plus a `.yaml` and a `.env_setup_done` file of
the same name) and leaves the old one on disk. To remove the old ones:

1. List the environments in use: `snakemake --list-conda-envs` (third column, `location`).
2. Delete every other hash-named folder in `.snakemake/conda/`, with its `.yaml` and
   `.env_setup_done` files, naming each one explicitly.

Do not use `snakemake --conda-cleanup-envs` for this: its help text says it removes unused
environments, but in Snakemake 9.27 it deletes the environments the workflow **uses** and keeps
the old ones. If that happens, rebuild them without running any job:

```bash
CONDA_OVERRIDE_CUDA=12.9 snakemake --use-conda --conda-create-envs-only --cores 1
```

`CONDA_OVERRIDE_CUDA=12.9` matters on a machine without a GPU, such as the frontend: without it
conda installs the CPU build of PyTorch in `llm_nearest_neighbours` (no triton, no GPU), under the
same environment folder, so Snakemake does not notice. Check with
`.snakemake/conda/<hash>_/bin/python -c 'import torch; print(torch.version.cuda)'`, which must
print `12.9`.

## 5. Model limitations

**Multimodal models are not supported.** Gemma 3n and Gemma 4 can read images, but their
processor requires a text prompt with an image placeholder token, and the pipeline passes images
alone. They are therefore configured as `modality: "language"` and embedded from text only.

**Mixture-of-experts (MoE) models do not fit on node5's 24 GB GPU.** In Transformers, their
experts are stored as fused `nn.Parameter` tensors rather than `nn.Linear` layers, and
bitsandbytes quantizes only `nn.Linear`, so the experts stay in bf16 whatever
`quantization_method` says. Gemma 4 26B A4B (`gemma4_26ba4b`) is commented out in
`config/config.yaml` for this reason: about 22.8B of its 25B parameters are experts (~46 GB in
bf16). Before adding a model, check its `config.json` for `num_experts`, `num_local_experts` or
`enable_moe_block`.

## 6. Troubleshooting

- **`ProtectedOutputException` / write-protected files under `resources/models/`**: pretrained
  models are downloaded via `huggingface_hub`, which can leave downloaded files (and sometimes
  their directory) read-only. Run `chmod -R u+w resources/models/` and retry. If Snakemake also
  reports that a model's software environment definition has changed since it was downloaded,
  either launch with `--rerun-triggers mtime` to ignore that check, or run
  `snakemake --cleanup-metadata <path>` for the affected outputs if you're confident the
  downloaded weights don't need re-fetching.
- **A rule fails because a manifest has an old layout** (for example
  `Manifest is missing columns: ['subject']`): the manifest was written by an older version of
  the code and was not rebuilt. This happens after a run with `--rerun-triggers mtime`, or for a
  rule not covered by `code_version()` (section 2). Force it with `--forcerun <rule name>`.
- **Results don't change after editing a dataset's inclusion rules**: the manifest rules rerun
  by themselves when their code changes (section 2), but the excluded-stimuli rules of Narratives
  and Nature Stories, and any change to the config values or files the manifests read, do not.
  Force the dataset's manifest and exclusion rules, e.g.
  `--forcerun write_narratives_problematic_stimuli write_narratives_parcel_manifest`. If
  `create_isc_manifest` stops with `FileNotFoundError: N of M eligible stimuli have no ISC file`,
  the dataset's `excluded_stimuli` file is older than its ISC outputs; the same forced rerun fixes
  it.
- **`MissingOutputException` in `compute_narratives_isc` after lowering
  `minimum_subjects_per_stimulus`**: this only happens once the value is 15 or more. The
  Narratives parcel and ISC manifests are written from values read when the workflow is parsed,
  and their `code` param hashes only their code, so Snakemake doesn't rebuild them when a story
  comes back into the analysis. Add `--forcerun write_narratives_parcel_manifest`. Raising the
  value doesn't need this: the stale manifests only cost extra compute.
- **A rule fails with `exit status 126` and `message: None`**: usually the command line was longer
  than Linux allows (`getconf ARG_MAX`, 2 MB on frontend and node5), so the program never started
  ("Argument list too long"). This happens when a rule passes thousands of input paths. Pass them
  through an argument file instead, as `aggregate_all_llm_llm_p_value_outputs` does: write them
  one per line with the `printf '%s\n'` builtin, call the script with `@file`, and give its
  `argparse.ArgumentParser` `fromfile_prefix_chars = "@"`.
- **A rule fails with only `CalledProcessError … returned non-zero exit status 1`**: the Snakemake
  log doesn't include the script's own error message. Copy the rule's `shell:` command from the
  log and re-run it inside the conda env the log names:
  `source /opt/conda/miniconda3/bin/activate .snakemake/conda/<hash>_`, then
  `export PYTHONPATH="$PWD/workflow:$PYTHONPATH"`. That prints the full Python traceback. For a
  quicker test, lower `--number_of_relabellings` and point the output at a scratch path. After
  fixing the problem, restart with `--rerun-incomplete`, so that the half-written outputs left by
  the crash are rebuilt. Unpinned dependencies (section 4) can still change when an environment
  is rebuilt and break code that used to work.
- **`get_embeddings` crashes on a large language model (GPU out of memory)**: the attention memory
  grows with the square of the chunk length. With 8192-token chunks, gemma2_27b (4-bit) needs more
  than the 24 GB of node5's GPU: Gemma 2 must use eager attention, and one fp32 attention matrix
  is about 8.6 GB per layer. Keep `max_chunk_length` at 2048 (section 3). Don't switch such a
  model from 4-bit to 8-bit: that shrinks only the weights, and 27B parameters at 8-bit (~27 GB)
  don't fit on the GPU at all. If loading fails with `ValueError: Some modules are dispatched on
  the CPU or the disk`, the quantized model doesn't fit even before any text is read; for MoE
  models this is expected (section 5).
- **"Requested k neighbours, but only n candidates"**: a dataset's `number_of_neighbours` must be
  smaller than its number of included stimuli (about 1,000 for `nsd_data` and `caption_scene`).

### Leftover outputs from older versions

Results directories written by older versions of the pipeline can contain files that the current
code no longer produces or reads. They are safe to delete:

- `*_similarity.parquet` files, and neighbour files with a `_<k>NN` suffix (the pipeline no
  longer writes full stimulus × stimulus similarity matrices);
- `results/mind/nsd_data/single_stimulus_bold_mni/` (full-brain MNI volumes per NSD
  presentation);
- `results/mind/caption_scene/intermediate_files/single_stimulus_bold/` (about 121 GB of cropped
  Caption Scene volumes, now warped and cut in memory) and the old copy of
  `csd_events_manifest.tsv` in `results/mind/caption_scene/intermediate_files/manifest/` (the
  manifest now lives in `results/mind/caption_scene/manifests/`);
- plot folders directly under `results/` (for example `results/alignment_heatmaps/`): plots now
  live in `results/pictures/`. Move them there to keep the plots without redrawing them, or delete
  them;
- `results/spearman_alignment/`: the Spearman tables now sit in
  `results/spearman_alignment_scores/` and the plots in `results/pictures/`.

If `plot_spearman_alignment` stops with a missing
`empirical_null_standard_deviation_spearman_coefficient` column, the model-level Spearman TSVs
predate that column. Rebuild them once with
`--forcerun compute_spearman_alignmentwith_empirical_p_value`.

## Changes

### 2026-10-06 16:30 — guide created

Created from the "Running the pipeline", "Setup → Pinned versions", "Models" and
"Troubleshooting" parts of `README.md`, when the README was cut down to an overview. Corrected on
the way: the troubleshooting entries still said that the manifest rules don't rerun when their
code changes, which has not been true since the `code_version()` rerun trigger of 2026-10-05; the
list of rules it covers and does not cover is now in section 2. The stale-output notes were
gathered under "Leftover outputs from older versions", without their dates.

### 2026-10-07 09:10 — clean-run duration updated

The clean-run duration quoted in section 1 went from about 29 h to about 32 h, after the node5
runs of 2026-10-05 and 2026-10-06 measured the Caption Scene per-run extraction.

### 2026-10-07 13:55 — warning about `--conda-cleanup-envs`

Section 4 now warns against `snakemake --conda-cleanup-envs`, which in Snakemake 9.27 deletes the
environments in use instead of the unused ones (it did so on 2026-10-07).

### 2026-10-07 14:45 — how to remove old environments

Section 4 now describes how to remove old environments by hand, and how to rebuild the ones in
use (with `CONDA_OVERRIDE_CUDA=12.9`, without which a rebuild on the frontend got the CPU build of
PyTorch); it replaces the warning added earlier the same day.

