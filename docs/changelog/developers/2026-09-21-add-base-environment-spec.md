# 2026-09-21 — Add base environment spec at workflow/envs/

## Summary

The base environment used to run Snakemake itself
(`workflow/envs/LLMmind_project`, referenced by `.envrc` and documented in
`README.md`'s Setup section) existed only as a materialized conda prefix on
disk — there was no versioned spec describing its contents, so it could not
be recreated or reviewed. Added a minimal conda environment YAML under
`workflow/envs/` to serve as that spec.

## Changes

### `workflow/envs/LLMmind_project_environment.yaml` (new)

```yaml
channels:
  - conda-forge
  - nodefaults
dependencies:
  - python
  - snakemake-minimal
```

Deliberately minimal: only `python` and `snakemake-minimal`. Per-rule conda
environments (numpy/pandas/pyarrow/etc., e.g.
`workflow/isc_nearest_neighbours/envs/isc_nearest_neighbours_environment.yaml`)
remain separate and are created on demand by Snakemake when run with
`--use-conda` — the base env only needs to be able to invoke `snakemake`
itself. Channel list (`conda-forge`, `nodefaults`) matches the convention
already used by the per-rule env files.

`snakemake-minimal` was chosen over `snakemake` to avoid pulling in the full
package's optional reporting/plugin dependencies, keeping the base env as
small as possible.

## Notes / caveats for future edits

- This file is a spec, not the materialized environment — the existing
  `workflow/envs/LLMmind_project` prefix was not regenerated from it in this
  session. To (re)build the env from the spec:
  `conda env create -f workflow/envs/LLMmind_project_environment.yaml -p workflow/envs/LLMmind_project`.
- If the base environment ever needs additional tooling (e.g. for
  `--use-conda` environment creation backends, linting, etc.), add it here
  rather than to a per-rule env file.

## Files touched

- `workflow/envs/LLMmind_project_environment.yaml` (new)
