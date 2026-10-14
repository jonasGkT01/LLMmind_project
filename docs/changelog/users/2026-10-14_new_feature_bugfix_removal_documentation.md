# 2026-10-14 — changes for users

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../../AI_USAGE.md).*

Changes made on this day, in order:

- The AI usage page lists only files of this project (documentation)
- Old files removed from the results (documentation)
- Results for a language and a visual brain region (new_feature, documentation)
- Summary tables now in their own folder (new_feature, documentation)
- Two unused files removed (removal, documentation)
- Readable scale on enrichment plots with a narrow range (bugfix, documentation)

---

## 12:13 — The AI usage page lists only files of this project

Kind: documentation

`docs/AI_USAGE.md` no longer lists the developer's TODO and SUGGESTIONS lists, which are kept
outside this project. Nothing in the pipeline or its results changed.

---

## 15:15 — Old files removed from the results

Kind: documentation

Files left in `results/` and `.snakemake/` by older versions of the pipeline were deleted: NSD
parcel files with an old name, the ISC reliability tables, the Narratives length-check files and
old Snakemake bookkeeping records. None of them is used any more, and no result has to be
rebuilt. The list of such leftover files, for other copies of the project, is in the guide
`docs/guides/running_and_troubleshooting.md`, under "Leftover outputs from older versions".

---

## 15:35 — Results for a language and a visual brain region

Kind: new_feature, documentation

So far every model was compared with the brain response of the whole cortex. Now each model is
also compared with the part of the cortex that matches its modality:

- **language models** with a language region of 17 parcels (the language and auditory networks
  of the Kong 2022 atlas), on Narratives, Nature Stories and Caption Scene;
- **vision models** with the visual network (29 parcels), on NSD and Caption Scene.

The region results sit next to the whole-cortex ones, with `_language` or `_vision` added to the
name: for example `results/alignment_scores_language/`,
`results/all_model_brain_alignment_scores_vision.tsv` and
`results/pictures/alignment_lineplots_language/`. The file names inside are the same as for the
whole cortex. The heatmaps exist for the whole cortex only. The whole-cortex results do not
change and are not recomputed.

The next run of the pipeline computes the region results (about as many brain-model jobs as the
whole cortex has, CPU only). Which parcels are used and how the region data are taken from the
whole-cortex data is described in [`brain_regions.md`](../../reference/brain_regions.md).

---

## 17:45 — Summary tables now in their own folder

Kind: new_feature, documentation

The summary tables (`all_model_brain_alignment_scores*.tsv`, `all_model_model_alignment_scores.tsv`
and `all_spearman_alignment_scores*.tsv`, including the `_language` and `_vision` versions) are now
in `results/tsv_summaries/` instead of directly in `results/`. The existing tables were moved
there unchanged. On the next run, the plots that read these tables are redrawn once; their content
does not change.

---

## 18:20 — Two unused files removed

Kind: removal, documentation

- The helper `workflow/libraries/estimate_batch_size.py`, meant to suggest batch sizes for the
  embedding step, was never used and has been deleted.
- The Nature Stories preprocessing no longer writes
  `results/mind/nature_stories/qc/valid_voxel_counts.tsv` (number of valid voxels per subject);
  nothing used it. The same table is still printed while the step runs. The existing file was
  deleted; other copies of the project can delete it too.

Nothing has to be rerun and no result changes.

---

## 18:50 — Readable scale on enrichment plots with a narrow range

Kind: bugfix, documentation

Some enrichment plots, mainly the similarity-comparison line plots
(`results/pictures/similarity_comparison_lineplots*/...alignment_enrichment_*NN.png`), showed
only the value 1 on the y-axis, so the size of the differences could not be read. When the y-range
is narrow, the axis now shows several evenly spaced values (for example 0.97, 0.98, …, 1.05), each
with its horizontal gridline. Plots that start at 0 look as before. No result changes. Existing
plots are not redrawn automatically: add
`--forcerun plot_similarity_comparison_enrichment_lineplot` to the next Snakemake command.
