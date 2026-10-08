# 2026-10-08 — changes for users

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../../AI_USAGE.md).*

Changes made on this day, in order:

- The ISC reliability table is no longer produced (removal, refactor, documentation)
- Broken embedding vectors now stop the pipeline (bugfix)
- Internal clean-up of the alignment-score scripts (refactor)
- Fewer hidden default values in the scripts (refactor)
- Mistakes in the config are reported at startup (new_feature, documentation)
- Unused code removed (removal)
- Correction about when editing a script rebuilds results (documentation)
- More analysis settings in the config file (refactor, documentation)
- Manifests are rebuilt when the settings they depend on change (bugfix, documentation)
- New neighbourhood sizes for Caption Scene and NSD: 5, 25 and 125 (new_feature, removal, documentation)

The first seven changes alter no result and need no recomputation. The last three were made later the same morning: they make the next run recompute everything (about 31 hours on node5).

---

## 09:43 — The ISC reliability table is no longer produced

Kind: removal, refactor, documentation

The pipeline no longer measures the split-half reliability of the brain (ISC) representations, so
`results/mind/all_isc_reliability.tsv` and the per-dataset `isc_reliability.tsv` files are no
longer made. The NSD and Caption Scene results are no longer labelled "exploratory". The old
files are still on disk and can be deleted by hand, together with
`results/mind/caption_scene/manifests/isc_manifest.tsv`. The earlier measurements are kept for
the record at the end of [`fmri_preprocessing.md`](../../reference/fmri_preprocessing.md).

---

## 09:43 — Broken embedding vectors now stop the pipeline

Kind: bugfix

If a model or brain vector contains a missing or infinite value, or is constant (for example all
zeros), the nearest-neighbour step now stops with an error naming the rows. Before, such a vector
would have silently produced meaningless neighbours. The current files have no such vectors.

---

## 09:43 — Internal clean-up of the alignment-score scripts

Kind: refactor

The scripts that compare model-brain and model-model neighbours now work identically. The only
visible difference: a model-brain comparison with no concept in common now stops with an error
instead of writing an empty file.

---

## 09:43 — Fewer hidden default values in the scripts

Kind: refactor

The random seed and the NSD interpolation are now taken only from `config/config.yaml`; the
scripts no longer have their own fallback values that could differ from it. The config comment of
`max_chunk_length` now explains why it is set to 2048.

---

## 09:43 — Mistakes in the config are reported at startup

Kind: new_feature, documentation

A wrong value in `config/config.yaml` (an unknown model modality, quantization or similarity type,
a model name without a size, a minimum number of subjects outside 2–8, or a number of neighbours
that is not a positive whole number) now stops the pipeline immediately with a message naming the
setting, instead of failing hours later or being silently ignored.

---

## 09:43 — Unused code removed

Kind: removal

Three similarity functions that nothing used were deleted. Nothing changes for users.

---

## 09:43 — When editing a script rebuilds results

Kind: documentation

[`running_and_troubleshooting.md`](../../guides/running_and_troubleshooting.md) said that editing
only comments never rebuilds results. That is true for code inside the Snakefiles, but not for the
scripts the pipeline tracks (for example the NSD and Caption Scene manifest scripts): any edit to
them, even a comment, rebuilds that dataset and everything after it.

---

## 09:54 — More analysis settings in the config file

Kind: refactor, documentation

Four settings that were fixed inside the scripts are now in `config/config.yaml`, with the same
values as before: `chunk_overlap` (tokens shared by consecutive chunks of a long text, 256),
`pooling` (how a model's outputs become one vector: `avg` for language models, `cls` for vision
models), and, for Caption Scene, `inside_threshold` (0.999) and `spline_order` (3). The results
do not change, but the next run recomputes every embedding and everything after it.

---

## 09:54 — Manifests are rebuilt when the settings they depend on change

Kind: bugfix, documentation

The lists of brain scans used by Narratives, Nature Stories and NSD are now rebuilt automatically
when a setting or file they depend on changes (for example `minimum_subjects_per_stimulus` or the
Narratives exclusion list). Before, they could silently stay out of date, and you had to force
them by hand. The first run after this change rebuilds them all.

---

## 09:54 — New neighbourhood sizes for Caption Scene and NSD: 5, 25 and 125

Kind: new_feature, removal, documentation

Caption Scene and NSD are now analysed with 5, 25 and 125 nearest neighbours instead of 5, 25, 50
and 100. All result files and plots for 50 and 100 neighbours were deleted. The combined summary
tables still contain the 50 and 100 rows until the next run rebuilds them with the 125 rows. A
full run now takes about 31 hours instead of 32
([`clean_run_duration.md`](../../reference/clean_run_duration.md)).
