# 2026-09-21 — developer changelog

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../../AI_USAGE.md).*

Changes made on this day, in order:

- Deduplicate boxplot summary stats; rewrap long signatures (refactor)
- Add top-level README.md (documentation)
- Add base environment spec at workflow/envs/ (new_feature)
- Mark degenerate (zero-spread) boxplots; remove per-run diagnostic logging (new_feature, removal)
- Unify empirical-p-value RNG and formula between llm-llm and llm-mind (bugfix)
- Document required input data and per-module breakdown in README (documentation)
- NSD: drop dataset-specific repetition constraint, compute ISC from all available observations (new_feature)

---

## Deduplicate boxplot summary stats; rewrap long signatures

Kind: `refactor`

### Summary

Follow-up cleanup after the `small cleanup` commit series (`48e6a42`–`9ebd759`),
which had collapsed several multi-line function signatures to single lines and
left a statistics-logging block duplicated across two plotting scripts.

### Changes

#### `workflow/libraries/visualisation_utils.py`

- Added `log_boxplot_summary_statistics(labels, boxplot_values)`. Given the
  per-label list of boxplot value arrays, it prints `n`, `unique`, `min`, `Q1`,
  `median`, `Q3`, `max`, and `IQR` (9 decimal places) for each label, in the
  same format previously inlined separately in two scripts.

#### `workflow/visualisation/scripts/plot_spearman_alignment.py`
#### `workflow/visualisation/scripts/plot_concept_alignment_enrichment.py`

- Replaced the inline `for label, values in zip(labels, boxplot_values): ...`
  print block in each script with a call to
  `log_boxplot_summary_statistics(labels, boxplot_values)`.
- No change in output format or values — this is a pure extraction. The two
  scripts previously carried byte-for-byte identical logging code that had to
  be edited in lockstep; a future format change (e.g. adding a mean, changing
  precision) now only needs to happen in one place.

#### `workflow/libraries/compute_alignment.py`
#### `workflow/libraries/compute_nearest_neighbours.py`

- Rewrapped three function signatures that the prior cleanup pass had
  collapsed past ~100 characters, back to one-argument-per-line (matching the
  style used elsewhere in these files, and the style these functions had
  before commit `9ebd759`):
  - `compute_alignment_scores(nearest_neighbours_df_1, nearest_neighbours_df_2, number_of_neighbours)`
  - `compute_mean_alignment_score(neighbour_mask, neighbours, concept_indices, number_of_neighbours)`
  - `relabel_nearest_neighbours(observed_neighbours, permutation, inverse_permutation, concept_indices)`
- No behavioral change — formatting only.

### Verification

- `ast.parse` on all five touched files confirms they remain syntactically
  valid.
- Manually diffed against commit `9ebd759` to confirm the restored signatures
  match the pre-collapse style and argument order.

### Files touched

- `workflow/libraries/visualisation_utils.py`
- `workflow/visualisation/scripts/plot_spearman_alignment.py`
- `workflow/visualisation/scripts/plot_concept_alignment_enrichment.py`
- `workflow/libraries/compute_alignment.py`
- `workflow/libraries/compute_nearest_neighbours.py`

---

## Add top-level README.md

Kind: `documentation`

### Summary

The project previously had no root-level `README.md` and no reference
documentation of any kind (verified via `find . -iname "*.md" -o -iname
"README*"` at the project root, excluding the conda env under
`workflow/envs/LLMmind_project` and third-party model-card READMEs under
`resources/models/*`). Added a `README.md` to serve as the entry point for
the repository.

### Source material

Content was derived entirely from static inspection of the existing
repository — no code changes were made:

- `workflow/Snakefile` — top-level rule graph (`PAIRINGS`,
  `LLM_LLM_PAIRINGS`, `HEATMAP_PAIRINGS`, `SPEARMAN_PAIRINGS`, `rule all`)
  and the `include:` order, used to derive the pipeline stage list and
  the repo-layout module descriptions.
- `config/config.yaml` — `datasets`, `models`, `similarity_types`,
  `number_of_relabellings` — used for the Datasets/Models sections.
- `.envrc` and `workflow/*/envs/*.yaml` — used for the Setup section
  (conda env activation, per-rule `conda:` environments).
- `.gitignore` — confirmed `resources/`, `results/`, and the conda env dir
  are untracked, reflected in the repo-layout notes.

### Changes

#### `README.md` (new)

Added at the project root with the following sections: Overview (pipeline
purpose and 6-step processing summary), Repository layout, Datasets, Models,
Setup, Running the pipeline, Outputs, Documentation (links to
`docs/changelog/developers/` and `docs/changelog/users/`).

### Notes / caveats for future edits

- The Overview section's description of pipeline purpose and stage ordering
  was inferred from rule/file naming and the `include:` order in
  `workflow/Snakefile`, not from any existing prose documentation (none
  existed) — verify against domain knowledge before treating it as
  authoritative.
- No dependency-pinning or install instructions beyond the existing
  conda-env mechanism were documented, since none exist in the repo.
- Keep this file in sync with `workflow/Snakefile` and `config/config.yaml`
  when datasets, models, or pipeline stages are added or removed — the
  README enumerates both by name.

### Files touched

- `README.md` (new)

---

## Add base environment spec at workflow/envs/

Kind: `new_feature`

### Summary

The base environment used to run Snakemake itself
(`workflow/envs/LLMmind_project`, referenced by `.envrc` and documented in
`README.md`'s Setup section) existed only as a materialized conda prefix on
disk — there was no versioned spec describing its contents, so it could not
be recreated or reviewed. Added a minimal conda environment YAML under
`workflow/envs/` to serve as that spec.

### Changes

#### `workflow/envs/LLMmind_project_environment.yaml` (new)

```yaml
channels:
  - conda-forge
  - nodefaults
dependencies:
  - python
  - snakemake-minimal
```

Deliberately minimal: only `python` and `snakemake-minimal`. Per-rule conda
environments (numpy/pandas/pyarrow/etc., e.g.
`workflow/isc_nearest_neighbours/envs/isc_nearest_neighbours_environment.yaml`)
remain separate and are created on demand by Snakemake when run with
`--use-conda` — the base env only needs to be able to invoke `snakemake`
itself. Channel list (`conda-forge`, `nodefaults`) matches the convention
already used by the per-rule env files.

`snakemake-minimal` was chosen over `snakemake` to avoid pulling in the full
package's optional reporting/plugin dependencies, keeping the base env as
small as possible.

### Notes / caveats for future edits

- This file is a spec, not the materialized environment — the existing
  `workflow/envs/LLMmind_project` prefix was not regenerated from it in this
  session. To (re)build the env from the spec:
  `conda env create -f workflow/envs/LLMmind_project_environment.yaml -p workflow/envs/LLMmind_project`.
- If the base environment ever needs additional tooling (e.g. for
  `--use-conda` environment creation backends, linting, etc.), add it here
  rather than to a per-rule env file.

### Files touched

- `workflow/envs/LLMmind_project_environment.yaml` (new)

---

## Mark degenerate (zero-spread) boxplots; remove per-run diagnostic logging

Kind: `new_feature`, `removal`

### Summary

Investigated a report of boxplots in `plot_concept_alignment_enrichment.py`
and `plot_spearman_alignment.py` output appearing to be "missing" for some
models. Root cause: `matplotlib`'s `ax.boxplot()` renders a box whose
quartiles collapse onto each other (`Q1 == Q3`, or the median coinciding with
`Q1` or `Q3`) as a flat, sub-pixel line — visually indistinguishable from no
data at all — rather than raising a warning. This happens legitimately
whenever the underlying per-concept scores are coarsely discretized (small
`number_of_neighbours` relative to the population) and/or the concept count
is small (e.g. the `narratives`/`nature_stories` datasets), causing quartiles
to coincide exactly. Confirmed via a live reproduction against real pipeline
output (`results/alignment_scores/dataset-caption_scene_model-*_brain_cosine-
alignment_score_50NN.parquet`): models with `Q1 == Q3 == 0` in the
diagnostics rendered no box at all, while models with only `median == Q1`
still rendered a visible (but asymmetric) box.

This is a plotting/legibility fix, not a statistics fix — no alignment
scores, p-values, or other computed values change.

### Changes

#### `workflow/libraries/visualisation_utils.py`

- Added `mark_degenerate_boxplot_statistics(ax, boxplot_values, marker="D", color="red", markersize=5, zorder=4)`.
  For each label's value array, computes `Q1`/`median`/`Q3` and, if any pair
  is equal (`np.isclose`), draws a red diamond at `(position, median)` on top
  of the boxplot (`zorder=4`, above the box at `zorder=3` and the scatter at
  `zorder=1`). Adds a single `"Degenerate box (zero-width quartile range)"`
  legend entry (only once, regardless of how many boxes are degenerate).
- Removed `log_boxplot_summary_statistics(labels, boxplot_values)` (added in
  the `2026-09-21-boxplot-stats-and-signature-formatting` changelog entry).
  It printed `n`/`unique`/`min`/`Q1`/`median`/`Q3`/`max`/`IQR` per label to
  stdout on every plotting run; this was diagnostic instrumentation used to
  investigate the issue above and is no longer needed now that degenerate
  boxes are self-documenting in the plot itself. The relevant per-model
  statistics that explained the different box shapes will be described in
  the manuscript instead of logged at runtime.

#### `workflow/visualisation/scripts/plot_concept_alignment_enrichment.py`
#### `workflow/visualisation/scripts/plot_spearman_alignment.py`

- Removed the `log_boxplot_summary_statistics(labels, boxplot_values)` call
  and its now-unused import.
- Added `mark_degenerate_boxplot_statistics(ax, boxplot_values)` immediately
  after each script's `ax.boxplot(...)` call, before `ax.legend()`.

### Verification

- Reproduced the degenerate-box rendering behavior directly against
  `matplotlib` with synthetic arrays (empty, all-NaN, all-identical,
  single-value) to confirm the exact failure mode before writing the fix.
- Ran both `plot_concept_alignment_enrichment.py` and
  `plot_spearman_alignment.py` end-to-end against real pipeline output
  (`dataset=caption_scene`, `similarity=cosine`, `neighbours=50`, and
  `dataset=narratives`, `similarity=cosine` respectively) in a scratch
  output directory. Confirmed: models with fully collapsed quartiles now
  show only the red diamond (previously nothing); models with a
  partially-visible box show both the box and the diamond; the
  `narratives` Spearman plot (continuous, non-discretized data, no
  collapsed quartiles) renders unchanged with no diamonds, confirming no
  false positives.

### Files touched

- `workflow/libraries/visualisation_utils.py`
- `workflow/visualisation/scripts/plot_concept_alignment_enrichment.py`
- `workflow/visualisation/scripts/plot_spearman_alignment.py`

---

## Unify empirical-p-value RNG and formula between llm-llm and llm-mind

Kind: `bugfix`

### Summary

Comparing the `llm-llm` and `llm-mind` empirical-p-value code paths surfaced
two implementation inconsistencies (no statistical bug in either path's
results, but divergent code for equivalent operations):

1. The positive-empirical-p-value correction `(k + 1)/(n + 1)` was already
   centralized in `libraries/compute_statistics.py` as
   `empirical_upper_tail_p_value()` and used by both concept-level scripts,
   but `aggregate_all_p_value_outputs.py`'s model-level p-value function
   reimplemented the same formula inline.
2. `llm-llm`'s permutation loop
   (`compute_llm_llm_empirical_p_value.py`) advanced one
   `np.random.default_rng(random_seed)` sequentially across all
   `number_of_relabellings` draws, while `llm-mind`'s relabelling loop
   (`relabel_llm_similarity_and_compute_relabelled_llm_alignment_score.py`)
   constructed a fresh `np.random.default_rng(random_seed + shuffle_i)` for
   every shuffle. Both are valid ways to produce independent permutations,
   but the two pipelines drew their null permutations differently for no
   documented reason.

Per explicit instruction, this change does **not** add concept-level
empirical or hypergeometric p-values to the `llm-llm` path — it remains a
model-pair-level-only test by design; only the two inconsistencies above
were addressed.

### Changes

#### `workflow/libraries/compute_statistics.py`

- Added `create_relabelling_rng(random_seed, shuffle_index)` →
  `np.random.default_rng(random_seed + shuffle_index)`. A fresh,
  independently-seeded generator per shuffle, so relabellings can be
  produced in any order (or in parallel) and still reproduce the same
  sequence for a given `random_seed`.

#### `workflow/llm_llm_alignment/scripts/compute_llm_llm_empirical_p_value.py`

- `compute_empirical_p_value()` now calls `create_relabelling_rng(random_seed, shuffle_i)`
  inside the loop instead of advancing one `default_rng(random_seed)` across
  all iterations.
- **Behavioral change**: this alters the exact sequence of permutations
  drawn (not just a refactor) — see Compatibility note below.

#### `workflow/llm_mind_alignment/scripts/relabel_llm_similarity_and_compute_relabelled_llm_alignment_score.py`

- `compute_relabelled_alignment_scores()` now calls
  `create_relabelling_rng(random_seed, shuffle_i)` instead of inlining
  `np.random.default_rng(random_seed + shuffle_i)`. Identical arithmetic,
  same seed schedule — no behavioral change, pure extraction to the shared
  helper.

#### `workflow/llm_mind_alignment/scripts/aggregate_all_p_value_outputs.py`

- `compute_model_level_empirical_p_value()` now calls
  `empirical_upper_tail_p_value(number_at_least_as_large=..., number_of_relabellings=...)`
  instead of reimplementing `(k + 1)/(n + 1)` inline. No behavioral change —
  identical arithmetic.

### Compatibility note

`llm-llm`'s empirical p-values will now be computed from a different
(though equally valid) sequence of random permutations than before. Any
existing `results/alignment_scores/dataset-*_model-*_model-*_empirical_*
-alignment_score_*NN.p_value.tsv` files were generated under the old
sequential-RNG scheme and should be regenerated (`snakemake --use-conda
--cores <N> --forcerun compute_llm_llm_empirical_p_value` or by deleting the
affected outputs) to be consistent with this change. `llm-mind`'s
concept-level and model-level outputs are numerically unaffected and do not
need regenerating.

### Verification

- Confirmed `create_relabelling_rng(seed, i)` is deterministic
  (`.permutation(...)` on two separately-constructed instances with the
  same arguments returns identical output).
- Ran `compute_llm_llm_empirical_p_value.py` end-to-end against real data
  (`dataset=caption_scene`, `model_1=dinov2_g`, `model_2=clip_h`,
  `similarity=pearson`, `5NN`, `8920` shared concepts, `20` relabellings)
  after the change; exited `0` and produced a well-formed result row.
- Imported all three modified modules under `PYTHONPATH=workflow` to
  confirm no syntax/import errors.

### Files touched

- `workflow/libraries/compute_statistics.py`
- `workflow/llm_llm_alignment/scripts/compute_llm_llm_empirical_p_value.py`
- `workflow/llm_mind_alignment/scripts/relabel_llm_similarity_and_compute_relabelled_llm_alignment_score.py`
- `workflow/llm_mind_alignment/scripts/aggregate_all_p_value_outputs.py`

---

## Document required input data and per-module breakdown in README

Kind: `documentation`

### Summary

`README.md` previously described the repository layout only at the
one-line-per-directory level (see `2026-09-21_new_feature_bugfix_refactor_removal_documentation.md`) and
said nothing about which raw files must exist under `resources/datasets/`
before a first run, nor how they get there. Added two new sections —
`## Subprojects` and `## Input data` — with content verified against the
current on-disk state rather than inferred from code alone.

### Source material / verification method

- **Required raw file paths**: verified directly against the populated
  `resources/datasets/{caption_scene_dataset,narratives_dataset,
  nature_stories_dataset,nsd_data_dataset}/` trees (`find`/`ls` for exact
  filename patterns and counts — e.g. 1600 BOLD runs + 1600 matching CSD
  event tables for `caption_scene_dataset`, 811 `afni-smooth` BOLD files for
  `narratives_dataset`, S01–S11 `_BOLD.hdf`/`_mappers.hdf` pairs for
  `nature_stories_dataset`, per-subject `design_session*_run*.tsv` /
  `timeseries_session*_run*.nii.gz` counts for `nsd_data_dataset` subj01–08).
- **NSD functional→MNI mapping requirement**: traced instead of assumed.
  `workflow/dataset_processing/nsd_data_dataset/scripts/assemble_nsd_bold.py`
  calls `nsdcode.nsd_mapdata.NSDmapdata(dataset_dir)`. Read the installed
  package source under
  `.snakemake/conda/b8a4553242f8148bf6c43764ef8548a2_/lib/python3.14/
  site-packages/nsdcode/` (`nsd_datalocation.py` + `nsd_mapdata.py`) to
  confirm it resolves to exactly `<dataset_dir>/nsddata/ppdata/subjXX/
  transforms/`, which matches what's present on disk (86 files/subject).
- **Directory-linking mechanism**: read the sibling `public_datasets/`
  project's `workflow/Snakefile` (a separate Snakemake pipeline, not part of
  this repo) — its `rule all` targets write to
  `results_molilab_cold_back/<dataset>/.*_complete` markers, where
  `results_molilab_cold_back` is a symlink to
  `/mnt/molilab_cold_bak/LLMmind/downloaded_datasets`. Confirmed via `ls -la`
  that `resources/datasets/<dataset>` in *this* repo are themselves symlinks
  into `public_datasets/results_molilab_cold_back/<dataset>` (with an extra
  `/dataset` path segment for `narratives_dataset`, since `public_datasets`
  also keeps a `cloned_dataset/` datalad working copy alongside the fetched
  files). No rule in either repo creates these symlinks automatically — they
  were made by hand in the current checkout.

### Changes

#### `README.md`

- New `## Subprojects` section, inserted after `## Repository layout`: one
  subsection per `workflow/*` module (`dataset_processing/<dataset>/`,
  `isc_nearest_neighbours/`, `llm_nearest_neighbours/`,
  `llm_mind_alignment/`, `llm_llm_alignment/`, `spearman_alignment/`,
  `visualisation/`, `libraries/`), each describing its role and mapping back
  to the numbered pipeline overview at the top of the file. Rule names were
  cross-checked against each module's `Snakefile` (`grep -n "^rule "`) to
  keep the descriptions accurate.
- New `## Input data` section, inserted after `## Datasets` and before
  `## Models`:
  - Per-dataset lists of the exact raw file paths/glob patterns required
    under `resources/datasets/<dataset>/` (see verification method above).
  - Explicit callout that `resources/models/` and `resources/atlases/` do
    *not* need to be populated manually (`download_pretrained_llm` rule and
    `nilearn.datasets.fetch_atlas_schaefer_2018` respectively handle those on
    demand), and that `resources/` internal generated files (`.stimuli_ready`,
    `excluded_stimuli.txt`, renamed transcripts, etc.) must not be supplied
    by hand.
  - New `### Organising the input data on disk` subsection documenting the
    expected `resources/datasets/<dataset>/` layout and, specific to this
    lab's setup, the `ln -s` commands needed to link `public_datasets/`
    output into place (since that pipeline's outputs land in a different
    physical location and are not wired up automatically).

### Notes / caveats for future edits

- The `ln -s` commands in the README hard-code the assumption that
  `public_datasets/` is checked out as a sibling of this repository — true
  in the current environment (`/home/molinerislab/LLMmind/{public_datasets,
  LLMmind_project}`) but not guaranteed elsewhere; the README already flags
  this as an assumption to adjust.
- If `public_datasets/workflow/Snakefile` changes its output paths (e.g.
  the `results_molilab_cold_back` root or the `narratives_dataset/dataset`
  subdirectory), the symlink commands and the "Organising the input data on
  disk" prose in `README.md` will need updating to match — nothing enforces
  this link automatically.
- The exact required-file lists are a manual transcription of what was
  observed on disk; if a dataset module's manifest logic changes to expect
  additional/renamed raw files (e.g. a new exclusion input), update both the
  `## Input data` section here and, if relevant, the corresponding
  `dataset_processing/<dataset>/Snakefile`.

### Files touched

- `README.md` (modified — two new sections added, no existing content
  removed or reordered)

---

## NSD: drop dataset-specific repetition constraint, compute ISC from all available observations

Kind: `new_feature`

### Summary

The NSD dataset-processing pipeline previously imposed an NSD-specific
inclusion rule that does not exist for any other dataset in the project: a
stimulus was retained only if **every** subject had seen it at least
`min_repetitions_per_subject` (3) times, and only the first
`repetitions_to_use` (3) repetitions per subject were used, concatenated
into one continuous BOLD time series per (subject, stimulus). This reduced
the ~1,000 images nominally shared across all 8 NSD subjects down to 515
retained stimuli, and the concatenation treated temporally distinct
presentations of the same image as if they were one continuous scan.

This change removes that constraint and brings NSD in line with the
`caption_scene` dataset's existing principle: a stimulus is usable whenever
there are at least two independent fMRI observations to compute ISC from
(`caption_scene_parcel_paths()` in
`workflow/dataset_processing/caption_scene_dataset/Snakefile` enforces
exactly this — `len(parcel_paths) < 2` is the only exclusion criterion).
For NSD, each presentation (occurrence) of an image, by any subject, is now
treated as one independent fMRI observation. A stimulus is excluded only
when it has fewer than two such observations in total, regardless of how
those observations are distributed across subjects.

### Changes

#### `config/config.yaml`

- Removed `nsd_data.min_repetitions_per_subject` and
  `nsd_data.repetitions_to_use`. No replacement config key was added — the
  only remaining constraint (≥2 observations) is not a tunable parameter,
  it is the mathematical minimum for computing a leave-one-out correlation.

#### `workflow/dataset_processing/nsd_data_dataset/scripts/make_nsd_manifest.py`

- Removed the `--min_repetitions_per_subject` / `--repetitions_to_use` CLI
  arguments and their validation.
- Replaced the per-subject eligibility intersection
  (`eligible_stimuli_per_subject` / `set.intersection(*...)`, which required
  *every* subject to individually clear the repetition floor) with a single
  pooled `observation_counts_by_stimulus` count summed across all subjects.
  A stimulus is retained iff `observation_counts_by_stimulus[id] >= 2`; this
  mirrors `make_caption_scene_manifest.py`'s
  `stimulus_counts = out.groupby("stimulus_id").size(); valid_stimuli =
  stimulus_counts[stimulus_counts >= 2].index` pattern exactly.
  Stimuli that fail this (i.e. exactly 0 or 1 observation across all
  subjects) are collected into `excluded_nsd_image_identifiers` and reported
  via `warnings.warn`, matching Caption Scene's `singleton_stimuli` warning.
- `--output_excluded_stimuli` now actually gets populated
  (`write_lines(...)`, a helper copied from Caption Scene's
  `make_caption_scene_manifest.py`) instead of always being written as an
  empty file.
- Manifest construction no longer slices `[:repetitions_to_use]` or asserts
  an exact repetition count per subject. For each retained stimulus, **all**
  of a subject's occurrences are used (a subject may contribute 0, 1, 2, or
  more), each assigned a sequential `repetition` number local to that
  subject/stimulus pair, and each written to its own `output_bold` path
  (`sub-{ss}_task-{stim}_rep-{NN}_bold.nii.gz`) instead of one shared path
  per (subject, stimulus) covering the concatenated repetitions.
- `stimulus_manifest` columns `repetitions_per_subject` and
  `volumes_per_subject_stimulus` (both assumed a fixed, uniform repetition
  count) were replaced with `n_observations` (total pooled observations for
  that stimulus) and `n_subjects_represented` (how many of the subjects
  contributed at least one observation) — both now genuinely variable
  per stimulus.
- `manifest_metadata.json` no longer contains
  `min_repetitions_per_subject` / `repetitions_to_use`; added
  `n_excluded_stimuli`.

#### `workflow/dataset_processing/nsd_data_dataset/scripts/assemble_nsd_bold.py`

- **Behavioral change, not a refactor.** Previously grouped occurrences by
  `(subject, stimulus_id)`, asserted a single shared `output_bold` and a
  contiguous `1..N` repetition sequence, cropped each repetition, then
  `np.concatenate(cropped_bold_arrays, axis=3)`'d them into one array before
  a single `NSDmapdata.fit()` call per (subject, stimulus) mapped the
  concatenated array to MNI space.
- Now groups occurrences by `(subject, source_bold)` purely to avoid
  reloading the same run file from disk repeatedly. Each occurrence is
  cropped and passed through its own `NSDmapdata.fit()` call independently,
  writing directly to that occurrence's own `output_bold` path. There is no
  concatenation and no cross-occurrence array; the `reference_bold_image`
  geometry-consistency check across repetitions was removed because there
  is no longer a group of repetitions to check consistency across — each
  occurrence stands on its own.
- Cost implication: this increases the number of `NSDmapdata.fit()` calls
  (previously one per (subject, stimulus) covering all its repetitions in
  one call; now one per occurrence). This is the direct, expected cost of
  no longer requiring/relying on a fixed repetition count to produce
  equal-length concatenated series.

#### `workflow/dataset_processing/nsd_data_dataset/Snakefile`

- `nsd_parcel_time_series_output(subject, stimulus_identifier)` →
  `nsd_parcel_time_series_output(subject, stimulus_identifier, repetition)`;
  output path now includes `rep-{NN}` so multiple observations from the
  same subject no longer collide on one file.
- `write_nsd_parcel_manifest()`: the uniqueness invariant it enforces moved
  from "at most one `output_bold` per `(subject, stimulus_id)`" (true under
  the old concatenate-then-map design) to "at most one `output_bold` per
  `(subject, stimulus_id, repetition)`" (true under the new
  one-file-per-occurrence design). Added `repetition` as a required/emitted
  column throughout.
- `write_nsd_isc_manifest()`: added `repetition` as an emitted column
  (informational; not required for the ISC computation itself) and sorts by
  `(subject, repetition)` instead of `subject` alone.
- `make_nsd_manifest` rule: dropped the `min_repetitions_per_subject` /
  `repetitions_to_use` params and the corresponding `--min_repetitions_per_subject`
  / `--repetitions_to_use` shell arguments.

#### `workflow/dataset_processing/nsd_data_dataset/scripts/compute_nsd_isc.py`

- Removed the `stimulus_manifest["subject"].duplicated().any()` guard that
  rejected an ISC manifest containing more than one row for the same
  subject under a given stimulus. Under the new occurrence-level model this
  is expected and correct: a subject who saw a stimulus 3 times now
  contributes 3 independent rows/observations, exactly as `compute_caption_scene_isc.py`
  never restricted itself to one observation per subject either.
- `len(parcel_time_series_files) < 2` (unchanged) is now the *only*
  exclusion check at this stage — the same role it plays in
  `compute_caption_scene_isc.py`'s `compute_isc()`. It remains as a
  belt-and-suspenders check; the primary filter happens earlier in
  `make_nsd_manifest.py`.
- Log message wording changed from "N subjects" to "N observations" to
  reflect that the leave-one-out axis is now observations, not subjects.

#### `workflow/dataset_processing/nsd_data_dataset/scripts/extract_nsd_parcels.py`

- No changes. It is already generic over whatever rows
  `write_nsd_parcel_manifest()` hands it (`bold_file` → `parcel_time_series`);
  the extra `repetition` column is simply ignored.

### Compatibility note

This changes both the *set* of retained NSD stimuli (more stimuli retained
— every stimulus with ≥2 total observations, rather than only ~515
stimuli meeting the old all-subjects-≥3-reps rule) and how each stimulus's
brain representation is derived (leave-one-out ISC over all raw
observations, rather than over one subject-level series built by
concatenating exactly 3 repetitions). `results/mind/nsd_data/` (occurrence
manifest, stimulus manifest, parcel time series, `single_stimulus_bold_mni/`,
ISC outputs) and `resources/datasets/nsd_data_dataset/excluded_stimuli.txt`
/ `.stimuli_ready` should all be regenerated from scratch — there is no
compatible partial-regeneration path given both the file-naming scheme
(`rep-{NN}` suffix) and the stimulus set changed.

Downstream consumers (`isc_nearest_neighbours`, `llm_mind_alignment`, etc.)
are unaffected at the interface level: they only depend on one
`task-{stimulus_id}_isc_mean.{npy,nii.gz}` file per retained stimulus and
one exported image per stimulus, both of which are still produced with the
same naming scheme.

### Verification

- `ast.parse()` on all four modified Python scripts — no syntax errors.
- `python3 -c "import yaml; yaml.safe_load(...)"` on `config/config.yaml` —
  parses cleanly after removing the two keys.
- Parsed the Snakefile's Python preamble (helper functions, before the
  first `rule`) with `ast.parse()` — no syntax errors. (The `rule` blocks
  themselves are Snakemake DSL, not plain Python, and were reviewed by
  inspection instead.)
- `grep -rn` across `*.py`, `*.yaml`, `Snakefile`, `*.md` for
  `min_repetitions_per_subject`, `repetitions_to_use`,
  `repetitions_per_subject`, `volumes_per_subject_stimulus` — no remaining
  references anywhere in the repo.
- Confirmed no code outside `dataset_processing/nsd_data_dataset/` reaches
  into NSD-specific manifest fields (`workflow/Snakefile` only does
  `include: "dataset_processing/nsd_data_dataset/Snakefile"`; the
  nearest-neighbour/alignment workflows were grepped for `nsd` and found to
  contain no dataset-specific branching).
- **Not run**: the pipeline was not executed end-to-end against real NSD
  data (requires the downloaded NSD dataset and is computationally
  expensive — one `NSDmapdata.fit()` call per occurrence). This should be
  smoke-tested against real data before relying on the outputs.

### Files touched

- `config/config.yaml`
- `workflow/dataset_processing/nsd_data_dataset/Snakefile`
- `workflow/dataset_processing/nsd_data_dataset/scripts/make_nsd_manifest.py`
- `workflow/dataset_processing/nsd_data_dataset/scripts/assemble_nsd_bold.py`
- `workflow/dataset_processing/nsd_data_dataset/scripts/compute_nsd_isc.py`
