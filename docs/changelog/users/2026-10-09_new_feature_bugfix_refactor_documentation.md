# 2026-10-09 — changes for users

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../../AI_USAGE.md).*

Changes made on this day, in order:

- Jobs no longer get stuck after finishing their work (bugfix, documentation)
- Where the Nature Stories transcripts come from is now documented (documentation)
- Narratives brain regions now drawn on the right brain template (bugfix, documentation)
- New plots comparing cosine, Pearson and Spearman similarity (new_feature, refactor, documentation)

---

## 09:40 — Jobs no longer get stuck after finishing their work

Kind: bugfix, documentation

In every long run, a few jobs wrote their results and then never ended. Each one blocked one of the
run's CPU slots until someone killed it, and enough of them could stop the run completely. The
cause was found: the way the scripts read `.parquet` files could freeze the program as it was
shutting down. All scripts now read these files in a way that cannot freeze.

Nothing changes in the results, and nothing has to be recomputed because of this fix. If a job
still hangs, the troubleshooting section of the
[guide](../../guides/running_and_troubleshooting.md#6-troubleshooting) explains how to end it
without losing its output.

---

## 11:35 — Where the Nature Stories transcripts come from is now documented

Kind: documentation

The word transcripts of the Nature Stories come from a different public dataset than the brain
recordings. A new page, [`nature_stories_stimuli.md`](../../reference/nature_stories_stimuli.md),
explains where each comes from and shows that both describe the same 11 stories with the same
lengths. The only mismatch is the audio file of the story "life" in the brain-data download, which
is about 71 seconds too short; the pipeline does not use the audio, so the results are not
affected.

---

## 15:14 — Narratives brain regions now drawn on the right brain template

Kind: bugfix, documentation

The Narratives brain data and the map of 200 brain regions used to average them were on two
slightly different standard brain templates, so the region borders were off by a few millimetres.
Narratives now uses the same region map published for its own template; it is downloaded
automatically into `resources/atlases/` the first time. The other datasets are unchanged.

The region numbers stay the same, so results stay comparable across datasets. The Narratives
results are **not** updated automatically. To recompute them, run the pipeline with
`--forcerun extract_narratives_parcels`; this redoes every Narratives result, from the brain region
time series to the plots and summary tables.

---

## 15:14 — New plots comparing cosine, Pearson and Spearman similarity

Kind: new_feature, refactor, documentation

A new folder, `results/pictures/similarity_comparison_lineplots/`, shows the three similarity
measures together, one colour per measure, so you no longer need to flip between three images:

- `dataset-<dataset>-brain_model_alignment_<k>NN.png`: mean alignment score;
- `dataset-<dataset>-brain_model_alignment_enrichment_<k>NN.png`: alignment enrichment;
- `dataset-<dataset>-brain_model_spearman_alignment.png`: Spearman alignment.

These plots have no significance asterisks (look at the per-measure plots for those), and their
y-axis is fitted to their own data. The existing plots look exactly as before. They are built by
a normal run; `docs/reference/statistics.md` (section 7) explains what they show.

