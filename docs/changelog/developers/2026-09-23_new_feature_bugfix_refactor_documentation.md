# 2026-09-23 — developer changelog

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../../AI_USAGE.md).*

Changes made on this day, in order:

- Require ≥2 distinct subjects per stimulus; NSD parcels extracted in memory; excluded-stimuli file drives both brain and model sides (new_feature)
- NSD invalid-coordinate handling; ISC manifest built from eligible stimuli (bugfix)
- Long-text chunking stops at the end of the text; float32-based constant-signal check in ISC (bugfix)
- Import-block ordering and concise comments (refactor)
- Python bytecode no longer tracked; corrections to the chunking and constant-signal entry (refactor, documentation)
- Fix pandas 3 crash in `relabel_llm_similarity_and_compute_relabelled_llm_alignment_score` (bugfix)
- Diagnosis: `create_isc_manifest` crash on Caption Scene after the two-subject rule (bugfix)

---

## Require ≥2 distinct subjects per stimulus; NSD parcels extracted in memory; excluded-stimuli file drives both brain and model sides

Kind: `new_feature`

### Summary

Before this change, a stimulus was retained whenever it had ≥2 fMRI
observations in total (see `2026-09-21_new_feature_bugfix_refactor_removal_documentation.md`). As a
result, most NSD and Caption Scene "ISC" values were within-subject
test-retest correlations:

- NSD: 65,216 of 66,216 retained stimuli came from a single subject.
- Caption Scene: 7,920 of 8,920 retained stimuli came from a single subject.

A stimulus is now retained only if it was presented to **≥2 distinct
subjects**. Every presentation is still its own observation in the
leave-one-out ISC, including repeats by the same subject; that part is
unchanged.

Expected retained counts, from the current manifests:

| Dataset | Retained | Previously | Subjects per retained stimulus |
|---|---|---|---|
| NSD | 1,000 | 66,216 | 907 × 8, 23 × 6, 70 × 4 |
| NSD presentations | 21,118 | 208,650 | — |
| Caption Scene | 1,000 | 8,920 | all 8 subjects |

### Changes

#### Filters

- `nsd_data_dataset/scripts/make_nsd_manifest.py`
  - Retention now counts distinct subjects (`subject_counts_by_stimulus`)
    instead of total observations.
  - `excluded_stimuli.txt` lists every presented-but-not-retained image.
  - Removed the `output_bold` column and the `--output_root` argument; both
    existed only to name the MNI NIfTIs, which are no longer written.
  - The warning now reports a count rather than printing all 65k IDs.
- `caption_scene_dataset/scripts/make_caption_scene_manifest.py`
  - Retention uses `groupby("stimulus_id")["subject"].nunique() >= 2`.
  - The existing `excluded_stimuli` computation (All_images_480 minus
    retained) and the run manifests already derive from the filtered
    manifest. Dropped stimuli are therefore never split, parcellated or
    ISC'd.
- `narratives_dataset/Snakefile`
  - `NARRATIVES_TASK_GROUPS` keeps only tasks whose scans come from ≥2
    distinct subjects. All 18 current tasks pass.
  - `parcel_outputs_for_task` uses `.get(task, [])`, so a dropped task no
    longer raises `KeyError` at parse time.
  - `write_narratives_problematic_stimuli` now writes
    `problematic_subtasks ∪ (transcript stems − retained tasks)`. It depends
    on the renamed-transcripts dir (`NARRATIVES_STIMULI_READY`) and has the
    retained task list as a param, so it reruns whenever that set changes.
- Nature Stories: unchanged. `compute_nature_stories_isc.py` already
  requires all `expected_subjects` for every story.

#### NSD: `assemble_nsd_bold` now writes parcel time series

- `scripts/assemble_nsd_bold.py`
  - Each occurrence is mapped func1pt8→MNI exactly as before.
  - It is then reduced to Schaefer parcels in memory, via
    `libraries.fmri_processing.get_resampled_parcel_matrix` with the atlas
    resampled onto the nsdcode MNI grid (`nsd_mni_affine()` reproduces the
    affine `nsd_write_vol` used to write).
  - Only the `(n_vols, n_rois)` float32 arrays are written, at the existing
    `parcel_time_series` paths.
  - Previous output size: about 117–237 MB per occurrence, roughly 24 TB for
    the old manifest. New output: 2.4 KB per occurrence.
  - Mapping now happens in float32 instead of float64. The old path wrote
    float64 NIfTIs that `extract_parcels` read back as float32 anyway.
- `scripts/extract_nsd_parcels.py` and rule `extract_nsd_parcels`: removed.
- `Snakefile`
  - `write_nsd_parcel_manifest` now carries
    `source_bold/start_vol/end_vol/n_vols` instead of `bold_file`.
  - `assemble_nsd_bold` takes the parcel manifest, adds the atlas params and
    outputs `.parcels_done`.
  - `NSD_BOLD_DONE` is removed.
- Verified on `sub-03_task-nsd-00001_rep-01`:
  - the new in-memory parcels vs `extract_parcels` on the old MNI NIfTI give
    a maximum absolute difference of `0.0`;
  - the affine matches the old file's.

#### Excluded-stimuli file as the single source of truth

- `get_embeddings.py` already skipped every stem listed in
  `config[dataset]["excluded_stimuli"]`, and `get_embeddings` already
  declared that file as an input. Neither was changed.
- `isc_nearest_neighbours/scripts/create_isc_manifest.py` (and its
  checkpoint) now takes `--excluded_stimuli` and drops ISC files for listed
  stimuli.
  - Without this, stale per-stimulus ISC files from earlier runs would be
    globbed back in. Caption Scene's `compute_caption_scene_isc` outputs are
    per-file, so Snakemake never deletes them.
  - Those stale files would then clash with the embeddings
    (`compute_alignment_scores` raises on differing concept sets).

### Follow-ups

- `results/mind/nsd_data/single_stimulus_bold_mni/` (1.8 TB) is orphaned
  and safe to delete. Stale per-stimulus files under
  `results/mind/{nsd_data,caption_scene}/parcels/` and
  `results/mind/caption_scene/isc/` are no longer read. The same is true of
  the dropped stimuli's files under
  `results/mind/caption_scene/intermediate_files/single_stimulus_bold/`.
- `number_of_neighbours` must be ≤ N−1 (about 999) for NSD and Caption
  Scene.

### Rerunning

The changed filters live in Python scripts that are called from `shell:`
rules. Snakemake's code-change trigger does not look at those scripts, so it
will not rerun the manifest steps by itself. Force them:

```bash
snakemake --use-conda --cores <N> --forcerun make_nsd_manifest make_caption_scene_manifest
```

Everything downstream is then rebuilt from the new manifests.

### Verification performed

- `python -m py_compile` on every modified script.
- A `snakemake -n` dry run: the DAG resolves with the new NSD rule chain
  `make_nsd_manifest → write_nsd_parcel_manifest → assemble_nsd_bold →
  write_nsd_isc_manifest → compute_nsd_isc`, with no `extract_nsd_parcels`.
  The unchanged Narratives ISC outputs are not rescheduled, which confirms
  all 18 tasks pass the filter.
- A numerical check of the new in-memory NSD parcel extraction against the
  old NIfTI-based path on one existing presentation (see above).
- `create_isc_manifest.py` run on the real 8,920-file Caption Scene ISC
  directory with a 3-stimulus exclusion list: 8,917 rows were written and
  none of the excluded stimuli appeared.
- Retained-stimulus counts were computed from the manifests already on disk
  (from before this change).

**Not verified:** no pipeline stage was actually executed with the new code.
In particular, `make_nsd_manifest`, `make_caption_scene_manifest` and a full
`assemble_nsd_bold` run have not been run yet.

### Context

- Basis: a review of the whole repository earlier in the same session, then explicit instructions from the developer (Jonas Salvalaggio) on which changes to make.
- Verification: limited to the checks listed under "Verification performed".

---

## NSD invalid-coordinate handling; ISC manifest built from eligible stimuli

Kind: `bugfix`

Follow-up to `2026-09-23_new_feature_bugfix_refactor_documentation.md`, prompted by an
external review of commit `697af46`.

### NSD: invalid transform coordinates re-masked after every volume

- `nsd_data_dataset/scripts/assemble_nsd_bold.py`
  - `nsdcode.interp_wrapper()` sets invalid (non-finite) coordinates to `1` in
    place and marks them invalid only in the output of that one call.
    `map_occurrence_to_mni()` reused one copy of the coordinates for every
    volume of an occurrence, so from the second volume on, invalid locations
    would have been sampled as if they were valid.
  - `get_subject_mni_transform()` now records the invalid mask once per
    subject and stores all-finite coordinates, which `interp_wrapper()` has
    nothing to change in. `map_occurrence_to_mni()` re-applies the mask
    (→ `badval`) after every interpolation. The `reusable` flag and the
    per-occurrence copy are removed.
- **Impact on existing outputs: none.** None of the 8 subjects' func1pt8→MNI
  transforms contains an invalid coordinate (0 of 7,221,032 for each), so the
  old copy path never ran and the output is unchanged.
- Verified on a synthetic volume and transform with 50 invalid coordinates:
  - new output vs `interp_wrapper()` called with fresh raw coordinates for
    each volume: maximum absolute difference `0.0`;
  - the old reuse pattern differed by about 925 and 1,068 on volumes 2 and 3.

### ISC manifest: built from the eligible stimuli, not from the ISC directory

- `isc_nearest_neighbours/scripts/create_isc_manifest.py` now takes
  `--stimuli_dirs`.
  - The eligible set is every stimulus file stem in each directory minus
    `excluded_stimuli`. This is the same selection as
    `get_embeddings.load_stimuli()`.
  - It raises an error if the modality directories disagree, or if any
    eligible stimulus has no ISC file.
  - ISC files for stimuli that are not eligible are ignored and counted.
- `isc_nearest_neighbours/Snakefile`, `create_isc_manifest`: adds the
  `stimuli_ready` input and the `stimuli_dirs` param.
- Verified on the current on-disk data:
  - Caption Scene 8,920 rows, Narratives 18, Nature Stories 11: unchanged.
  - NSD now fails with `65701 of 66216 eligible stimuli have no ISC file`,
    because only 515 ISC files from a partial old-filter run exist. The
    previous version would have quietly written a 515-row manifest.
- `snakemake -n --cores 32` resolves.

### Not changed (review points left to the developer)

- NSD and Caption Scene `number_of_neighbours` stay `[5, 25, 50, 100]`.
  Previously they were `[5,50,250,500,1000]` (NSD) and
  `[5,50,500,2500,5000]` (Caption Scene). With about 1,000 retained stimuli,
  `k ≤ 999` is valid, so 250 and 500 could be restored. This is an
  experimental-design choice.
- NSD extraction failures still stop the job; no observation is ever
  dropped, so the two-subject criterion evaluated on presentations holds for
  what reaches the ISC. If observation-level QC exclusion is added later, the
  subject count must be re-checked after it.

---

## Long-text chunking stops at the end of the text; float32-based constant-signal check in ISC

Kind: `bugfix`

> **Correction:** some statements below (which texts change, equal
> weighting, what counts as a flat signal) were inaccurate; see
> [`2026-09-23_new_feature_bugfix_refactor_documentation.md`](2026-09-23_new_feature_bugfix_refactor_documentation.md).

Follow-up to `2026-09-23_new_feature_bugfix_refactor_documentation.md`,
addressing the two code points the external review of commit `60bb6c5` left
open.

### Long-text chunking: no redundant final chunk

- `llm_nearest_neighbours/scripts/get_embeddings.py`, `embed_long_text()`
  - The loop `for start in range(0, n_tokens, step)` kept going after a chunk
    had already reached the end of the text. The extra chunk lay entirely
    inside the previous one. It re-embedded tokens that were already covered
    and gave them extra weight in the length-weighted mean.
  - The loop now breaks once `start + chunk_token_length >= n_tokens`.
- When the old loop over-ran: with `step = chunk_token_length - overlap`, it
  added one redundant chunk exactly when `n_tokens > step` and
  `0 < n_tokens mod step <= overlap`. The CLI default is `--chunk_overlap 256`
  (not overridden by the `get_embeddings` rule), and
  `chunk_token_length = max_length - 1` when the tokenizer has a BOS token.
- Checked by simulating the loop with `chunk_token_length = 511` and
  `overlap = 128` (step 383). The old loop added a redundant chunk for 400,
  511, 800, 894 and 2,000 tokens, but not for 100, 383, 512 or 895. The new
  loop drops exactly that chunk, and every token is still inside some chunk.
- **Impact on existing outputs:**
  - Embeddings change for text stimuli whose token count meets the condition
    above.
  - The `n_chunks` metadata column in `*_embeddings.parquet` goes down by one
    for those stimuli.
  - Stimuli that fit in a single chunk, and all image stimuli, are unchanged.

### ISC: constant-signal detection

- `libraries/fmri_processing.py`
  - The old check was `np.isclose(x, x[0])` with default tolerances
    (`rtol = 1e-5` against the first sample). On raw-scale BOLD, which the
    pipeline does not z-score, a parcel around 1000 varying by less than about
    0.01 was treated as constant and its correlation set to 0.
  - New `is_constant_signal()`: a signal counts as constant when its range
    over time is at most `8 × float32 eps` (about 9.5e-7) times its maximum
    absolute value. In other words, it varies only by float32 rounding noise.
    All-zero and exactly constant parcels are still caught.
  - `compute_leave_one_out_isc()` and `safe_pearsonr()` both use it, so they
    stay equivalent as the docstring says (`safe_pearsonr` is currently not
    called anywhere).
- Verified on synthetic data (8 subjects × 20 TRs):
  - normal-amplitude signals: output identical to the old implementation
    (max abs difference `0.0`);
  - all-zero and exactly constant parcels: still 0;
  - a parcel around 1000 with a shared signal of range about 0.008: the old
    check gave 0, the new one gives ISC 0.94.
- **Impact on existing outputs:** only parcels the old tolerance wrongly
  flagged change. How many there are in the real data has not been checked.

### Rerunning

Both scripts are called from `shell:` rules, so Snakemake will not rerun
them by itself. The NSD and Caption Scene manifests have to be regenerated
anyway (see the previous entry), so ISC is recomputed for those datasets
downstream of that. For Narratives, Nature Stories and the text embeddings,
force the ISC and embedding rules, e.g.:

```bash
snakemake --use-conda --cores <N> --forcerun get_embeddings compute_narratives_isc compute_nature_stories_isc
```

### Not changed

- NSD ISC still treats each presentation as its own observation, including
  repeats by the same subject. This is a deliberate methodological choice.
  The manuscript should report the number of observations and the number of
  distinct subjects separately.

### Context

- Basis: an external review of commit `60bb6c5`, which the assistant first checked against the code and the data on disk, then the developer's instructions (Jonas Salvalaggio) in the same session.
- Verification: only the synthetic checks listed above. No pipeline stage was run with the new code, and the effect on the real data was not measured.

---

## Import-block ordering and concise comments

Kind: `refactor`

Style-only change across the Python sources in `workflow/` (27 files). No
statement other than imports and comments was touched, so no pipeline
output changes. The rules are summarised in `README.md` under
[Code conventions](../../../README.md#code-conventions).

### Import blocks

Every file's top-level import block is now split into up to four groups,
in this order, separated by one blank line:

| Group | Contents | Modules currently used |
|---|---|---|
| 1. Standard library | anything in `sys.stdlib_module_names` | `argparse`, `collections`, `concurrent.futures`, `gc`, `hashlib`, `json`, `math`, `os`, `pathlib`, `re`, `sys`, `warnings` |
| 2. General scientific stack | general-purpose numeric/data/plotting | `h5py`, `matplotlib`, `numpy`, `pandas`, `PIL`, `pyarrow`, `scipy`, `torch` |
| 3. Domain-specific | neuroimaging, speech, LLM tooling | `huggingface_hub`, `netneurotools`, `nibabel`, `nilearn`, `nsdcode`, `praatio`, `transformers` |
| 4. Project | this repository's own helpers | `libraries.*` |

Within a group:

- lines are sorted case-insensitively by **module name**, regardless of the
  `import x` / `from x import y` form. So `from pathlib import Path` now
  precedes `import re`, and `PIL` sorts between `pandas` and `pyarrow`;
- names inside a `from x import a, b` are sorted case-insensitively
  (e.g. `as_completed, ProcessPoolExecutor`);
- parenthesised multi-line imports keep their one-name-per-line layout.

`torch` is in group 2 and `transformers` in group 3. That is a judgment
call: `torch` is treated as a general array/compute framework.

Notable moves:

- `nibabel` (including `nibabel.freesurfer.io`) and `nilearn` moved from
  group 2 into group 3 wherever they were mixed with `numpy`/`pandas`.
- `scipy` moved up from the domain block into group 2 in
  `libraries/fmri_processing.py` and
  `dataset_processing/nature_stories_dataset/scripts/extract_nature_stories_parcels.py`.
- The out-of-order `nsdcode.*` imports in `assemble_nsd_bold.py` and the
  `libraries.*` imports in `plot_alignment_heatmap.py`,
  `plot_empirical_p_value_heatmap.py` and `plot_spearman_alignment.py` are
  now sorted.
- `create_isc_dataframe.py` had `numpy`/`pandas` above the standard library.
- Stray blank lines inside group 1 (e.g. after `import argparse` in the NSD
  scripts) and between a shebang and the first import were removed.

The reordering was done by a one-off script, which is not committed. It
parsed each file with `ast`, took the contiguous top-level
`Import`/`ImportFrom` nodes, and aborted on any file where a comment or
statement sat inside that range. Nothing enforces the rule going forward:
no `isort`/`ruff` config was added, and neither tool is in the environment.
With `isort`, the same layout would need custom sections
(`sections=FUTURE,STDLIB,THIRDPARTY,DOMAIN,FIRSTPARTY`, `known_domain=...`,
`known_first_party=libraries`, `force_sort_within_sections=true`,
`case_sensitive=false`).

### Comments

- Comments stay as `#` lines. Converting multi-line comments to `"""`
  blocks was considered and dropped: outside a docstring position they are
  no-op string expressions (flagged by pylint `W0105`) and interpret
  backslash escapes unless written `r"""`.
- About 20 multi-line comments were shortened to 1–3 lines, keeping the
  *why* and dropping narrative. The largest reductions:
  - `assemble_nsd_bold.py`: transform-cache rationale (7 → 3 lines),
    `interp_wrapper()` invalid-coordinate handling (7 → 3), occurrence
    grouping (7 → 3), plus four 2–3 line comments reduced to 1–2;
  - `libraries/fmri_processing.py`: `CONSTANT_SIGNAL_RTOL` rationale (5 → 3);
  - `compute_llm_llm_empirical_p_value.py` and
    `relabel_llm_similarity_and_compute_relabelled_llm_alignment_score.py`:
    why top-k is recomputed on the closed concept subset (5 → 2 each). The
    Snakemake wildcard/output note (4 → 2). This rewording also dropped a
    stale reference to "the plan file / commit message";
  - `create_isc_manifest.py`, `get_embeddings.py`,
    `compute_spearman_alignment_with_empirical_p_value.py`,
    `compute_llm_mind_alignment_score.py`, `make_nsd_manifest.py`,
    `make_caption_scene_manifest.py`, `compute_nsd_isc.py`,
    `convert_nature_stories_textgrids.py`.
- Left unchanged: single-line comments, the Praat TextGrid format examples
  in `convert_nature_stories_textgrids.py`, the `##### … SIMILARITY #####`
  section headers, all docstrings, and two commented-out `print` blocks
  (`compute_narratives_isc.py:94`, `compute_llm_mind_alignment_score.py`).

### `.gitignore`

- Added repository-wide `__pycache__/` and `*.py[cod]` patterns.
  `2026-09-23_new_feature_bugfix_refactor_documentation.md` says these
  were added, but commit `6b2bc6e` kept only the path-specific
  `workflow/libraries/__pycache__/` rule. As a result, 35 `.pyc` files
  generated by this session's `py_compile` check under `*/scripts/__pycache__/`
  were not ignored and ended up staged. They were unstaged and deleted
  before this entry was written.

### Verification

- `python3 -m py_compile` (Python 3.12) passes on every `.py` file under
  `workflow/` except `envs/`.
- Every `+`/`-` line in the diff of `workflow/` matches
  `^\s*(#|import |from \S+ import|$)`, i.e. it is an import, a comment or
  a blank line.
- No pipeline stage was run. Reordering imports could in principle
  matter if a module relied on import-time side effects of an earlier
  one. None of the moved imports is known to do so, but this was not
  tested.

### Context

- Basis: the developer's (Jonas Salvalaggio) style requests in the same session. The assistant proposed the rules first, the developer approved them, and then asked to keep `#` comments instead of `"""` blocks.
- Verification: as listed above. No pipeline stage was run.

---

## Python bytecode no longer tracked; corrections to the chunking and constant-signal entry

Kind: `refactor`, `documentation`

> **Correction:** the repository-wide `.gitignore` patterns described below
> were not in commit `6b2bc6e`; they were added later, see
> [`2026-09-23_new_feature_bugfix_refactor_documentation.md`](2026-09-23_new_feature_bugfix_refactor_documentation.md).

Follow-up to `2026-09-23_new_feature_bugfix_refactor_documentation.md`
(commit `ea9145a`), prompted by an external review of that commit. No
pipeline code changed in this entry.

### Python bytecode removed from Git

- `.gitignore`: the path-specific `workflow/libraries/__pycache__/` rule is
  replaced by repository-wide `__pycache__/` and `*.py[cod]` patterns.
- Removed from the index (and deleted from the working tree), since all
  three were committed by mistake:
  - `workflow/llm_nearest_neighbours/scripts/__pycache__/get_embeddings.cpython-313.pyc` (added in `ea9145a`)
  - `workflow/dataset_processing/nsd_data_dataset/scripts/__pycache__/assemble_nsd_bold.cpython-314.pyc` (added in `12181e1`)
  - `workflow/llm_mind_alignment/scripts/__pycache__/aggregate_all_p_value_outputs.cpython-314.pyc` (added in `29b7cc0`)
- After this change, `git ls-files | grep pycache` returns nothing.
- Why only `workflow/libraries/__pycache__/` should appear during a normal
  run: rules call scripts as `python3 <script>.py` from `shell:`, and CPython
  writes bytecode only for imported modules, never for the `__main__`
  script. The scripts import `libraries/` modules, so that is the only cache
  a pipeline run produces. No file in `workflow/` imports
  `get_embeddings`, `assemble_nsd_bold` or `aggregate_all_p_value_outputs`,
  so their caches came from ad-hoc imports during testing.
  `workflow/envs/LLMmind_project/` also contains caches, but that is the
  conda prefix and was already ignored.

### Corrections to the `ea9145a` changelog entries

The code in `ea9145a` is unchanged. Three statements in its documentation
were inaccurate.

#### Which embeddings the chunking fix changes

- The entry said that stimuli fitting in a single chunk are unchanged. That
  is wrong: `get_embeddings.py` routes every text stimulus through
  `embed_long_text()`, whatever its length.
- With `L = chunk_token_length` and the default `--chunk_overlap 256`
  (`step = L - 256`), the old loop started a second chunk at `step` for any
  text with `L - 255 <= n_tokens <= L`, although the first chunk already
  covered the whole text. Checked by simulating both loops: for `L = 511`
  every length from 256 to 511 tokens goes from 2 chunks to 1, and for
  `L = 2047` every length from 1,792 to 2,047.
- So short texts whose length falls in that window change too, along with
  the longer texts described in the original entry. Image stimuli are
  unaffected.

#### Overlap weighting

- The final embedding is still the chunk-length-weighted mean of
  overlapping chunks. Tokens in an overlap region contribute to two chunk
  embeddings, and tokens at the start and end of the text to only one. The
  fix removes the redundant final chunk. It does not make every token
  count equally, as the user entry claimed.

#### Constant-signal threshold

- `is_constant_signal()` treats a signal as constant when
  `ptp(x) <= 8 * eps(float32) * max|x|`, which is about 9.5e-7 relative. At
  a baseline around 1,000 that is a range of about 0.00095, roughly 16
  float32 ulps. It is a near-constancy tolerance, not a test for
  rounding noise only. A real fluctuation smaller than that is still
  zeroed.
- Leaving the tolerance as it is, or switching to an exact check
  (`np.ptp(x, axis=axis) == 0`), is an open methodological decision. It
  should be made after counting how many parcels the current rule zeroes on
  real processed BOLD, which has not been done yet. An exact check would
  still catch all-zero and exactly constant parcels: the leave-one-out mean
  `y` of identical signals is computed the same way at every time point,
  so it stays exactly flat.
- `README.md` (`dataset_processing/<dataset>/` and `llm_nearest_neighbours/`
  sections) has been updated to match. The `ea9145a` entries are left
  as written, with a note at the top pointing here.

### Still to validate

The review recommends checking regenerated results before changing more
code:

- retained stimulus IDs should agree across the manifests, the ISC outputs
  and the embeddings;
- measure how often the constant-signal rule returns 0 on real data;
- compare the new NSD parcel outputs with the previous extraction method on
  representative presentations.

### Context

- Basis: an external review of commit `ea9145a`, which the assistant checked against the source (reading `get_embeddings.py` and `fmri_processing.py`, and simulating the old and new chunking loops), and the developer's instructions (Jonas Salvalaggio) in the same session.
- Verification: `git ls-files` shows no tracked bytecode; the chunk-count simulation described above. No pipeline stage was run.

---

## Fix pandas 3 crash in `relabel_llm_similarity_and_compute_relabelled_llm_alignment_score`

Kind: `bugfix`

### Summary

The 2026-09-23 run (`.snakemake/log/2026-09-23T112911.353357.snakemake.log`)
stopped at 358/8031 steps. Rule
`relabel_llm_similarity_and_compute_relabelled_llm_alignment_score` failed
for `dataset=nature_stories, model=bloom_560m, stimuli_type=language,
similarity_type=cosine` (k=3) with:

```
File ".../relabel_llm_similarity_and_compute_relabelled_llm_alignment_score.py", line 22, in encode_brain_nearest_neighbours
    neighbours_by_concept = brain_nearest_neighbours_df.groupby("concept", sort=False)["neighbour"].agg(list).to_dict()
TypeError: unhashable type: 'list'
```

The Snakemake log shows only `CalledProcessError`. The traceback above came
from re-running the rule's shell command by hand in its conda env
(`.snakemake/conda/8c935a13331796cb2f07682d758b4d59_`).

### Root cause

- `isc_{similarity_type}_nearest_neighbours.parquet` stores `concept` and
  `neighbour` as `category`, a deliberate storage choice
  (`libraries/compute_nearest_neighbours.py`, shared `CategoricalDtype`).
- The rule's env resolves to **pandas 3.0.5, Python 3.14**, because
  `envs/llm_mind_alignment_environment.yaml` does not pin `pandas`.
- In pandas 3, `SeriesGroupBy.agg(list)` on a categorical column tries to
  cast the aggregated result back to the column's `CategoricalDtype`. That
  means looking each per-group `list` up in the categories index, and a list
  is unhashable.
- The input data is fine: 11 concepts × 3 neighbours for Nature Stories.

### Change

`workflow/llm_mind_alignment/scripts/relabel_llm_similarity_and_compute_relabelled_llm_alignment_score.py`,
`encode_brain_nearest_neighbours`:

```diff
-    neighbours_by_concept = brain_nearest_neighbours_df.groupby("concept", sort=False)["neighbour"].agg(list).to_dict()
+    neighbours_by_concept = brain_nearest_neighbours_df.groupby("concept", sort=False, observed=True)["neighbour"].apply(list).to_dict()
```

- `.apply(list)` returns an object Series of Python lists and does not cast
  back to the categorical dtype.
- `observed=True` keeps only categories that actually occur as a group
  instead of the full category set. It was already the pandas 3 default;
  passing it explicitly guards against older pandas versions, where the
  default was `False`.
- Behaviour is otherwise unchanged:
  - neighbour order within each group follows row order, which is the
    stored similarity ranking;
  - the missing-concept and too-few-neighbours checks further down still
    run, via `.get(concept, [])`.

No other workflow script uses `.agg(list)`. The other `groupby` call sites
were not audited for pandas-3 categorical behaviour.

### Verification performed

- Reproduced the failure by re-running the failing command with
  `--number_of_relabellings 2`, output written to a scratch directory.
- Confirmed in isolation, against the same input file, that `.agg(list)`
  raises the `TypeError` and that `.apply(list)` returns the expected
  mapping (e.g. `alternateithicatom → ['life', 'avatar', 'undertheinfluence']`).
- Ran the patched script end to end with the exact production arguments
  (`--number_of_neighbours 3 --number_of_relabellings 1000 --random_seed 37`),
  output written to a scratch directory. It completed all 1000 relabellings
  and wrote an 11,000 × 7 parquet with the expected columns.

**Not verified:**

- The Snakemake workflow has not been restarted.
- No other `(dataset, model, similarity_type)` combination of this rule has
  been run with the patch.
- Results were not compared numerically against a pandas-2 run.

### Follow-ups

- Restart with `--rerun-incomplete`. The crashed run left entries in
  `.snakemake/incomplete`.
- Consider pinning `pandas` (and `python`) in
  `envs/llm_mind_alignment_environment.yaml`. Until then, any env rebuild
  can pull in a new major version.
- Other scripts that `groupby` on categorical columns from the
  nearest-neighbour parquets may hit similar pandas-3 differences.

### Context

- Basis: the Snakemake log of the crashed run, a manual re-run of the failing command in the rule's conda env, and the developer's (Jonas Salvalaggio) go-ahead to apply the fix.
- Verification: limited to the checks listed under "Verification performed".

---

## Diagnosis: `create_isc_manifest` crash on Caption Scene after the two-subject rule

Kind: `bugfix`

### Summary

No code was changed. This entry records a diagnosis, so that the next person
who hits the same error can find the cause and the fix.

After the two-subject retention change (commit `697af46`, see
`2026-09-23_new_feature_bugfix_refactor_documentation.md`), the checkpoint
`create_isc_manifest` failed for `dataset=caption_scene` with:

```
File "workflow/isc_nearest_neighbours/scripts/create_isc_manifest.py", line 68, in main
    raise FileNotFoundError(...)
FileNotFoundError: 7920 of 8920 eligible stimuli have no ISC file in results/mind/caption_scene/isc,
e.g. ['COCO_train2014_000000000036', 'COCO_train2014_000000000529', ...]
```

### Root cause

The rule filters got out of sync with the files on disk:

| Artefact | State at crash time |
| --- | --- |
| `make_caption_scene_manifest.py` | New code (commit `697af46`, 2026-09-23 10:06): drops stimuli with `subject.nunique() < 2` |
| `intermediate_files/manifest/csd_events_manifest.tsv` | Old output (2026-09-13): 8,920 stimuli, of which 1,000 were seen by 8 subjects and 7,920 by 1 subject |
| `resources/datasets/caption_scene_dataset/V1/excluded_stimuli.txt` | Old output (2026-09-13): 5,164 entries, so 14,084 − 5,164 = 8,920 eligible |
| `results/mind/caption_scene/isc/`, `parcels/` | Already pruned to the 1,000 two-subject stimuli (dir mtime 2026-09-23 10:30) |

`create_isc_manifest.py` builds the expected stimulus set from each
`stimuli_dir` minus `excluded_stimuli`, so it still expected 8,920 ISC files.
The 7,920 it reported as missing are exactly the single-subject stimuli.

The documented `--forcerun make_nsd_manifest make_caption_scene_manifest`
step had not been run. Because the manifest script is called from a
`shell:` rule, Snakemake's code trigger does not see edits to it. Its
outputs were newer than its inputs, so nothing rebuilt it.

The script's missing-ISC check behaved as intended: it stopped the run
instead of silently computing neighbours over a mismatched stimulus set.

### Fix (operational, no code change)

Regenerate the Caption Scene manifest checkpoint, so that
`excluded_stimuli.txt` lists 13,084 stimuli and 1,000 remain eligible:

```bash
snakemake --use-conda --cores <N> --forcerun make_caption_scene_manifest -n   # inspect first
snakemake --use-conda --cores <N> --forcerun make_caption_scene_manifest
```

What to expect downstream:

- The new manifest mtime reschedules `split_caption_scene_bold_by_run_manifest`,
  `extract_caption_scene_parcels`, `compute_caption_scene_isc` and
  `write_caption_scene_stimuli_transcripts`. BOLD splitting is the expensive
  step.
- The language `stimuli_dir` can stay at 8,920 transcripts:
  `eligible_stimuli_in_dir` subtracts `excluded_stimuli` per directory, so
  both the language and vision dirs resolve to the same 1,000 stems.
- `llm_nearest_neighbours` rules take `excluded_stimuli` as an input and
  rerun on its new mtime. Embeddings built over the 8,920-stimulus set
  are stale.
- Cheaper alternative, not tested: run only the manifest script by hand,
  then `snakemake --touch` the downstream Caption Scene outputs to keep the
  existing 1,000 parcel/ISC files. This is only valid if those files were
  produced by the current parcel/ISC code.

### Verification performed

- Counted distinct subjects per `stimulus_id` in the manifest: 1,000 with
  8 subjects and 7,920 with 1. This matches the error's 7,920 / 8,920.
- `results/mind/caption_scene/isc/` holds 1,000 `*_isc_mean.npy` files.
- Line counts: 14,084 images in `All_images_480`, 8,920 transcripts,
  5,164 lines in `excluded_stimuli.txt`.
- Confirmed that `make_caption_scene_manifest.py` (lines 270–306) contains
  the `>= 2` subject filter.

**Not verified:**

- No `snakemake` dry run or rerun: `snakemake` was not on the assistant
  shell's `PATH`.
- The Caption Scene pipeline has not been rebuilt, and the fix above has not
  been confirmed end to end.
- NSD was not checked for the same staleness. If `make_nsd_manifest` was not
  forced either, the same error may appear for `nsd_data`.

### Follow-ups

- Run the forced rebuild for `make_caption_scene_manifest`, and for
  `make_nsd_manifest` if NSD's manifest also predates `697af46`.
- Consider adding the manifest scripts as explicit rule `input:` entries.
  Snakemake would then reschedule these checkpoints when the scripts change,
  and this class of failure would go away.

### Context

- Basis: the traceback pasted by the developer (Jonas Salvalaggio), and read-only inspection of the Snakefiles, scripts, manifest, ISC directory, file timestamps and git history.
- Verification: limited to the checks listed under "Verification performed". No commands that modify the pipeline were run.
