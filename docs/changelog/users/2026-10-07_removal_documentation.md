# 2026-10-07 — changes for users

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../../AI_USAGE.md).*

Changes made on this day, in order:

- New estimate of how long a full run takes: about 32 h (documentation)
- The software environments will be rebuilt at the next run (removal, documentation)
- Software environments rebuilt, old ones removed (removal, documentation)

---

## 09:10 — A full run takes about 32 hours

Kind: documentation

The page [`clean_run_duration.md`](../../reference/clean_run_duration.md) now uses the times
measured in the two node5 runs of 5 and 6 October, which together rebuilt the whole project.
A full run on node5 takes about **32 hours** (30–35 h), plus about 1.5 h if the models must be
downloaded, instead of the 29 hours estimated before.

The difference comes mostly from the Caption Scene brain data: extracting each scanner run takes
about 4 minutes instead of the expected 30 seconds. This step runs next to the NSD data assembly,
which takes about 18.6 hours and sets the length of the whole run.

---

## 13:55 — The software environments will be rebuilt at the next run

Kind: removal, documentation

A cleanup command meant to delete old, unused software environments deleted the ones the project
uses instead. Your results are not affected and nothing needs to be recomputed, but the next run
with `--use-conda` first rebuilds the environments, which takes extra time. The old environments
(14 GB) are still on disk and will be removed separately.

Do not use `snakemake --conda-cleanup-envs`: in the Snakemake version the project uses, it deletes
the environments in use. The [running guide](../../guides/running_and_troubleshooting.md),
section 4, explains this.

The full rerun also confirmed that the brain-similarity steps no longer write the large brain
map files (`*_isc_mean.nii.gz`) that older versions produced.

---

## 15:05 — Software environments rebuilt, old ones removed

Kind: removal, documentation

The software environments the project uses have been rebuilt, so the next run starts right away
and nothing is recomputed. The old, unused environments were removed. The environment that
computes the model embeddings on the GPU has been checked on the frontend but has not yet run on
node5's GPU.

If you ever need to clean up or rebuild the environments yourself, follow section 4 of the
[running guide](../../guides/running_and_troubleshooting.md). On a machine without a GPU, start
the rebuild command with `CONDA_OVERRIDE_CUDA=12.9`, otherwise the GPU environment gets a version
of PyTorch that cannot use the GPU.

