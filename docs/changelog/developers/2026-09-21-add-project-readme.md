# 2026-09-21 — Add top-level README.md

## Summary

The project previously had no root-level `README.md` and no reference
documentation of any kind (verified via `find . -iname "*.md" -o -iname
"README*"` at the project root, excluding the conda env under
`workflow/envs/LLMmind_project` and third-party model-card READMEs under
`resources/models/*`). Added a `README.md` to serve as the entry point for
the repository.

## Source material

Content was derived entirely from static inspection of the existing
repository — no code changes were made:

- `workflow/Snakefile` — top-level rule graph (`PAIRINGS`,
  `LLM_LLM_PAIRINGS`, `HEATMAP_PAIRINGS`, `SPEARMAN_PAIRINGS`, `rule all`)
  and the `include:` order, used to derive the pipeline stage list and
  the repo-layout module descriptions.
- `config/config.yaml` — `datasets`, `models`, `similarity_types`,
  `number_of_relabellings` — used for the Datasets/Models sections.
- `.envrc` and `workflow/*/envs/*.yaml` — used for the Setup section
  (conda env activation, per-rule `conda:` environments).
- `.gitignore` — confirmed `resources/`, `results/`, and the conda env dir
  are untracked, reflected in the repo-layout notes.

## Changes

### `README.md` (new)

Added at the project root with the following sections: Overview (pipeline
purpose and 6-step processing summary), Repository layout, Datasets, Models,
Setup, Running the pipeline, Outputs, Documentation (links to
`docs/changelog/developers/` and `docs/changelog/users/`).

## Notes / caveats for future edits

- The Overview section's description of pipeline purpose and stage ordering
  was inferred from rule/file naming and the `include:` order in
  `workflow/Snakefile`, not from any existing prose documentation (none
  existed) — verify against domain knowledge before treating it as
  authoritative.
- No dependency-pinning or install instructions beyond the existing
  conda-env mechanism were documented, since none exist in the repo.
- Keep this file in sync with `workflow/Snakefile` and `config/config.yaml`
  when datasets, models, or pipeline stages are added or removed — the
  README enumerates both by name.

## Files touched

- `README.md` (new)
