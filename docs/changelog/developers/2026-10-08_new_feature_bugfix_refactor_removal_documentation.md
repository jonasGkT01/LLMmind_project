# 2026-10-08 — developer changelog

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../../AI_USAGE.md).*

Changes made on this day, in order:

- Split-half ISC reliability removed (removal, refactor, documentation)
- Non-finite and constant vectors rejected before the nearest-neighbour search (bugfix)
- LLM-brain and LLM-LLM alignment-score scripts made identical (refactor)
- Script defaults that duplicated config values removed (refactor)
- Config checked at startup (new_feature, documentation)
- Unused similarity functions removed (removal)
- `code_version()` script hashes include comments: guide corrected (documentation)
- Analysis parameters moved from the scripts to the config; last script defaults removed (refactor, documentation)
- Manifest rules rerun when the data they are written from changes (bugfix, documentation)
- Neighbourhood sizes of Caption Scene and NSD changed to 5, 25, 125; 50NN and 100NN outputs deleted (new_feature, removal, documentation)

The changes up to the guide correction were made together after the 2026-10-05/06 rerun had
finished (no Snakemake job running for the user on node5); a dry run afterwards
(`snakemake --use-conda --cores 4 -n --quiet rules`) reported "Nothing to be done". The last three
changes, made at the user's request the same morning, make the next run a full recomputation
(dry run: 33,269 jobs before the checkpoints expand; model downloads are not rerun).

---

## 09:43 — Split-half ISC reliability removed

Kind: removal, refactor, documentation

The developer decided on 2026-10-05 not to use the ISC reliability (TODO P44/S44).

- `workflow/isc_nearest_neighbours/Snakefile`: rules `compute_isc_reliability` and
  `aggregate_isc_reliability`, `ISC_MANIFEST_LAYOUT`, `AGGREGATE_ISC_RELIABILITY_SCRIPT` and the
  `all_isc_reliability` input of `rule all_isc_nearest_neighbours` deleted.
- `workflow/Snakefile`: `isc_reliability_summary` input of `rule all` deleted.
- `workflow/isc_nearest_neighbours/scripts/compute_isc_reliability.py` and
  `aggregate_isc_reliability.py` deleted.
- `workflow/libraries/compute_isc.py`: `compute_split_half_isc_reliability()` deleted;
  `load_isc_inputs()` folded back into `compute_isc_from_files()`, its only remaining caller (same
  behaviour; S44 item 2).
- `config/config.yaml`: `isc_reliability_number_of_splits` deleted.
- `workflow/dataset_processing/caption_scene_dataset/Snakefile`: `write_caption_scene_isc_manifest`
  and `CAPTION_SCENE_ISC_MANIFEST` deleted (the rule existed only to feed the reliability).
- This also removes the unguarded Spearman-Brown column (P41) and the stale "TODO S30" comment
  (P43). SUGGESTIONS I9/IS9 (number of valid splits) became moot and were removed.
- Docs: step 7 of `docs/reference/fmri_preprocessing.md` and the README output bullet removed,
  together with the "exploratory" label of NSD and Caption Scene; the method, the 2026-10-02
  measurements and the decision moved to the `## Changes` section of `fmri_preprocessing.md`.
  Three rows removed from `docs/reference/clean_run_duration.md`.
- Left to the developer: delete `results/mind/*/isc_reliability.tsv`,
  `results/mind/all_isc_reliability.tsv` and `results/mind/caption_scene/manifests/isc_manifest.tsv`
  (leaf outputs: nothing else reruns).

### Context

- Request: the user asked to implement every entry of `.claude/TODO/LLMmind_project.md`.
- Files changed: the code files above, `README.md`, `docs/reference/fmri_preprocessing.md`,
  `docs/reference/clean_run_duration.md`, `docs/guides/running_and_troubleshooting.md`.
- Verification: `compute_isc_from_files()` recomputed the ISC of 3 NSD stimuli from
  `results/mind/nsd_data/manifests/isc_manifest.tsv`; `np.array_equal` with the stored
  `*_isc_mean.npy` files was true for all 3. Dry run: nothing to be done.

---

## 09:43 — Non-finite and constant vectors rejected before the nearest-neighbour search

Kind: bugfix

`compute_blockwise_topk_from_embeddings()` (`workflow/libraries/compute_nearest_neighbours.py`)
now raises a `ValueError` listing the row indices of rows with a non-finite value
(`~np.isfinite(...).all(axis = 1)`) or a constant vector (`np.ptp(..., axis = 1) == 0`, which
covers zero vectors). Before, a NaN row entered every other concept's top-k, and a constant row,
normalised to zeros, got arbitrary neighbours (TODO P40/S40). The function serves the LLM and ISC
neighbours and the relabelling null (`compute_relabelled_alignment.py`).

### Context

- Request: as above (TODO S40).
- Files changed: `workflow/libraries/compute_nearest_neighbours.py`.
- Verification: on a random 10 x 5 matrix the function returns the same shape as before; a NaN row,
  an inf row, and a zero row plus a constant row each raise the error with the right indices. The
  99 embedding files on disk had no such row (checked on 2026-10-05). Libraries are not in the
  shell rules' rerun triggers, so nothing reruns.

---

## 09:43 — LLM-brain and LLM-LLM alignment-score scripts made identical

Kind: refactor

- `read_nearest_neighbours(path, number_of_neighbours)` moved unchanged from
  `compute_llm_llm_alignment_score.py` to `workflow/libraries/compute_nearest_neighbours.py`
  (which now imports `validate_required_columns` from `libraries.validate_data`).
- `workflow/llm_mind_alignment/scripts/compute_llm_mind_alignment_score.py` and
  `workflow/llm_llm_alignment/scripts/compute_llm_llm_alignment_score.py` now differ only in the
  names and help texts of the two neighbour arguments: every argument `required = True`, the
  `<= 0` check, `read_nearest_neighbours()`, `compute_alignment_scores()`, a `ValueError` on an
  empty result (new for the LLM-brain script), the same comments. Removed: the hand-written column
  checks, `None` check, variable copies and commented-out print block (LLM-brain); the shebang and
  the `Path`/`mkdir` lines (LLM-LLM; Snakemake creates output directories).
- `workflow/llm_nearest_neighbours/scripts/compute_llm_nearest_neighbours.py`: the 4 path
  arguments are now `required = True`.

### Context

- Request: as above (TODO P45/S45).
- Files changed: the three scripts and `workflow/libraries/compute_nearest_neighbours.py`.
- Verification: both scripts rerun into the scratchpad on real inputs (Caption Scene,
  `gemma2_9b`, Pearson, 25NN; NSD, `clip_b` vs `dinov2_l`, cosine, 50NN); `DataFrame.equals`
  with the stored parquets was true for both. Running each script without arguments lists all
  arguments as required. The `shell:` commands are unchanged.

---

## 09:43 — Script defaults that duplicated config values removed

Kind: refactor

`--random_seed` is now required (no default 0) in
`compute_spearman_alignment_with_empirical_p_value.py`,
`relabel_llm_similarity_and_compute_relabelled_llm_alignment_score.py` and
`relabel_llm_similarity_and_compute_relabelled_llm_llm_alignment_score.py`; `--interpolation` is
required (no default "cubic") in `assemble_nsd_bold.py`. The Caption Scene Snakefile reads
`config["caption_scene"]["run_table_encoding"]` without the `"gbk"` fallback. The config comment of
`max_chunk_length` now says that `null` is the intended default and that 2048 is set because some
Gemma models crash with `null`.

Not done: the defaults of `--onset_shift_s` and `--run_table_encoding` in
`make_caption_scene_manifest.py`. That script is hashed by `code_version()` in the `params` of
`make_caption_scene_manifest`, byte for byte, so any edit (even the attribution header) reruns the
Caption Scene manifest and everything downstream (the dry run listed 29,264 jobs). The edit was
reverted; TODO P46/S46 now hold only this part, to be done at the next full recomputation.

### Context

- Request: as above (TODO P46/S46).
- Files changed: the four scripts above, `workflow/dataset_processing/caption_scene_dataset/Snakefile`,
  `config/config.yaml`.
- Verification: dry run, nothing to be done (the param value of `run_table_encoding` is unchanged).

---

## 09:43 — Config checked at startup

Kind: new_feature, documentation

`workflow/Snakefile` now checks `config/config.yaml` at parse time and raises a `ValueError` naming
the key and the allowed values when: a model key does not match `<family>_<size>`
(`re.fullmatch(r".+_[^_]+", ...)`); a model's `modality` is not `language`/`vision`; its
`quantization_method` is not `null`/`4bit`/`8bit`; a `similarity_types` entry is not
`cosine`/`pearson`/`spearman`; `minimum_subjects_per_stimulus` is not between 2 and 8; a dataset's
`number_of_neighbours` is not a positive integer or a list of them (checked after
`dataset_numbers_of_neighbours()`, which still accepts a scalar). New helper
`check_config_value()`. The check that k is smaller than the number of concepts stays in
`compute_blockwise_topk_from_embeddings()`. The README configuration paragraph mentions the checks.

### Context

- Request: as above (TODO P48/S48).
- Files changed: `workflow/Snakefile`, `README.md`.
- Verification: `snakemake -n` with `--config minimum_subjects_per_stimulus=9`,
  `similarity_types=[cosin]` and `nsd_data={number_of_neighbours:[0]}` each stops with the
  `ValueError`; the dry run with the real config passes.

---

## 09:43 — Unused similarity functions removed

Kind: removal

`cosine_similarity()`, `pearson_similarity()` and `spearman_similarity()` deleted from
`workflow/libraries/compute_similarity.py`; no script or Snakefile called them (checked again with
`grep`). The pipeline uses the `*_normalize()` functions and
`compute_blockwise_topk_from_embeddings()`.

### Context

- Request: as above (TODO P49/S49).
- Files changed: `workflow/libraries/compute_similarity.py`.
- Verification: `grep` for the three names in `workflow/` finds nothing; dry run passes.

---

## 09:43 — `code_version()` script hashes include comments: guide corrected

Kind: documentation

`docs/guides/running_and_troubleshooting.md`, "Covered by `code_version()`", said that comments and
blank lines never count. That holds for helper functions (compiled code is hashed), not for
scripts: `script_bytes()` hashes the script and its libraries byte for byte. The section now says
so, and the two removed rules were dropped from its lists.

### Context

- Request: found while implementing S46 (see above).
- Files changed: `docs/guides/running_and_troubleshooting.md`.
- Verification: read `workflow/libraries/code_version.py`; the dry run before the revert flagged
  `make_caption_scene_manifest` with "params have changed since last execution".

---

## 09:54 — Analysis parameters moved from the scripts to the config; last script defaults removed

Kind: refactor, documentation

TODO P47/S47 and the rest of P46/S46.

- `config/config.yaml`: new top-level `chunk_overlap: 256` and `pooling: {language: "avg",
  vision: "cls"}`; new `caption_scene.inside_threshold: 0.999` and `caption_scene.spline_order: 3`.
- `workflow/llm_nearest_neighbours/Snakefile`, rule `get_embeddings`: new params `chunk_overlap`
  and `pool` (`config["pooling"][modality]`), passed as `--chunk_overlap` and `--pool`.
- `workflow/llm_nearest_neighbours/scripts/get_embeddings.py`: `--pool` and `--chunk_overlap` are
  `required = True` (no default 256, no inference of the pooling from the input type); `main()`
  uses `args.pool` directly.
- `extract_caption_scene_parcels.py`: `SPLINE_ORDER` replaced by a required `--spline_order`;
  `compute_caption_scene_sampling_coordinates.py`: `INSIDE_THRESHOLD` replaced by a required
  `--inside_threshold`; both passed from the Caption Scene Snakefile (rules
  `extract_caption_scene_run_parcels`, `compute_caption_scene_sampling_coordinates`).
- `make_caption_scene_manifest.py`: `--onset_shift_s` and `--run_table_encoding` are required (no
  defaults 0.0 and "gbk").
- No value changes, but the changed commands and the edited `code_version()`-hashed script rerun
  every embedding, the Caption Scene chain and everything downstream.
- Docs: `docs/reference/model_embeddings.md` (sections 3 and 4) and the Caption Scene part of
  `docs/reference/fmri_preprocessing.md`, step 3, name the config keys.

### Context

- Request: the user asked to implement P47 and P50, and chose to include the rest of P46.
- Files changed: the scripts, Snakefiles and config above, the two reference pages.
- Verification: dry run parses; `get_embeddings` and the Caption Scene parcel rules are among the
  planned jobs. The embeddings themselves are checked only by the next run.

---

## 09:54 — Manifest rules rerun when the data they are written from changes

Kind: bugfix, documentation

TODO P50/S50. The 6 `write_*_manifest` rules defined with `run:` got a `data` param listing the
module-level variables their helpers read (re-read from the code on 2026-10-08, unchanged since
2026-10-05):

- `write_narratives_parcel_manifest`, `write_narratives_isc_manifest`:
  `[NARRATIVES_TASK_GROUPS, NARRATIVES_PROCESSING_OUTPUT_DIR]`
- `write_nature_stories_parcel_manifest`: `[NATURE_STORIES_SUBJECTS,
  NATURE_STORIES_TRAIN_STORIES, NATURE_STORIES_TEST_STORY, NATURE_STORIES_RUN_METADATA,
  NATURE_STORIES_RESPONSES_DIR, NATURE_STORIES_MAPPERS_DIR, NATURE_STORIES_PROCESSING_OUTPUT_DIR]`
- `write_nature_stories_isc_manifest`: `[NATURE_STORIES_SUBJECTS, NATURE_STORIES_STORIES,
  NATURE_STORIES_PROCESSING_OUTPUT_DIR]`
- `write_nsd_parcel_manifest`: `[NSD_PROCESSING_OUTPUT_DIRECTORY]`
- `write_nsd_isc_manifest`: `[NSD_ISC_DIRECTORY]`

Snakemake's `params` trigger now reruns a manifest when its content would change, whether from a
config value, `minimum_subjects_per_stimulus` or an exclusion file such as `scan_exclude.json`.
`code_version()` is unchanged. Because the param is new, the first run reruns all six manifests and
everything downstream (including the 18.6 h `assemble_nsd_bold`). In
`docs/guides/running_and_troubleshooting.md` the `data` param is described in section 2, and the
"not covered" item and the `MissingOutputException` troubleshooting entry it fixes were removed.

### Context

- Request: as above.
- Files changed: `workflow/dataset_processing/{narratives,nature_stories,nsd_data}_dataset/Snakefile`,
  `docs/guides/running_and_troubleshooting.md`.
- Verification: dry run lists the six manifest rules as planned jobs.

---

## 09:54 — Neighbourhood sizes of Caption Scene and NSD changed to 5, 25, 125

Kind: new_feature, removal, documentation

- `config/config.yaml`: `caption_scene.number_of_neighbours` and `nsd_data.number_of_neighbours`
  changed from `[5, 25, 50, 100]` to `[5, 25, 125]` (both datasets have 1,000 concepts, so k = 125
  passes the k < number of concepts check). The stored neighbour files hold the largest k, so they
  are recomputed at k = 125.
- Deleted at the user's request: every file under `results/alignment_scores/` and
  `results/pictures/` whose name contains `_50NN` or `_100NN` (15,300 files: 15,228 alignment-score
  and p-value files and 72 plots, of both datasets). No other file names carry k.
- The summary TSVs (`all_model_brain_alignment_scores.tsv`, `all_model_model_alignment_scores.tsv`)
  still hold the 50NN and 100NN rows until they are rebuilt by the next run, which drops them and
  adds the 125NN rows.
- `docs/reference/clean_run_duration.md`: job counts of the k-dependent rules scaled to the dry run;
  estimate ~31 h instead of ~32 h (also in `README.md` and the running guide).

### Context

- Request: the user asked to change the list from `[5, 25, 50, 100]` to `[5, 25, 125]` and delete
  the 50NN files; asked which datasets and whether to delete the 100NN files too, they chose both
  datasets and deleting 100NN as well.
- Files changed: `config/config.yaml`, `docs/reference/clean_run_duration.md`, `README.md`,
  `docs/guides/running_and_troubleshooting.md`; the deleted result files.
- Verification: `find results -name '*_50NN*' -o -name '*_100NN*'` finds nothing after the
  deletion; dry run plans the 125NN jobs.
