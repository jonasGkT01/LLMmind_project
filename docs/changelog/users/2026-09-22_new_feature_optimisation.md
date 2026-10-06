# 2026-09-22 — changes for users

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../../AI_USAGE.md).*

Changes made on this day, in order:

- Concept-level plot now shows raw alignment, not enrichment (new_feature)
- NSD brain-data processing is dramatically faster (optimisation)
- Alignment line plots and concept-level plots now share the same vertical scale (new_feature)
- NSD-scale runs no longer crash, and brain-response computation is much faster (optimisation)
- Similarity comparisons no longer need huge intermediate files (optimisation)

---

## Concept-level plot now shows raw alignment, not enrichment

Kind: `new_feature`

### What changed

The concept-level LLM-brain plot used to show each concept's alignment
score as a ratio against chance level ("enrichment"). It now shows the raw
alignment score instead, matching the model-level plot, which has always
shown raw alignment scores.

### What this means for you

- The plot's file name and location changed:
  `results/alignment_enrichment_plots/dataset-{dataset}_{similarity}-concept_alignment_enrichment_{k}NN.png`
  is now
  `results/concept_alignment_scatterplots/dataset-{dataset}_{similarity}-concept_alignment_{k}NN.png`
  (the directory name now makes clear this is a scatterplot).
- The y-axis now shows "Alignment score" (the same [0, 1] score used
  elsewhere) instead of a ratio. The dashed reference line still marks the
  hypergeometric chance level, just in raw-score units instead of as a
  ratio fixed at 1.0.
- Boxes/points that previously sat above or below the `1.0` reference line
  will now sit above or below the reference line at its raw-score value;
  the relative ordering of models and the degenerate-box markers are
  unaffected.

### Action needed

Re-run the pipeline (or just the `plot_concept_alignment_scatterplot` rule)
to regenerate this plot under its new path. Update any dashboards,
notebooks, or scripts that reference the old
`results/alignment_enrichment_plots/...concept_alignment_enrichment...`
path.

---

## NSD brain-data processing is dramatically faster

Kind: `optimisation`

### What changed

The step that prepares NSD (Natural Scenes Dataset) brain scans for
analysis — registering each fMRI scan into a standard brain space (MNI) so
scans from different people can be compared — was taking an extremely long
time to run. We found why and fixed it.

The step processes each individual viewing of an image (there are
hundreds of thousands of these across all 8 participants) one at a time.
For every single one, it was reloading the same reference file from disk
and rebuilding the same internal lookup table from scratch, even though
that file and table never change for a given participant. That repeated,
unnecessary work was the vast majority of the total run time — not the
actual brain-data processing itself.

Two fixes:

- That reference file and lookup table are now loaded once per participant
  and reused for all of that participant's scans, instead of being
  reloaded from scratch for every single viewing.
- This step can now also use multiple processor cores at once to work on
  several scans in parallel, instead of handling them one after another.

### What this means for you

- Preparing NSD data should now take a small fraction of the time it used
  to.
- The results are unchanged — we checked that the new, faster version
  produces byte-for-byte identical output to the old version. Nothing about
  the brain-data analysis itself changed.
- This step will now use more CPU cores than before while it runs (up to
  however many you give the pipeline via `--cores <N>` when you launch it).
  If you're running this alongside other work on a shared machine, keep
  that in mind — the more cores you allow, the faster this step finishes,
  but the more of the machine it will use while it's running.

### Action needed

None. Existing NSD outputs remain valid — you don't need to rerun anything
for correctness. If you do rerun the NSD processing step, expect it to
finish much faster than before.

---

## Alignment line plots and concept-level plots now share the same vertical scale

Kind: `new_feature`

### What changed

The model-level alignment line plots (in `results/alignment_lineplots/`)
sometimes showed their points and lines crowded right up against the top
edge of the plot, even though the same values on the concept-level plot
(in `results/concept_alignment_scatterplots/`) had comfortable headroom.
Both plots now use the same fixed vertical range, `0` to `1`, which is the
full possible range of the alignment score they both show.

### What this means for you

- Line plots and concept-level plots for the same dataset now look
  consistent when placed side by side — same vertical scale, same plot
  height.
- No more misleadingly "maxed out" looking line plots; a point near the
  top of the plot now genuinely means the alignment score is close to 1,
  not just that it was the largest value in that particular plot.
- No action needed — this only changes how existing results are drawn.
  Re-run the relevant `plot_brain_model_alignment_lineplot` and
  `plot_concept_alignment_scatterplot` rules to regenerate the plots with
  the new scale.

---

## NSD-scale runs no longer crash, and brain-response computation is much faster

Kind: `optimisation`

### What changed

The NSD dataset (Natural Scenes Dataset) has far more usable images
(~66,000) than any other dataset in this pipeline. Several steps that
compare models and brain data to each other were written assuming every
dataset was small enough to hold entirely in memory at once. That
assumption held for every other dataset, but not for NSD at its full size,
and it started causing real problems this session:

- The step that finds each image's nearest neighbours (in a model's
  representation space) was crashing outright — the machine ran out of
  memory and the process was killed.
- Three other steps (the brain-model alignment test, the model-vs-model
  alignment test, and the "relabelling" significance test) were either
  crashing with an error, or would have used far more memory and disk
  activity than actually necessary, once run at NSD's full scale.
- Separately, the step that computes how consistent people's brain
  responses are to each other (inter-subject correlation, or "ISC") was
  extremely slow for NSD specifically, because it processes each of the
  ~66,000 images individually and was doing so in a way that didn't take
  advantage of how fast modern computers can do this kind of math in bulk.

All of these are now fixed. None of them change any scientific result —
every fix was checked against the exact same computation running the old
way, on real data, and the numbers matched exactly (or matched to floating
point rounding, in the ISC case).

### What this means for you

- Running the pipeline on NSD at full scale should now actually complete,
  instead of crashing partway through.
- The brain-response consistency (ISC) computation for NSD should now
  finish roughly 500x faster than before — what would have taken hours is
  now expected to take well under a minute.
- The steps that were crashing now use only a small, fixed amount of
  memory regardless of how many images are involved, instead of trying to
  hold everything at once.
- We also found and fixed an unrelated problem that was stopping a full
  pipeline launch: the downloaded model files had accidentally been left
  in a "read-only" state (a side effect of the tool used to download them,
  not something anyone did on purpose), which was blocking Snakemake from
  even starting. That's been corrected.
- A new helper was added that can automatically pick a reasonable
  "batch size" for processing images/text based on how large a given
  model is, instead of that number having to be manually chosen for each
  model. It isn't being used by the pipeline yet — it's ready for a
  follow-up change that will let the model-embedding step process
  multiple images/texts at once instead of one at a time (a separate,
  larger speed improvement planned for later).

### Action needed

None for existing outputs — nothing about already-computed results
changes. If you were previously avoiding a full run on NSD because it was
crashing, it should now be safe to try again. Two things worth knowing
before a full launch:

- **Disk space**: NSD's full-scale comparisons produce large files (each
  model's similarity data is roughly 88GB). Running this for many models
  back-to-back needs a substantial amount of free disk space — worth
  checking beforehand if you're low.
- **Model downloads**: if you see Snakemake complain about "write-protected"
  files under `resources/models/`, or about the software environment
  having changed for the model-download step, see the developer changelog
  entry for the exact commands to resolve it.

---

## Similarity comparisons no longer need huge intermediate files

Kind: `optimisation`

### What changed

Every step that compares how similar two things are (two images, two
pieces of text, a model's representation of a stimulus, a brain response)
used to work by first writing out a complete "everything compared to
everything else" table, then reading only a small piece of it back out
later. For most datasets in this pipeline that table was small enough not
to matter. For NSD (the dataset with by far the most usable images), it
wasn't: each model's table was a fixed ~88GB, and the brain-response side
was about to become the same size once a recent fix (see the 2026-09-21
"NSD now includes many more images" note) let it use far more images than
before. Running the full set of configured models would have needed well
over 1TB of disk space, on a machine that had well under that much free.

This is now fixed properly: those big intermediate tables are never
created at all. Instead, each comparison is done in smaller pieces and
immediately reduced down to "which are this item's most similar matches,"
which is the only thing every later step actually uses. The
significance-testing step that repeats a comparison thousands of times
with randomly shuffled labels was also changed to do all of its shuffling
in one pass per dataset instead of repeating the same random shuffles
separately for every neighbourhood size — the random results are
identical, it's just no longer wastefully redone.

### What this means for you

- Running the pipeline on NSD (or any dataset with several neighbourhood
  sizes configured) should now use a small fraction of the disk space it
  used to, since the big intermediate tables no longer exist.
- Nothing about how you run the pipeline changes — same command, same
  `config.yaml`. This is purely a behind-the-scenes storage change.
- On this machine, roughly 129GB of now-unused old-format files (the big
  comparison tables, plus old per-neighbourhood-size files that have been
  replaced by a single combined file) were deleted as part of this session,
  freeing that space back up.
- If you kept your own copies of, or scripts referencing, files named
  `*_similarity.parquet` or ending in a specific neighbourhood-size suffix
  like `_50NN.parquet` for the nearest-neighbour files, those no longer
  exist — the pipeline now produces one neighbour file per
  model/dataset/metric (without a size suffix in the name) that
  automatically covers every neighbourhood size you have configured.

### Action needed

None for how you use the pipeline day to day. If you have older
already-computed results for NSD (or any multi-neighbourhood-size dataset)
sitting around from before this change, they used the old file layout and
should be regenerated by rerunning the pipeline rather than mixed with new
outputs.
