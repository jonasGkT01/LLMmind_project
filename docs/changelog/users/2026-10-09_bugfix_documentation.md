# 2026-10-09 — changes for users

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../../AI_USAGE.md).*

Changes made on this day, in order:

- Jobs no longer get stuck after finishing their work (bugfix, documentation)
- Where the Nature Stories transcripts come from is now documented (documentation)

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
