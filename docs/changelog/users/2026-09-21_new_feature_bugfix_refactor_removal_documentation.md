# 2026-09-21 — changes for users

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../../AI_USAGE.md).*

Changes made on this day, in order:

- Small cleanup to the alignment plotting scripts (refactor)
- New README added to the project (documentation)
- Recipe added for the base setup environment (new_feature)
- Boxes with no visible spread are now marked on alignment plots (new_feature, removal)
- Consistency fix for how significance tests generate randomness (bugfix)
- README now explains what data you need and what each part does (documentation)
- NSD dataset now includes many more images (new_feature)

---

## Small cleanup to the alignment plotting scripts

Kind: `refactor`

### What changed

We tidied up the two scripts that generate the Spearman alignment plot and
the concept-alignment enrichment plot. This was a behind-the-scenes cleanup,
not a change to how the analysis works.

### What this means for you

- **No change to your results.** The plots you generate, and the summary
  numbers printed alongside them (n, min, median, max, etc.), look exactly
  the same as before.
- The code behind these two plots is now easier to maintain, which reduces
  the chance of the two plots' summary output drifting out of sync in future
  updates.

### Action needed

None. You can keep using these plotting scripts exactly as before.

---

## New README added to the project

Kind: `documentation`

### What changed

The project now has a `README.md` file at the top level. Previously there
was no overview document at all.

### What this means for you

If you're new to this project, or just need a refresher, you can now open
`README.md` to find:

- A plain explanation of what the pipeline does
- A map of the folders in the repository and what each one is for
- Which datasets and models are currently supported
- How to set up your environment and run the pipeline
- Where your results will end up once it finishes

### Action needed

None. This is a new reference document, not a change to how the pipeline
runs. Take a look next time you or a teammate needs a refresher on the
project.

---

## Recipe added for the base setup environment

Kind: `new_feature`

### What changed

There's now a file, `workflow/envs/LLMmind_project_environment.yaml`, that
lists exactly what's needed in the base environment you activate to run the
pipeline (just Python and Snakemake, kept as small as possible).

### What this means for you

Previously, that base environment only existed on this machine — if it ever
got lost or you needed to set it up somewhere new, there was no recipe to
rebuild it from scratch. Now there is one.

### Action needed

None for your day-to-day workflow — you still activate the environment the
same way described in `README.md`. This new file only matters if you (or
someone new) ever needs to recreate the base environment from scratch.

---

## Boxes with no visible spread are now marked on alignment plots

Kind: `new_feature`, `removal`

### What changed

On the concept-level enrichment plot and the concept-level Spearman plot,
some models could appear to have no box at all, as if their data were
missing. That box is now marked with a small red diamond whenever this
happens.

### What this means for you

- **A missing-looking box is not missing data.** It means that model's
  result had essentially no spread across concepts — most or all concepts
  landed on the same value, so the box collapsed to a flat line and was
  easy to miss. The red diamond makes this visible instead of it silently
  blending into the axis.
- **No numbers have changed.** Alignment scores, p-values, and every other
  computed value are exactly the same as before — this only changes how a
  specific kind of result is drawn.
- The per-run console printout of summary statistics (min/median/max/etc.
  for each model) that appeared when generating these two plots has been
  removed, since it was added specifically to investigate this issue and is
  no longer needed.

### Action needed

None. Regenerate the two affected plots (concept-level enrichment,
concept-level Spearman) to see the new markers on any results that have
this zero-spread pattern.

---

## Consistency fix for how significance tests generate randomness

Kind: `bugfix`

### What changed

The pipeline computes two kinds of significance tests by comparing your
real results to many randomly shuffled ("relabelled") versions: one for how
well a model's representations align with brain activity, and one for how
well two models' representations align with each other. Under the hood,
these two tests were generating their random shuffles in two different
ways. We found no evidence this made either test wrong, but there was no
good reason for them to differ, so both now generate their random shuffles
using the same method.

### What this means for you

- The brain-model alignment test's results (per-concept and per-model
  p-values) are **unchanged** — you don't need to do anything for those.
- The model-model alignment test's results will change slightly the next
  time you regenerate them, because its random shuffles are now drawn
  differently. This does not mean anything was wrong with the old numbers —
  a significance test based on random shuffling is expected to give
  slightly different p-values if you draw a different set of random
  shuffles, the same way re-rolling dice gives a different sequence each
  time. The overall conclusions (which model pairs are/aren't
  significantly aligned) should not change.
- As a reminder (unchanged from before): only the overall alignment between
  two models is tested for significance — there isn't a separate
  significance test for each individual concept in the model-model
  comparison.

### Action needed

If you rely on the model-model alignment p-values
(`dataset-*_model-*_model-*_empirical_*-alignment_score_*NN.p_value.tsv`),
regenerate them by rerunning the pipeline so they reflect the corrected,
consistent random-shuffling method. No action is needed for the brain-model
alignment results.

---

## README now explains what data you need and what each part does

Kind: `documentation`

### What changed

The `README.md` file has two new sections:

- **Subprojects** — a plain description of what each piece of the pipeline
  actually does, from turning raw brain scans into "mind" representations,
  through extracting model embeddings, to scoring alignment and making the
  final plots.
- **Input data** — a checklist of exactly which raw data files need to exist,
  and where, before you can run the project for the first time, plus a new
  "Organising the input data on disk" section showing how to get them into
  place.

### What this means for you

If you've ever wondered "what files do I actually need before I can run
this?" or "what does the `llm_llm_alignment` folder even do?", the README
now answers both directly instead of you having to dig through the code or
ask around.

The Input data section also spells out which things you *don't* need to
worry about providing yourself — pretrained model weights and the brain
atlas download automatically the first time they're needed (as long as
you have internet access), and the `results/` folder is entirely generated
by the pipeline.

### Action needed

None for existing setups that already work. If you're setting up a fresh
checkout of the project, follow the new "Organising the input data on disk"
section in the README before your first run — it walks through linking the
downloaded datasets into the right place.

---

## NSD dataset now includes many more images

Kind: `new_feature`

### What changed

The NSD (Natural Scenes Dataset) brain-image data is processed differently
now, in a way that keeps far more of the available images usable.

Previously, an image could only be included in the analysis if **every one**
of the 8 NSD participants had seen it at least 3 times. That rule was
specific to NSD — no other dataset in this project works that way — and it
threw away most of the data: only 515 of the roughly 1,000 shared images
made it through.

Now NSD follows the same rule already used for the other datasets in this
project (like Caption Scene): an image is kept as long as there are at
least two brain-activity recordings of someone looking at it, no matter
which participant, and no matter how many times each participant saw it.
This is the minimum needed to check whether people's brains respond
similarly to an image at all — you can't compare a single recording to
itself. Below that minimum, an image simply can't be used; above it,
everything available is used.

We also fixed a related issue: when a participant saw the same image more
than once, those separate viewings were previously being stitched together
into one long, continuous brain recording, as if they happened back to
back. They didn't — they happened at different, often far-apart moments
during the experiment. Each viewing is now treated as its own separate,
independent recording, which is the more accurate way to combine them.

### What this means for you

- Many more NSD images are now available for analysis than before — not
  just the ~515 that previously met the strict 3-repetitions-for-everyone
  rule.
- Each image's number of usable recordings can now differ from image to
  image, and from participant to participant. That's expected: some images
  were shown more often, or to more participants, than others.
- The final output you consume is unchanged in shape: one brain-response
  summary per image, feeding into the same downstream comparisons
  (nearest-neighbour search, brain-model alignment) as before.

### Action needed

If you use NSD results, regenerate them by rerunning the pipeline — the
set of included images and how each image's brain response is computed
have both changed, so old NSD outputs are not compatible with this update
and should be treated as outdated.
