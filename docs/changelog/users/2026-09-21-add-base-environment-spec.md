# 2026-09-21 — Recipe added for the base setup environment

## What changed

There's now a file, `workflow/envs/LLMmind_project_environment.yaml`, that
lists exactly what's needed in the base environment you activate to run the
pipeline (just Python and Snakemake, kept as small as possible).

## What this means for you

Previously, that base environment only existed on this machine — if it ever
got lost or you needed to set it up somewhere new, there was no recipe to
rebuild it from scratch. Now there is one.

## Action needed

None for your day-to-day workflow — you still activate the environment the
same way described in `README.md`. This new file only matters if you (or
someone new) ever needs to recreate the base environment from scratch.
