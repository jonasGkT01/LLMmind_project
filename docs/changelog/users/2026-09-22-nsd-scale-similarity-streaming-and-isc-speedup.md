# 2026-09-22 — NSD-scale runs no longer crash, and brain-response computation is much faster

## What changed

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

## What this means for you

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

## Action needed

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

*This note was drafted by an AI coding assistant (Claude Code, model
Claude Sonnet 5) and reviewed by the developer before being published.*
