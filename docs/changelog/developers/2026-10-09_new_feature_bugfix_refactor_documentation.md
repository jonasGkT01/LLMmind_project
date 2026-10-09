# 2026-10-09 — developer changelog

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../../AI_USAGE.md).*

Changes made on this day, in order:

- Parquet files read through pyarrow's own file system, fixing jobs that hang at exit (bugfix, documentation)
- Origin of the Nature Stories TextGrids documented and checked against the fMRI data (documentation)
- Narratives parcellated with the Schaefer atlas in its own MNI template (bugfix, documentation)
- Similarity-comparison line plots (new_feature, refactor, documentation)

---

## 09:40 — Parquet files read through pyarrow's own file system

Kind: bugfix, documentation

**Problem (TODO P51).** A few jobs per run wrote their complete output and then never exited
(0 CPU time, main thread in `futex`), each holding one `--cores` slot until killed. On 2026-10-09 a
hung `compute_hypergeometric_p_value` job of the run started on 2026-10-08 was traced with
`gdb -p <pid> -batch -ex "thread apply all bt"`. With pandas 3.0.6, pyarrow 25.0.0 and Python
3.14.7:
- for a local path, `pd.read_parquet(path, engine = "pyarrow")` opens a Python file object
  (`pandas.io.parquet._get_path_or_handle` → `get_handle`), which pyarrow wraps in
  `arrow::py::PyReadableFile` and reads with `RandomAccessFile::ReadAsync` on its I/O thread pool;
- main thread: `exit()` → C++ static destructors → `arrow::internal::ThreadPool::Shutdown`, waiting
  for the I/O workers;
- one I/O worker: dropping the last reference to the `PyReadableFile` from a finished `ReadAsync`
  task; the destructor calls `PyGILState_Ensure`, and with the interpreter finalised Python 3.14
  parks the thread forever (`PyThread_hang_thread` → `pause()`).
A race at exit, hence a few hangs in thousands of jobs. OpenBLAS and OpenMP were not involved.

**Fix.**
- New `workflow/libraries/parquet_io.py`: `LOCAL_FILESYSTEM = pyarrow.fs.LocalFileSystem()` and
  `read_parquet(path, **read_options)`, which calls `pd.read_parquet(path, engine = "pyarrow",
  filesystem = LOCAL_FILESYSTEM, **read_options)`. With a filesystem given, pandas skips
  `get_handle` and pyarrow opens a native file whose destructor needs no GIL.
- All 13 `pd.read_parquet` calls replaced by `read_parquet()`, in
  `libraries/compute_alignment.py` (`read_relabelled_alignment_scores()`,
  `read_alignment_scores()`, keeping their `columns`/`filters`), `libraries/compute_nearest_neighbours.py`
  (`read_nearest_neighbours()`) and the scripts `compute_isc_nearest_neighbours.py`,
  `compute_llm_nearest_neighbours.py`, `compute_hypergeometric_p_value.py`,
  `compute_empirical_p_value.py`, both `relabel_llm_similarity_and_compute_relabelled_*` scripts
  and `compute_spearman_alignment_with_empirical_p_value.py`. The `import pandas as pd` that
  became unused was removed from four scripts.
- `docs/guides/running_and_troubleshooting.md`: troubleshooting entry for a job that hangs after
  writing its output, including how to end it with exit status 0
  (`gdb -p <pid> -batch -ex "call (void)_exit(0)"`) so that Snakemake keeps the output.
- `docs/reference/clean_run_duration.md`: the sentence excluding hung jobs from the estimate removed.

No result changes. The rules' shell commands are unchanged, and a dry run
(`snakemake -n --rerun-incomplete --use-conda --cores 4 --resources gpu=1`) lists no job with
"Code has changed": its 14,228 jobs are the rest of the unfinished 2026-10-08 run.

### Context

- Request: the developer asked what was running, then why a `compute_hypergeometric_p_value` job
  had been asleep for 3 h after writing its output, then to implement the proposed fix (TODO S51,
  approved on 2026-10-09, also while S52 is still unapproved). The developer ended the run before
  the change.
- Files: `workflow/libraries/parquet_io.py` (new), the 9 files listed above,
  `docs/guides/running_and_troubleshooting.md`, `docs/reference/clean_run_duration.md`,
  `docs/AI_USAGE.md`.
- Verification, in the pipeline environment (`.snakemake/conda/273bf7076eaea539fd63764652c1c761_`):
  old and new reads give equal frames (`DataFrame.equals` and equal index) for a language and a
  vision embeddings file, an ISC dataframe, an ISC and an LLM nearest-neighbour file, an alignment
  score file (all columns and `columns = [...]`) and a relabelled common-neighbours file with
  `columns` and `filters` (10,000,000 rows); relative paths and `pathlib.Path` work; all edited
  files compile; `compute_hypergeometric_p_value.py` run on the hung job's input gives a TSV
  byte-identical to the one the hung job wrote. The hang itself is a rare race and could not be
  reproduced on demand; the next full run will show whether it is gone.

---

## 11:35 — Origin of the Nature Stories TextGrids documented and checked against the fMRI data

Kind: documentation

New reference page `docs/reference/nature_stories_stimuli.md`, linked from the README index and
from the Nature Stories input list:
- The TextGrids come from OpenNeuro `ds003020` (LeBel et al., *Sci. Data* 2023,
  `derivatives/TextGrids`), downloaded by `public_datasets` rule `download_nature_story_stimuli`;
  the BOLD data, mappers and `.wav` files come from the G-Node archive `10.12751/g-node.t4wew2`,
  which has no transcripts.
- `convert_nature_stories_textgrids.py` keeps only the word sequence; no rule reads the word
  timings or the `.wav` files.
- Check: `ds003020/derivatives/respdict.json` TR counts equal the `new_run_onsets.json` lengths
  + 20 (10 trimmed TRs per end) for all 11 stories, while the original `run_onsets.json` differs
  for alternateithicatom, avatar and howtodraw; TextGrid `xmax` equals the G-Node `.wav` duration
  within 0.01 s for 10 stories. `life`: TextGrid 880.3 s, `train_04.wav` 808.8 s, scan 900 s, so
  the G-Node audio is truncated and the TextGrid matches the scan. No effect on results.

### Context

- Request: the developer asked where the Nature Stories TextGrids come from, then to check that
  `ds003020` is the LeBel et al. dataset and that its timings match the G-Node data, then to
  record the discussion in the project documentation.
- Files: `docs/reference/nature_stories_stimuli.md` (new), `README.md`, `docs/AI_USAGE.md`, the
  2026-10-09 changelogs.
- Verification: `ds003020/dataset_description.json` and `derivatives/respdict.json` fetched from
  the public OpenNeuro bucket; durations computed with Python's `wave` module and the
  `read_textgrid`/`get_word_tier` functions of `convert_nature_stories_textgrids.py`, in the
  Nature Stories processing environment, on the files in
  `public_datasets/results_molilab_cold_back/nature_stories_dataset/`.

---

## 15:14 — Narratives parcellated with the Schaefer atlas in its own MNI template

Kind: bugfix, documentation

**Problem (TODO P53).** The Narratives BOLD files are in MNI152NLin2009cAsym, but
`extract_narratives_parcels.py` took the atlas from nilearn's `fetch_atlas_schaefer_2018()`
(`Schaefer2018_200Parcels_7Networks_order_FSLMNI152_1mm`, MNI152NLin6Asym).
`get_resampled_parcel_matrix()` matches atlas and BOLD by world coordinates only, and its
`sform_code` check accepts both templates, so the parcel borders were shifted by a few mm.

**Change (S53).** `workflow/dataset_processing/narratives_dataset/scripts/extract_narratives_parcels.py`
no longer imports `nilearn.datasets`. It builds
`tpl-MNI152NLin2009cAsym_res-01_atlas-Schaefer2018_desc-{n_rois}Parcels{yeo_networks}Networks_dseg.nii.gz`,
downloads it with `urllib.request.urlretrieve()` from `TEMPLATEFLOW_URL`
(`https://templateflow.s3.amazonaws.com/tpl-MNI152NLin2009cAsym`) into `--atlas_dir` if it is not
there yet, and loads it with `image.load_img()`. Arguments, rule and environment are unchanged;
`extract_parcels()` and `get_resampled_parcel_matrix()` are unchanged; NSD and Caption Scene keep
the nilearn atlas, Nature Stories the fsaverage one. The rule has no `code` param, so the change
does not trigger a rerun by itself: run with `--forcerun extract_narratives_parcels`, which
recomputes the Narratives parcel time series, ISC, nearest neighbours, alignment and Spearman
scores, summary TSVs and plots.

### Context

- Request: the developer approved S53 on 2026-10-09 and asked for it to be implemented.
- Files: `extract_narratives_parcels.py`; `docs/reference/fmri_preprocessing.md` (parcellation step
  and Changes).
- Verification: label order checked against nilearn's `Schaefer2018_200Parcels_7Networks_order.txt`
  with TemplateFlow's `..._desc-200Parcels7Networks_dseg.tsv` and both NIfTIs: the nearest
  TemplateFlow parcel of every nilearn parcel has the same index (200/200), all 200 colours agree,
  and the centroids differ by 1.6 mm median (3.1 mm max). 40 sub-region names differ (older naming
  in TemplateFlow); the workflow never reads the names. The script was run on one run
  (`sub-001_task-tunnel`) in the narratives conda env: download OK, output 1040 × 200, per-parcel
  correlation with the old time series median 0.981, min 0.768. The full rerun has not been run.

---

## 15:14 — Similarity-comparison line plots

Kind: new_feature, refactor, documentation

**Request (TODO P52).** One plot per dataset × *k* comparing the cosine, Pearson and Spearman
similarity types, in addition to the existing per-type plots, which stay unchanged.

**New outputs** in `results/pictures/similarity_comparison_lineplots/`, 20 PNGs with the current
config (8 dataset × *k* combinations for each of the first two, 4 datasets for the third):
`dataset-{dataset}-brain_model_alignment_{k}NN.png`,
`dataset-{dataset}-brain_model_alignment_enrichment_{k}NN.png`,
`dataset-{dataset}-brain_model_spearman_alignment.png`. (S52 said 18; the count is 20.)

**Code (S52):**
- `workflow/visualisation/scripts/plot_similarity_comparison_lineplot.py` (new):
  `--quantity {alignment, enrichment, spearman}`. Groups the alignment parquets by similarity type
  (`parse_alignment_path()`), or the Spearman TSV rows by their `similarity_type` column; for
  enrichment, passes each group the relabelled files matching `relabelled_name_for_observed_path()`
  to `compute_alignment_enrichment()`. Checks that every type covers the same models, sorts them with
  `sort_models()`, draws one series per type, the null line, no asterisks, and data-fitted y-limits
  (on symlog positions for enrichment, bottom ≥ 0).
- `workflow/libraries/visualisation_utils.py`: `SIMILARITY_TYPE_COLOURS`,
  `plot_similarity_type_points()`, `similarity_type_legend_handles()`, `DATA_FITTED_Y_PADDING` and
  `data_fitted_ylim(values, minimum)`; `HYPERGEOMETRIC_NULL_LABEL`, `ENRICHMENT_NULL_LABEL`,
  `SPEARMAN_NULL_LABEL`; `plot_title()` takes `similarity_type = None`; `style_model_axes()` skips
  the asterisks and their legend entries when `p_values` is `None`.
- Refactor: the per-model mean/SE loop of `plot_brain_model_alignment_lineplot.py` moved to
  `summarise_alignment_scores()` in `workflow/libraries/compute_alignment.py` (returns the model
  dataframe and the shared hypergeometric expectation); the Spearman TSV loading and validation of
  `plot_spearman_alignment.py` moved to `read_spearman_scores(paths, dataset, model_level)` in the
  new `workflow/libraries/spearman_scores.py`, together with `NULL_STANDARD_DEVIATION_COLUMN`. The
  duplicate check is now on (label, similarity type); the similarity-type check stays in
  `plot_spearman_alignment.py`.
- `workflow/Snakefile`: `NEIGHBOUR_PAIRINGS` (dataset × *k*), the three output lists in `rule all`.
- `workflow/visualisation/Snakefile`: the same lists in `rule all_visualisation`; rules
  `plot_similarity_comparison_alignment_lineplot`, `plot_similarity_comparison_enrichment_lineplot`
  (both with `wildcard_constraints: number_of_neighbours = r"\d+"`, so the alignment rule cannot
  match the enrichment file names) and `plot_similarity_comparison_spearman_lineplot`.

### Context

- Request: the developer approved S52 on 2026-10-09, after the run of that day had finished.
- Files: the five Python files and two Snakefiles above; `docs/reference/statistics.md`
  (section 7 and Changes), `docs/guides/running_and_troubleshooting.md` (redraw command),
  `README.md` (output folders).
- Verification: `snakemake -n` on the 20 new targets plans exactly the 20 new jobs and nothing
  upstream. The refactored `plot_brain_model_alignment_lineplot.py` (3 configurations) and
  `plot_spearman_alignment.py` (2 configurations, both outputs) give PNGs pixel-identical to those
  of the 2026-10-09 run. Comparison plots rendered for alignment (caption_scene, k = 25;
  nature_stories, k = 3), enrichment (nature_stories, k = 3) and Spearman (caption_scene,
  narratives) and checked by eye.

