# 2026-10-09 — changes for users

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../../AI_USAGE.md).*

Changes made on this day, in order:

- Jobs no longer get stuck after finishing their work (bugfix, documentation)

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
