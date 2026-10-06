# 2026-10-01 — developer changelog

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../../AI_USAGE.md).*

Changes made on this day, in order:

- LLM-LLM aggregation passes its arguments through a file (bugfix)
- `.gitignore` ignores Python bytecode everywhere (refactor)
- Dead `safe_pearsonr()` removed from `fmri_processing.py` (removal)
- Model download works with current `huggingface_hub` (bugfix)
- One shared loader and validator for the four ISC scripts (refactor)
- The Narratives Snakefile no longer writes files at parse time (refactor)
- The ISC rules no longer write NIfTI maps (removal)
- ISC averaging and the model-key naming rule are documented (documentation)
- One shared writer for the LLM and ISC nearest-neighbour files (refactor)
- One model-order rule for every figure (refactor)
- Commented-out rules and targets removed (removal)
- Faster p-value aggregation (both summary TSVs) (optimisation)
- Model tick labels without the stimulus type (new_feature)
- `download_pretrained_llm.py` uses argparse (refactor)
- Pinned conda environments (new_feature)

---

## 09:37 — LLM-LLM aggregation passes its arguments through a file

Kind: `bugfix`

### Problem

`aggregate_all_llm_llm_p_value_outputs` (`workflow/llm_llm_alignment/Snakefile`) put every input
path on the `python3` command line: 11,184 empirical and 11,184 hypergeometric p-value TSVs,
4,038 relabelled all-k parquets and the 38 `--model_order` keys, about 4.0 MB in total. The kernel
limit on the arguments plus environment of one `execve` (`getconf ARG_MAX`) is 2,097,152 bytes on
both frontend and node5. `bash` therefore failed with `E2BIG` ("Argument list too long") and exited
with status 126 before Python started. Snakemake reported only `CalledProcessError ... exit status
126` with `message: None` (run `.snakemake/log/2026-10-01T092014.485984.snakemake.log`). The
argument list grows with the square of the number of models.

### Changes

- `workflow/llm_llm_alignment/scripts/aggregate_all_llm_llm_p_value_outputs.py`, `main()`:
  `argparse.ArgumentParser(...)` gains `fromfile_prefix_chars = "@"`. An argument `@file` expands
  to the lines of `file`, one argument per line (argparse's default
  `convert_arg_line_to_args`). The arguments, their parsing and the output are unchanged; the
  script can still be called with the arguments on the command line.
- Rule `aggregate_all_llm_llm_p_value_outputs`, shell block: the same arguments are written one per
  line to `args_file=$(mktemp)` with the `printf '%s\n'` builtin (a builtin makes no `execve`, so
  `ARG_MAX` does not apply), then the script is run as `python3 ... @"$args_file"` and the file is
  removed. `mktemp` uses `$TMPDIR`, which Snakemake sets from `resources.tmpdir`. If the script
  fails, the ~4 MB file stays in `$TMPDIR`. Inputs, outputs and params are unchanged.

Not changed: `plot_alignment_heatmap` (~703 LLM-LLM paths per heatmap, ~100 KB) and
`plot_empirical_p_value_heatmap` (two TSVs) are far below the limit. Alternatives considered and
rejected: Snakemake's `script:` directive (breaks the standalone-`argparse`-CLI convention) and
globbing the inputs inside the script (would read files Snakemake did not declare).

### Rerun impact

The shell command changed, so Snakemake's code trigger reruns only this rule. Its output,
`results/all_model_model_alignment_scores.tsv`, did not exist yet. A dry run
(`snakemake -n --sdm conda --cores 1 -- results/all_model_model_alignment_scores.tsv`) plans exactly
one job. No numerical result changes.

### Verification

The rendered `printf` command from the dry run wrote a 26,450-line, 4.0 MB argument file. The
script's own parser read it back as 11,184 + 11,184 + 4,038 paths (all existing), 38 model keys
and the output path. The full rule has not yet been run at the time of writing.

### Context

- Basis: the developer asked why the project crashed; the fix is TODO entry S33, approved by the developer on 2026-10-01 and then removed from the TODO file as solved.
- Files changed: `workflow/llm_llm_alignment/Snakefile`, `workflow/llm_llm_alignment/scripts/aggregate_all_llm_llm_p_value_outputs.py`.

---

## 14:59 — `.gitignore` ignores Python bytecode everywhere

Kind: `refactor`

### Change

`.gitignore`: the entry `workflow/libraries/__pycache__/` is replaced by `__pycache__/`, which
matches a `__pycache__/` directory at any depth. Before, running a script outside
`workflow/libraries/` (for example `workflow/visualisation/scripts/`) left an untracked
`__pycache__/` that could be committed by mistake.

No `*.py[cod]` pattern is added: Python 3 writes bytecode only inside `__pycache__/`.
`git ls-files | grep -E '__pycache__|\.pyc$'` printed nothing before the change, so no tracked
file is affected.

No rule or output changes; nothing reruns.

### Context

- Request: Written for TODO entry S5, approved by the developer on 2026-09-30 and confirmed on 2026-10-01 ("start solving the problems that do not involve the aggregation code").
- Files changed: `.gitignore`.

---

## 14:59 — Dead `safe_pearsonr()` removed from `fmri_processing.py`

Kind: `removal`

### Change

`workflow/libraries/fmri_processing.py`:

- `safe_pearsonr()` is deleted. It had no caller since `compute_leave_one_out_isc()` was
  vectorised (see `2026-09-22_new_feature_optimisation.md`).
- `from scipy.stats import pearsonr`, used only by it, is deleted.
- The `compute_leave_one_out_isc()` docstring no longer describes the function by reference to
  `safe_pearsonr()`. It now states what it computes: per parcel, the mean over subjects of the
  Pearson r between each subject's time course and the mean time course of the other subjects,
  with r = 0 for a constant signal.
- `is_constant_signal()` is kept: `compute_leave_one_out_isc()` uses it.

Not done, on purpose: computing the leave-one-out means as `(total − x_i)/(n − 1)`. It saves a
fraction of a second per task, but its different rounding would change the ISC values in their
last bits and force a full downstream recompute.

### Verification

`compute_leave_one_out_isc()` from the old (`HEAD`) and new module returned identical arrays
(`np.array_equal`) on random float32 data of shape 6 × 50 × 200 with one constant parcel.
No shell command changes, so nothing reruns.

### Context

- Request: Written for TODO entry S8, approved by the developer on 2026-09-30 and confirmed on 2026-10-01 ("start solving the problems that do not involve the aggregation code").
- Files changed: `workflow/libraries/fmri_processing.py`.

---

## 14:59 — Model download works with current `huggingface_hub`

Kind: `bugfix`

### Change

`workflow/llm_nearest_neighbours/scripts/download_pretrained_llm.py::download_model_repo()`: the
`local_dir_use_symlinks=False` keyword is removed from the `huggingface_hub.snapshot_download()`
call. The parameter was deprecated and is gone in the installed `huggingface_hub` 1.31.0, which
rejects unknown keyword arguments, so the next download (a new model, or a re-download after an
environment rebuild) would have raised a `TypeError`. With `local_dir` set, current versions write
real files into `local_dir`, which is what the removed argument requested.

The `download_pretrained_llm` rule's shell command and its `directory()` output are unchanged, so
nothing reruns. Existing models in `resources/models/` are untouched.

### Context

- Request: Written for TODO entry S25, approved by the developer on 2026-09-30 and confirmed on 2026-10-01 ("start solving the problems that do not involve the aggregation code").
- Files changed: `workflow/llm_nearest_neighbours/scripts/download_pretrained_llm.py`.

---

## 15:13 — One shared loader and validator for the four ISC scripts

Kind: `refactor`

### Change

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

### Verification

All parcel files are float32 (checked on a sample of every dataset), so the float32 cast is a
no-op for the two scripts that did not cast before. The original scripts (`d3db409`) and the new ones
were run on one item per dataset, with outputs redirected to a scratch directory: Narratives
`merlin` (35 subjects, 613–657 TRs, so truncation is exercised), Caption Scene
`COCO_train2014_000000434623`, Nature Stories `souls` and NSD `nsd-60457`. All four `.npy` and
three `.nii.gz` outputs were byte-identical (`cmp`). The error paths (fewer than 2 files, wrong
shape, unequal lengths, several values in `single_value`) were exercised on small test arrays.

### Context

- Request: Written for TODO entry S6, approved by the developer on 2026-09-30; the implementation plan was approved on 2026-10-01 ("go on with S6, S7, S28, and S32").
- Files changed: `workflow/libraries/fmri_processing.py`, `workflow/dataset_processing/narratives_dataset/scripts/compute_narratives_isc.py`, `workflow/dataset_processing/caption_scene_dataset/scripts/compute_caption_scene_isc.py`, `workflow/dataset_processing/nature_stories_dataset/scripts/compute_nature_stories_isc.py`, `workflow/dataset_processing/nsd_data_dataset/scripts/compute_nsd_isc.py`.

---

## 15:19 — The Narratives Snakefile no longer writes files at parse time

Kind: `refactor`

### Change

`workflow/dataset_processing/narratives_dataset/Snakefile` ran two blocks at module level, i.e. on
every Snakemake command, dry runs and `--list-rules` included:

- **Length check (TODO S28):** `narratives_write_length_check_json()` wrote
  `results/mind/narratives/qc/task-*_length_check.json` (18 files) for every valid task. No rule
  declared them and nothing read them. Deleted: the function, its module-level call, the
  commented-out variants, and `import numpy as np`, which only it used (`json` and `Path` are still
  used). The useful part, which files are truncated and from which length, is now printed into the
  `compute_narratives_isc` job log by `compute_isc_from_files(..., truncate_to_shortest = True)`
  (see `2026-10-01_new_feature_bugfix_optimisation_refactor_removal_documentation.md`).
- **Excluded-scans JSON (TODO S32):** a loop collected the 44 scans of tasks outside
  `VALID_NARRATIVES_TASKS` with a reason and wrote them to
  `config["narratives"]["excluded_scans_for_task"]`, a file in `resources/`. Nothing read it, and
  its content follows from `config.yaml` (`tasks`, `schema_subtasks`, `notthefall_variants`).
  Deleted: the loop, the write and the `excluded_scans_for_task` key in `config/config.yaml`.
  `excluded_stimuli.txt`, which `get_embeddings.py` reads, is built by its own rule and is unchanged.

The existing files (`results/mind/narratives/qc/`, `resources/datasets/narratives_dataset/excluded_scans_for_task.json`)
are deleted when this change is merged into `main`. No rule changes, so nothing reruns.

`docs/reference/fmri_preprocessing.md`, step 5, now states why truncating Narratives to the shortest
run is safe.

### Verification

A dry run (`snakemake -n --quiet rules`) of the changed workflow parsed without errors, planned no
ISC or relabelling job, and left the modification times of both JSON files unchanged.

### Context

- Request: Written for TODO entries S28 and S32, approved by the developer on 2026-09-30; the implementation plan was approved on 2026-10-01 ("go on with S6, S7, S28, and S32").
- Files changed: `workflow/dataset_processing/narratives_dataset/Snakefile`, `config/config.yaml`, `docs/reference/fmri_preprocessing.md`.

---

## 15:25 — The ISC rules no longer write NIfTI maps

Kind: `removal`

### Change

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

### Rerun cost and merge plan

The ISC values do not change, but the three ISC rules' shell commands and params change, so
Snakemake reruns them and everything downstream: a dry run on 2026-10-01 listed 3,745 jobs,
including all relabelling jobs. This commit is therefore held on its own branch, `s7-isc-nifti` (based on `todo-fixes`), and merged
into `main` only together with the batched full rerun (TODO S22). The existing
`results/mind/*/isc/*_isc_mean.nii.gz` files are deleted at that point.

### Verification

For Narratives `merlin`, Caption Scene `COCO_train2014_000000434623` and NSD `nsd-60457`, the
`.npy` written by the new scripts is byte-identical (`cmp`) to that of the original scripts
(`d3db409`). A dry run of the changed workflow parsed without errors.

### Context

- Request: Written for TODO entry S7 (option B, approved by the developer on 2026-09-30); on 2026-10-01 the developer approved implementing it now and merging it only with the batched full rerun ("go on with S6, S7, S28, and S32").
- Files changed: `workflow/dataset_processing/narratives_dataset/Snakefile`, `workflow/dataset_processing/caption_scene_dataset/Snakefile`, `workflow/dataset_processing/nsd_data_dataset/Snakefile`, `workflow/dataset_processing/narratives_dataset/scripts/compute_narratives_isc.py`, `workflow/dataset_processing/caption_scene_dataset/scripts/compute_caption_scene_isc.py`, `workflow/dataset_processing/nsd_data_dataset/scripts/compute_nsd_isc.py`.

---

## 15:32 — ISC averaging and the model-key naming rule are documented

Kind: `documentation`

No code or numerical change; nothing reruns.

- **ISC averaging (TODO S11):** `libraries/fmri_processing.py::compute_leave_one_out_isc()` keeps
  the arithmetic mean of the per-subject r values. `docs/reference/fmri_preprocessing.md`, step 6,
  now states this and why Fisher-z averaging was rejected: with the 3- and 6-volume windows of NSD and
  Caption Scene, r is often near ±1, where `arctanh` explodes (≈ 7.25 at r = 0.999999) and the z
  standard error `1/sqrt(n − 3)` is undefined for n = 3; for Narratives and Nature Stories the two
  means barely differ; and the downstream top-k similarities are hardly affected by a small
  shrinkage.
- **Model family (TODO S14):** `libraries/manage_model_metadata.py::model_family()` stays
  `model.rsplit("_", 1)[0]`. The rule it relies on, `<family>_<size>` with no `_` in the size, is now
  a comment above `models:` in `config/config.yaml`. A key such as `gemma3_1b_it` would break it.

### Context

- Request: Written for TODO entries S11 (option b) and S14 (option B), approved by the developer on 2026-09-30; implemented on 2026-10-01 after the developer asked which solutions could be done while the S34 check was running ("proceed").
- Files changed: `docs/reference/fmri_preprocessing.md`, `config/config.yaml`.

---

## 15:34 — One shared writer for the LLM and ISC nearest-neighbour files

Kind: `refactor`

### Change

`compute_llm_nearest_neighbours.py` and `compute_isc_nearest_neighbours.py` repeated the same three
blocks (cosine, Pearson, Spearman: `compute_blockwise_topk_from_embeddings()` then
`write_nearest_neighbours_parquet()`). They differed only in the loader and the argument names.

- `workflow/libraries/compute_nearest_neighbours.py` gains
  `write_all_nearest_neighbours(embedding_matrix, concepts, number_of_neighbours, output_path_by_similarity_type)`.
  For each similarity type in the dict it looks up the normaliser with
  `compute_similarity.normalize_fn_for_similarity_type()` (which rejects unknown types), computes
  the top-k and writes the Parquet, freeing the arrays before the next type, as before. The library
  now imports `normalize_fn_for_similarity_type` from `libraries.compute_similarity`.
- The two scripts keep their argument parsing and their own loader (`extract_embedding_matrix` /
  `dataframe_to_embedding_matrix`) and make one call with `{"cosine": …, "pearson": …, "spearman": …}`.
  The loaders are not merged.
- Command-line arguments and Snakefile rules are unchanged, so nothing reruns.
- `compute_blockwise_topk_from_embeddings()` docstring: the reference to "the *_from_parquet readers
  above", which no longer exist, is removed (TODO S20 item 1).

Adding a similarity type now needs only an entry in
`compute_similarity.NORMALIZE_FUNCTIONS_BY_SIMILARITY_TYPE`, a new argument in each script and the
rule outputs.

### Verification

The original (`d3db409`) and new scripts were run on the Narratives `bloom_1b1` embeddings (k = 5)
and on the Narratives (k = 5) and NSD (k = 100) ISC dataframes. All nine Parquet outputs were
byte-identical (`cmp`), and two of them also byte-identical to the files in `results/`.

### Context

- Request: Written for TODO entries S18 and S20 (item 1), approved by the developer on 2026-09-30; implemented on 2026-10-01 after the developer asked which solutions could be done while the S34 check was running ("proceed").
- Files changed: `workflow/libraries/compute_nearest_neighbours.py`, `workflow/llm_nearest_neighbours/scripts/compute_llm_nearest_neighbours.py`, `workflow/isc_nearest_neighbours/scripts/compute_isc_nearest_neighbours.py`.

---

## 15:46 — One model-order rule for every figure

Kind: `refactor`

### Change

The required order is **family (alphabetical) → number of parameters → model → stimulus type**,
with the brain after all models in the heatmaps. It was implemented three ways (a local key in the
p-value heatmap, `heatmap_label_sort_key()` in the alignment heatmap, and the shared key without a
stimulus-type level in the six model figures). Now:

- `workflow/libraries/manage_model_metadata.py`: `model_sort_key(model, stimuli_type, parameters_by_model)`
  returns `(model_family(model), parameters_by_model[model], model, stimuli_type)`. Families are
  sorted alphabetically in code. `model_family_order()`, which took the family order from the order
  of the `models:` block in the config, is deleted (its only caller was `model_sort_key()`); the
  config order no longer affects any figure.
- `plot_empirical_p_value_heatmap.py`: the local `model_sort_key()`, the `model_family` import and
  the `number_of_parameters` field of `model_metadata` are deleted.
- `plot_alignment_heatmap.py`: `heatmap_label_sort_key()` is deleted. Its label sort no longer
  depends on the iteration order of a `set` when one model appears with two stimulus types.
- Both heatmaps sort with
  `(1,) if label == "brain" else (0, *model_sort_key(model, stimuli_type, parameters_by_model))`.
- `plot_brain_model_alignment_lineplot.py`, `plot_concept_alignment_scatterplot.py`,
  `plot_spearman_alignment.py` (both figures), `plot_brain_model_alignment_enrichment_lineplot.py`
  and `plot_concept_alignment_enrichment_scatterplot.py` pass the stimulus type, so ties no longer
  depend on the order of the input files.
- `grep -rn "sorted(\|sort_values" workflow/visualisation` finds no other model sort.

Only the plotting rules are affected (`[light]`). Snakemake does not see edits to scripts run from
`shell:` rules, so the figures are redrawn the next time the plot rules run (they rerun anyway after
the S34 aggregation change is merged).

### Verification

- All 38 configured models plus "brain", and a synthetic second stimulus type for `clip_b`, were
  shuffled 20 times and sorted with the old keys (`d3db409`) and the new one. The order was the
  same every time (the config families are alphabetical and contiguous), and the synthetic pair
  was ordered by stimulus type.
- One real job of each of the 7 changed plot rules was run with the new code, its command taken from
  a dry run, figures written to a scratch directory. All 8 figures were byte-identical to the current
  ones in `results/pictures/`.

### Context

- Request: Written for TODO entry S1, modified and approved by the developer on 2026-09-30; implemented on 2026-10-01 after the developer asked which solutions could be done while the S34 check was running ("proceed").
- Files changed: `workflow/libraries/manage_model_metadata.py`, `workflow/visualisation/scripts/plot_empirical_p_value_heatmap.py`, `workflow/visualisation/scripts/plot_alignment_heatmap.py`, `workflow/visualisation/scripts/plot_brain_model_alignment_lineplot.py`, `workflow/visualisation/scripts/plot_concept_alignment_scatterplot.py`, `workflow/visualisation/scripts/plot_spearman_alignment.py`, `workflow/visualisation/scripts/plot_brain_model_alignment_enrichment_lineplot.py`, `workflow/visualisation/scripts/plot_concept_alignment_enrichment_scatterplot.py`.

---

## 16:18 — Commented-out rules and targets removed

Kind: `removal`

### Changes

- `workflow/llm_mind_alignment/Snakefile`: deleted the commented-out rules `reduce_all_p_values`
  (wrote `results/tsv_summary.tsv` with `matrix_reduce` and `bawk`, through a conda environment
  `envs/reduce_all_p_values_environment.yaml` that no longer exists) and
  `translate_parquet_to_tsv_adding_observed_alignment_score` (wrote `…NN.observed.tsv` from the
  per-k `…NN_relabelled.parquet` files, which were replaced on 2026-09-30 by the all-k
  `-relabelled_common_neighbours.parquet` files). Deleted their commented-out targets from
  `rule all_llm_mind_alignment`.
- `workflow/Snakefile`, `rule all`: deleted the same commented-out targets (`…NN.observed.tsv`,
  `results/tsv_summary.tsv`).

Comments only: no rule, input, output or shell command changed, so nothing reruns.
`parquet2tsv.sh` is kept (used by hand to view parquet files). The `bawk`, `coreutils`,
`matrix_reduce` and `molinerislab` entries of `llm_mind_alignment_environment.yaml` stay until S22
(TODO S29 item 3), since changing an environment file reruns every rule that uses it.

### Verification

`snakemake --list-rules` and `snakemake -n` parse the changed Snakefiles (run on a copy of the
committed tree, with `resources/` and `results/` linked read-only).

### Context

- Request: Written for TODO entry S29 item 3 (Snakefile part), approved by the developer on 2026-09-30; implemented after the developer asked to do the parts of S29 that do not interfere with the running S34 check.
- Files changed: `workflow/Snakefile`, `workflow/llm_mind_alignment/Snakefile`.

---

## 16:40 — Faster p-value aggregation (both summary TSVs)

Kind: `optimisation`

### Problem

`libraries/aggregate_alignment_scores.py::aggregate_all_p_value_outputs()`, shared by the rules
`aggregate_all_p_value_outputs` (LLM-brain) and `aggregate_all_llm_llm_p_value_outputs` (LLM-LLM),
handled one result at a time on one core. The first complete LLM-LLM run on node5 took 4 h 10 min
for 11,184 results (~1.4 s each). About a quarter of that was a duplicate check on the relabelled
rows of each result.

### Changes

- `workflow/libraries/aggregate_alignment_scores.py`:
  - deleted `read_unique_relabelled_alignment_scores()`, which ran
    `duplicated(subset = ["shuffle_id", "concept"])` on the up-to-10-M relabelled rows of each
    result. The relabelled files are written only by `libraries/compute_relabelled_alignment.py`,
    where (k, shuffle, concept) is unique by construction, and `compute_empirical_p_value.py`
    already reads them without the check. The reads now call
    `compute_alignment.read_relabelled_alignment_scores()` directly (unchanged filtered per-k read);
  - new top-level `aggregate_result(metadata, empirical_path, hypergeometric_path, relabelled_path)`:
    reads one result's inputs and returns `aggregate_model_results()`;
  - `aggregate_all_p_value_outputs()` gains a required `threads` parameter and maps
    `aggregate_result` over the results, in sorted key order, with
    `concurrent.futures.ProcessPoolExecutor(max_workers = threads).map(..., chunksize = 16)`.
    `map()` keeps the input order, so the rows, and the TSV, are unchanged.
- `workflow/llm_mind_alignment/scripts/aggregate_all_p_value_outputs.py`,
  `workflow/llm_llm_alignment/scripts/aggregate_all_llm_llm_p_value_outputs.py`: new required
  `--threads` (int), passed to `aggregate_all_p_value_outputs()`.
- Rules `aggregate_all_p_value_outputs` and `aggregate_all_llm_llm_p_value_outputs`: `threads: 4`
  and `--threads {threads}` (after `@"$args_file"` in the LLM-LLM rule). Peak memory: about 4 ×
  one result's relabelled rows.

Rejected (TODO S34 part 1, implemented and measured): reading each all-k relabelled file once and
splitting it by k with `groupby`. On a Caption Scene file (40 M rows, k = 5, 25, 50, 100) that took
14–17 s against ~0.7 s for the four filtered per-k reads, because the split copies the categorical
`shuffle_id` and `concept` columns.

### Rerun impact

The two shell commands changed, so Snakemake reruns both aggregation rules, and the plots that
wait for their TSVs, once. The outputs do not change.

### Verification

Old code (`main` at `d3db409`) and new code, run in the same conda environment on the frontend:
- all 768 LLM-brain results: output byte-identical (`cmp`) to
  `results/all_model_brain_alignment_scores.tsv`; 23 min 24 s old, 6 min 20 s new;
- 180 LLM-LLM results (60 relabelled files, 40 of them Caption Scene or NSD): byte-identical;
  4 min 27 s old, 2 min 25 s new (with the frontend's load about 10 and about 40 respectively).

A full LLM-LLM comparison was stopped after 2 h by the frontend's load (~40 on 8 cores) and not
repeated; the developer accepted the evidence above. The node5 duration of the new code is still
to be measured (`docs/reference/clean_run_duration.md`).

### Context

- Request: Written for TODO entry S34, approved by the developer on 2026-10-01 and revised after measurement (part 1 dropped), after the developer asked to start addressing the TODO problems while the pipeline was running.
- Files changed: `workflow/libraries/aggregate_alignment_scores.py`, `workflow/llm_mind_alignment/Snakefile`, `workflow/llm_mind_alignment/scripts/aggregate_all_p_value_outputs.py`, `workflow/llm_llm_alignment/Snakefile`, `workflow/llm_llm_alignment/scripts/aggregate_all_llm_llm_p_value_outputs.py`, `README.md`, `docs/reference/clean_run_duration.md`.

---

## 19:00 — Model tick labels without the stimulus type

Kind: `new_feature`

### Changes

Only the drawn tick text changes. `manage_model_metadata.model_key(model, stimuli_type)`
(`<model>-<stimuli_type>`) stays the internal identifier used to match rows and fill
dictionaries, and output filenames are unchanged.

- `plot_brain_model_alignment_lineplot.py`, `plot_concept_alignment_scatterplot.py`,
  `plot_spearman_alignment.py` (both figures): `ax.set_xticklabels(models, ...)` instead of
  `labels`. `models` is the list, in tick order, already passed to
  `add_model_family_annotations()`.
- `plot_brain_model_alignment_enrichment_lineplot.py`,
  `plot_concept_alignment_enrichment_scatterplot.py` (both calls):
  `style_model_x_axis(ax, models)` instead of `labels`.
- `plot_alignment_heatmap.py`, `plot_empirical_p_value_heatmap.py`: new local
  `tick_names` (`model_metadata[label]["model"]`, or `brain`) passed to
  `set_xticklabels()`/`set_yticklabels()`.
- `README.md`: model-naming paragraph and the plot conventions updated.

The stimulus type stays visible through `colour_tick_labels_by_stimuli_type()` and the legend.
No model runs with both stimulus types in the same dataset (checked on
`results/alignment_scores/`), so the names stay unique within each figure.

### Rerun impact

Snakemake does not hash script contents, so existing figures update only with
`--rerun-triggers mtime --forcerun` of the 7 plot rules (193 jobs, ~20 min on node5) or with the
next full rerun. Without `--rerun-triggers mtime`, a dry run on `main` (2026-10-01) plans 40,957
jobs, because of "software environment definition has changed" provenance triggers on upstream
rules (left as is by the developer, to be resolved by the S22 full rerun).

### Verification

One real job of each of the 7 plot rules (8 figures), with commands from a dry run, rendered with
the code before and after the change. The labels show model names only, in the same colours, with
`brain` unchanged; nothing else differs. The line and box plots are ~175 px shorter (shorter
labels, tight bounding box); the heatmaps keep their size.

### Context

- Request: Written for TODO entry S36, raised and approved by the developer on 2026-10-01 ("there is no need for this extra specification, since now language and vision models are distinguished visually colouring their names").
- Files changed: `workflow/visualisation/scripts/plot_alignment_heatmap.py`, `workflow/visualisation/scripts/plot_empirical_p_value_heatmap.py`, `workflow/visualisation/scripts/plot_brain_model_alignment_lineplot.py`, `workflow/visualisation/scripts/plot_concept_alignment_scatterplot.py`, `workflow/visualisation/scripts/plot_brain_model_alignment_enrichment_lineplot.py`, `workflow/visualisation/scripts/plot_concept_alignment_enrichment_scatterplot.py`, `workflow/visualisation/scripts/plot_spearman_alignment.py`, `README.md`.

---

## 19:24 — `download_pretrained_llm.py` uses argparse

Kind: `refactor`

### Changes

- `workflow/llm_nearest_neighbours/scripts/download_pretrained_llm.py`: replaced the `sys.argv`
  handling (two positional arguments, and a usage message with the stale path
  `workflow/scripts/...`) with `argparse`: required `--model_name` (Hugging Face repository ID) and
  `--save_dir`. Removed `download_model_repo()`; `main()` calls
  `snapshot_download(repo_id = ..., local_dir = ...)` directly. `--help` now works like in the
  other scripts.
- Rule `download_pretrained_llm` (`workflow/llm_nearest_neighbours/Snakefile`): passes
  `--model_name {params.hf_name:q}` and `--save_dir {output.model_dir:q}`.

### Rerun impact

The rule's shell command changed, so with Snakemake's default rerun triggers all 38
`download_pretrained_llm` jobs, and through their outputs the whole pipeline, rerun. That is why
this change sits on the branch `s37-download-argparse` and is merged only together with the S22
full rerun (TODO S37), like S7. With `--rerun-triggers mtime` nothing reruns.

### Verification

In the rule's conda environment: `--help` prints both options; a missing `--save_dir` exits
with an argparse error; the command rendered by `snakemake -n -p` for `bloom_560m`, run with
`snapshot_download` replaced by a stub, calls it with
`repo_id = "bigscience/bloomz-560m", local_dir = "resources/models/bloom_560m"`, as before.

### Context

- Request: Written for TODO entry S37, option (b) chosen by the developer on 2026-10-01 ("switch the script to argparse"), after the post-merge check found the stale usage path.
- Files changed: `workflow/llm_nearest_neighbours/scripts/download_pretrained_llm.py`, `workflow/llm_nearest_neighbours/Snakefile`.

---

## 22:24 — Pinned conda environments

Kind: `new_feature`

### Changes

- Every package listed in the 11 environment files is pinned to an exact version: conda
  `- pkg=<version>`, pip `netneurotools==0.3.0`, and
  `git+https://github.com/cvnlab/nsdcode.git@bfd36a503cc90a3eb3ebfd69b269403f7e186924` (the current
  HEAD; the only tag, `v1.0`, is older). Versions are the latest on each channel on 2026-10-01
  (`mamba search`), never below the minimum table of TODO P22:
  python 3.14.7, numpy 2.5.3, pandas 3.0.6, pyarrow 25.0.0, scipy 1.18.1, nibabel 5.4.2,
  nilearn 0.14.1, h5py 3.16.0, pip 26.2.1, praatio 6.2.2, git 2.56.0, pillow 12.3.0, tqdm 4.70.1,
  matplotlib 3.11.2, accelerate 1.15.0, bitsandbytes 0.50.2, datasets 5.0.1,
  huggingface_hub 1.32.0, protobuf 7.35.1, pytorch 2.13.0, scikit-learn 1.9.1,
  sentencepiece 0.2.1, tiktoken 0.14.0, timm 1.0.30, torchvision 0.28.0, transformers 5.18.0,
  snakemake 9.27.0.
- `workflow/envs/LLMmind_project_environment.yaml`: `python=3.14.7`, `snakemake=9.27.0`
  (snakemake-minimal 9.27 dropped the `python <3.14` cap of 9.21; snakemake still requires
  `pandas <3`, so this environment resolves pandas 2.3.3; comment added).
- `llm_nearest_neighbours_environment.yaml`: `python=3.12` → `python=3.14.7` (pytorch,
  bitsandbytes, sentencepiece, tiktoken, timm and transformers all solve on 3.14, CUDA 12.9
  builds). New package `cuda-cudart-dev=12.9.79` (approved exception to S22's "no new
  packages"): pytorch 2.13 dispatches some ops (e.g. `bmm_outer_product` in the Gemma rotary
  embedding) to triton kernels; triton compiles a `cuda_utils` helper on first use with
  `-I $CONDA_PREFIX/targets/x86_64-linux/include` and needs `cuda.h`, which no package of the
  environment provided. The current environment only worked because the helper was cached in
  `~/.triton/cache` for cpython-312; a fresh build crashed with `fatal error: cuda.h`.
- `llm_mind_alignment_environment.yaml`: removed `bawk`, `coreutils`, `matrix_reduce` and the
  `molinerislab` channel, used only by the commented-out rules deleted earlier (TODO S29 item 3).
- `README.md`: new "Pinned versions" section (pins, caps, the `cuda-cudart-dev` reason, upgrade
  procedure); the base environment is described as python + full `snakemake`, not
  `snakemake-minimal`.

Release notes checked for breaking changes against the APIs used (`AutoModel`,
`AutoProcessor`, `AutoTokenizer`, `BitsAndBytesConfig`, `snapshot_download`): transformers
5.17 (vision RoPE refactor; not used by DINOv2/CLIP/ViT) and 5.18 (🚨 DINOv2 refactor, PR #46266),
huggingface_hub 1.32. No code change was needed.

### Rerun impact

Every environment file changed, so Snakemake rebuilds every environment and reruns every job. This
change sits on the branch `s22-pinned-envs` and is merged only for the single full recomputation
together with S10, S17 and S31 (and the S7 and S37 branches), as required by the S22 approval.
The base environment `workflow/envs/LLMmind_project/` must be rebuilt by hand at that time:
`conda env create -p workflow/envs/LLMmind_project -f workflow/envs/LLMmind_project_environment.yaml`
after removing the old prefix.

### Verification

- All 11 environments solve (`mamba env create --dry-run`, `CONDA_OVERRIDE_CUDA=12.9`) and build.
- 19 representative jobs, commands from `snakemake -n -p` on `main`, run on the frontend (CPU)
  in the current and in the pinned environment, outputs compared:
  - byte-identical: ISC (Caption Scene, Nature Stories, Narratives), TextGrid conversion,
    `make_nsd_manifest`, Spearman, empirical and hypergeometric p-values;
  - identical values, parquet metadata differs: embeddings of `clip_b`, `dinov2_s` and
    `bloom_560m` (Caption Scene), nearest neighbours (models and ISC), relabelled files;
  - same rows in a different order: the two alignment-score parquets, because
    `compute_alignment_scores()` iterates over a `set` of concepts (string hash randomisation;
    independent of the environment);
  - lineplot: 0 differing pixels.
- node5 GPU, pinned environment with `cuda-cudart-dev`: `get_embeddings.py` for `gemma2_9b`
  (8-bit) and `gemma2_27b` (4-bit) on Narratives gives embeddings exactly equal to the pipeline's.
- Snakemake 9.27.0 (Python 3.14) parses the workflow and builds the DAG without errors.

### Context

- Request: Written for TODO entry S22 (approved by the developer on 2026-09-30; `cuda-cudart-dev` exception approved on 2026-10-01), implemented after the developer chose "Implement S22 (pinning)".
- Files changed: all 11 `*_environment.yaml` files (`workflow/envs/`, `workflow/*/envs/`, `workflow/dataset_processing/*/envs/`), `README.md`.
