# 2026-10-02 — changes for users

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../../AI_USAGE.md).*

Changes made on this day, in order:

- Alignment-score files: rows in a fixed order, one unused column removed (refactor, removal)
- Clearer null display in the plots, consistent significance stars, statistics page (refactor)
- Unused code removed (removal)
- Shuffled (null) scores drawn from one random sequence (refactor)
- Code reformatted to one consistent style (refactor)
- Caption Scene now aligned to MNI; repeated presentations averaged in the ISC (new_feature, bugfix)
- Narratives: participants who heard a story twice now count once (new_feature)
- New table: how reliable the brain representations are (new_feature, bugfix)
- Narratives: excluded stories listed once, by reason (refactor)

---

## 08:27 — Alignment-score files: rows in a fixed order, one unused column removed

Kind: `refactor`, `removal`

The per-model alignment-score files (`results/alignment_scores/…NN.parquet`) now list their
concepts in alphabetical order. Before, the order changed randomly on every run. The scores
themselves are unchanged. Two runs now give exactly the same file, so old and new results can be
compared directly, and the files are easier to read when you open them with `parquet2tsv.sh`.

The `alignment_score_percentage` column (the alignment score times 100) is no longer written,
because nothing used it. Use `alignment_score` instead.

Nothing reruns because of this change. Existing files keep their old row order and column until
they are regenerated.

### Context

- Request: Written for TODO entries S38 (approved by the developer on 2026-10-02) and S29 item 2 (approved on 2026-09-30), implemented together at the developer's request.
- Files changed: `workflow/libraries/compute_alignment.py`.

---

## 09:27 — Clearer null display in the plots, consistent significance stars, statistics page

Kind: `refactor`

**What changes in the figures** (after you redraw them):

- **Model-level enrichment plot and model-level Spearman plot:** the points no longer carry error
  bars. Instead, each model gets a grey interval on the dashed reference line (enrichment = 1, or
  ρ = 0), labelled "Null ± 1 SD". It shows how much that model's score varies by chance. A point
  far above its grey interval is well above chance; the asterisks still say whether it is
  significant.
- **Heatmaps:** the diagonal (a model, or the brain, with itself) is now blank instead of 1.0,
  since it is not a computed score. The white margins around the heatmaps are trimmed.
- **p-value heatmap:** the stars of the brain row and column now match the stars of the
  brain-model line plots exactly. The model-model cells are corrected among themselves. Before,
  both groups were corrected together, so a brain-model cell could get more stars in the heatmap
  than in the line plots.

**New documentation:** `docs/reference/statistics.md` explains how the alignment
scores, the shuffled (null) scores, the p-values, the enrichment and the multiple-testing
correction are computed, and what every point, bar and grey interval in the figures means. It is
meant as the source for the methods section. It also says clearly that the averaged per-concept
p-values in the summary tables are descriptions, not tests.

**Nothing else changes:** no result file, table or number changes, and nothing reruns by itself.
To redraw all figures, run the "redraw every plot" command in the README's "Running the pipeline"
section; it now includes the two heatmap rules.

Behind the scenes, the code that reads result filenames and the plotting code were merged into
shared functions, so future changes to file names or figure style are made in one place.

### Context

- Request: Written for TODO entries S2, S3, S4, S13, S15, S16 and S20 (approved by the developer on 2026-09-30), implemented after the developer asked to do the TODO tasks that need no rerun.
- Files changed: see the developer changelog entry of the same name.

---

## 09:31 — Unused code removed

Kind: `removal`

Two pieces of code that nothing used were deleted: a function that computed a mean alignment
score in a way the pipeline no longer uses, and an extra value kept by the enrichment
calculation but never shown. Nothing changes when you run the pipeline: no result, table or
figure changes, and nothing reruns.

### Context

- Request: Written after the developer approved removing the two unused leftovers found during the S2/S3 refactor.
- Files changed: `workflow/libraries/compute_alignment.py`, `workflow/libraries/compute_alignment_enrichment.py`.

---

## 09:50 — Shuffled (null) scores drawn from one random sequence

Kind: `refactor`

The significance tests compare each alignment score with scores computed after randomly
shuffling the concept labels 10,000 times. These shuffles are now all drawn from one random
sequence, started from `random_seed` in `config/config.yaml`, exactly as the Spearman test already
did. As a result, all tests of a dataset use the same shuffles, and a replication with a
different seed gives genuinely different shuffles.

**What changes:** after the full recomputation, the alignment p-values and enrichment values
differ slightly from the previous run, as expected for a new set of random shuffles. The Spearman
results stay the same. The methods should say that all tests share one random sequence (see
`docs/reference/statistics.md`, section 2).

### Context

- Request: Written for TODO entry S17 (approved by the developer on 2026-09-30), implemented when the developer asked to include S17 in the full recomputation.
- Files changed: `workflow/libraries/compute_relabelled_alignment.py`, `workflow/libraries/compute_statistics.py`, `docs/reference/statistics.md`.

---

## 10:21 — Code reformatted to one consistent style

Kind: `refactor`

All the project's code (Python scripts, Snakefiles, the configuration file and the
`parquet2tsv.sh` helper) now follows the same layout rules: spacing, line length, blank lines,
comments and import order. Nothing the code does has changed; this was checked automatically.

- `config/config.yaml` now has a short comment above every setting whose meaning is not obvious.
  No value changed.
- The "Code conventions" section of the README summarises the rules to follow when you edit the
  code.

The reformatting changes some Snakemake commands, so the affected steps rerun. This change is
part of the full recomputation started on 2026-10-02, which reruns everything anyway.

### Context

- Request: Written for TODO entry S35 (approved by the developer on 2026-10-01), done before the full recomputation at the developer's request.
- Files changed: every `.py` file under `workflow/`, every Snakefile, `config/config.yaml`, `parquet2tsv.sh`, `README.md`.

---

## 10:58 — Caption Scene now aligned to MNI; repeated presentations averaged in the ISC

Kind: `new_feature`, `bugfix`

**Caption Scene brain data are now put into standard (MNI) space before the brain regions are
measured.** The dataset's BOLD files are in each participant's own anatomical space. Until now the
standard-space brain atlas was laid over them without any alignment, so each "region" covered a
different part of the brain in each participant. The pipeline now aligns each participant's
anatomical scan to the MNI template with ANTs, and uses that alignment to read the BOLD data at the
right place for every atlas region. A check image per participant
(`results/mind/caption_scene/registration/sub-*_t1w_to_mni_qc.png`) shows the aligned brain with the
template's outlines on top. In a test on one image, the region-by-region brain response changed
almost completely (correlation 0.16 between old and new), so all Caption Scene results change.

**NSD and Caption Scene: each participant's repeated viewings of an image are averaged first.**
The brain response of an image (ISC) compares each participant with the others. Participants saw
some images two or three times, and each viewing used to count as a separate participant, so a
person was partly compared with themselves. Now the repeats are averaged, so every participant
counts once. NSD results change moderately (median ISC 0.043 → 0.047 in a test).

**What you need:** the anatomical scans `V1/sub-*/anat/sub-*_ses-01_run-001_T1w.nii.gz` must be
present (they come with the dataset), and the pipeline downloads the MNI template the first time.
The cropped Caption Scene volumes in
`results/mind/caption_scene/intermediate_files/single_stimulus_bold/` (about 121 GB) are no longer
written or used and can be deleted.

### Context

- Request: Written for TODO entries S10 and S31 (approved by the developer on 2026-09-30), implemented when the developer asked to go on with S10 and S31.
- Files changed: see the developer changelog entry of the same name.

---

## 11:16 — Narratives: participants who heard a story twice now count once

Kind: `new_feature`

In the Narratives story "pieman", 11 participants were scanned twice. Each of their two scans
used to count as a separate participant when the story's brain response (ISC) was computed, so
those participants were partly compared with themselves. Their two scans are now averaged first,
as already done for NSD and Caption Scene. The effect is small: the pieman brain response is
almost unchanged (correlation 0.999 with the old one). The other stories are not affected.

### Context

- Request: Written after the developer asked to add the Narratives pieman repeats, found while implementing S10, to the batch.
- Files changed: `workflow/dataset_processing/narratives_dataset/Snakefile`, `workflow/dataset_processing/narratives_dataset/scripts/compute_narratives_isc.py`, `docs/reference/fmri_preprocessing.md`.

---

## 11:37 — New table: how reliable the brain representations are

Kind: `new_feature`, `bugfix`

The pipeline now measures how reliable each stimulus's brain representation (its 200-region ISC
pattern) is: it splits the participants at random into two halves 100 times and checks how well
the two halves agree. The results are in `results/mind/all_isc_reliability.tsv` (one row per
dataset) and `results/mind/{dataset}/isc_reliability.tsv` (one row per stimulus).

A first measurement on the current data shows a large difference between the datasets. For the
stories (Narratives, Nature Stories) the two halves agree very well (corrected reliability 0.97
and 0.86). For the short image events (NSD: 3 brain volumes per image; Caption Scene: 6) they
barely agree (0.03 and 0.01), so these brain representations are mostly noise. The Caption Scene
value will be measured again after the full recomputation, now that its brain data are aligned to
MNI.

Also fixed: a file-naming mismatch introduced earlier today in the new Caption Scene processing,
which would have stopped the Caption Scene brain-response step during the recomputation.

### Context

- Request: Written for TODO entry S30 (approved by the developer on 2026-09-30), implemented when the developer asked to proceed with S30.
- Files changed: see the developer changelog entry of the same name.

---

## 11:59 — Narratives: excluded stories listed once, by reason

Kind: `refactor`

In `config/config.yaml`, the Narratives stories left out of the analysis are now listed only once,
in two groups that say why: `schema_subtasks` (the schema sub-stories) and `notthefall_variants`
(the two scrambled versions of "Not the Fall"). The third list, `problematic_subtasks`, which
repeated both groups, is gone; the pipeline combines the two groups itself. The excluded stories
are exactly the same as before. To exclude another story, add it to one of the two groups.

### Context

- Request: Written after the developer chose to keep the two reason lists separate and derive the exclusion list from them.
- Files changed: `config/config.yaml`, `workflow/dataset_processing/narratives_dataset/Snakefile`, `docs/reference/fmri_preprocessing.md`.
