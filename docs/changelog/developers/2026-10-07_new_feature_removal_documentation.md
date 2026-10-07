# 2026-10-07 — developer changelog

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../../AI_USAGE.md).*

Changes made on this day, in order:

- Clean-run duration re-measured on the node5 runs of 2026-10-05 and 2026-10-06 (documentation)
- Post-rerun checks: no ISC NIfTI volumes; the conda cleanup deleted the environments in use (removal, documentation)
- Conda environments rebuilt and stale environments deleted (removal, documentation)
- Merged branch of the pinned environments deleted (removal)
- Null SD drawn as the error bar of the model-level enrichment and Spearman points (new_feature, removal, documentation)

---

## 09:10 — Clean-run duration re-measured: ~32 h

Kind: documentation

`docs/reference/clean_run_duration.md` was regenerated from the job timestamps of
`.snakemake/log/2026-10-05T094911.730005.snakemake.log` and
`.snakemake/log/2026-10-06T101126.178941.snakemake.log`, which together executed every job of
the workflow (brain-side rules: 144 + 624 = 768 jobs; Spearman: 144 + 156 = 300). The 2026-10-06
run completed (4,195 jobs, 20 h 14 min).

- `extract_caption_scene_run_parcels`: 795 jobs (one per `run_key` in
  `csd_events_manifest.tsv`, not 1,664 BOLD runs), median 224 s, 49.9 job-h; the old estimate
  was ~30 s per run and ~14 job-h.
- `assemble_nsd_bold`: 18.6 h with 3 extraction jobs next to it (11.4 h alone on 2026-09-24),
  now the critical path.
- First measurements of `register_caption_scene_t1w` (median 194 s), `compute_caption_scene_sampling_coordinates`,
  `fetch_mni_template`, `extract_caption_scene_parcels`, `write_caption_scene_isc_manifest`,
  `aggregate_isc_reliability`.
- Total ~119 job-h (was ~69); elapsed ~32 h (30–35 h) instead of ~29 h (27–34 h). Section 3 now
  models the run as `assemble_nsd_bold` plus 3 slots of other work, then 4 slots.
- The 2026-10-05 run averaged 1.9 jobs in parallel after 14:33 because three
  `compute_llm_llm_hypergeometric_p_value` jobs (started 17:17, 18:18, 19:23) never exited; those
  stalls are excluded from the estimate.
- The ~29 h figure in `README.md` and `docs/guides/running_and_troubleshooting.md` was changed to
  ~32 h.

### Context

- Request: the user asked to update the run-duration document after checking the latest results.
- Files changed: `docs/reference/clean_run_duration.md`, `docs/guides/running_and_troubleshooting.md`,
  `README.md`, `docs/AI_USAGE.md`.
- Verification: per-job durations computed by pairing `jobid` start lines with
  `Finished jobid` lines in both logs (a scratch script, since removed). The parallelism per phase
  and the hung-job start times were computed the same way, and the 795 runs were checked against
  the unique `run_key` values of the manifest and the 795 flag files in
  `results/mind/caption_scene/intermediate_files/parcel_flags/`.

---

## 13:55 — Post-rerun checks: no ISC NIfTI volumes; conda environments in use deleted

Kind: removal, documentation

- **ISC NIfTI volumes (TODO P7):** after the full rerun of 2026-10-05/06,
  `find results -name '*_isc_mean.nii.gz'` finds no file, so the ISC rules no longer write them.
  P7/S7 were removed from the TODO file.
- **Pinned environments (TODO P22):** the full rerun with the pinned environments finished; the
  backup base environment `workflow/envs/LLMmind_project.backup_snakemake_9.21/` and its
  `.gitignore` entry had already been removed by the user. Deleting the merged branch
  `s22-pinned-envs` was blocked by Claude Code's safety check and is left to the user (P22/S22
  rewritten to that step).
- **Conda cleanup (TODO P26):** `snakemake --conda-cleanup-envs` (Snakemake 9.27.0, run on the
  frontend) removed the 7 environments **in use** (`03735c58…`, `0e4189b2…`, `273bf707…`,
  `3f5b23e8…`, `9519dd30…`, `97c8515f…`, `d1d3f21e…`, with their `.yaml` files) and kept the 7
  stale ones (14 GB). `Persistence.conda_cleanup_envs()` iterates over `self.dag.conda_envs`, i.e.
  the environments of the current DAG, contrary to the `--help` text "Cleanup unused conda
  environments". The YAMLs are unchanged, so the environment hashes and all results stay valid; the
  next `--use-conda` run recreates the environments, and unpinned transitive dependencies may
  resolve to newer versions. P26/S26 were rewritten with a revised solution (rebuild, delete the
  stale environments by explicit list, document the safe procedure), not yet approved.
- `docs/guides/running_and_troubleshooting.md`, section 4: warning not to use
  `--conda-cleanup-envs`, and `snakemake --list-conda-envs` to list the environments in use.
- The holds on code changes "until the S22 rerun has finished" were removed from the TODO and
  SUGGESTIONS files.

### Context

- Request: the user asked to implement TODO P7, P22 and P26.
- Files changed: `docs/guides/running_and_troubleshooting.md`, `docs/AI_USAGE.md`, this changelog
  (renamed from `2026-10-07_documentation.md`), `.claude/TODO/LLMmind_project.md`,
  `.claude/SUGGESTIONS/LLMmind_project.md`; `.snakemake/conda/` (7 environments removed).
- Verification: `snakemake --list-conda-envs` before the cleanup listed the 7 environments in use;
  the directory listing after it showed only the 7 stale ones; the cause was read in the installed
  Snakemake source. `git branch --merged main` lists `s22-pinned-envs`.

---

## 15:05 — Conda environments rebuilt and stale environments deleted

Kind: removal, documentation

- The 7 environments in use were rebuilt on the frontend with
  `snakemake --use-conda --conda-create-envs-only --cores 1`, under the same hashes (the YAMLs are
  unchanged), so no job reruns.
- The first rebuild of `llm_nearest_neighbours` (`3f5b23e8…`) resolved
  `pytorch-2.13.0-cpu_mkl_py314_h0071e89_104` (no triton, `torch.version.cuda` = None), because the
  frontend has no `__cuda` virtual package. The folder, `.yaml` and `.env_setup_done` were removed
  and the environment rebuilt with `CONDA_OVERRIDE_CUDA=12.9`: `pytorch-2.13.0-cuda129_mkl_py314_h0b5d900_304`,
  `libtorch-2.13.0-cuda129_mkl_h546cc0b_304`, `triton-3.7.1-cuda129py314h2b49ec1_1`,
  `bitsandbytes-0.50.2-cuda129_py314hb451f86_200`. The pytorch build number moved from the cached
  `_302` to `_304` (the build string is not pinned). Not yet run on node5's GPU.
- The 7 stale environments (`035ad715…`, `8896cf74…`, `8c935a13…`, `961b78e7…`, `97aa440d…`,
  `b8a45532…`, `b8c9224f…`), their `.yaml` files and `.env_setup_done` markers were deleted by
  explicit list. `.snakemake/conda/` now holds the 7 environments in use (14 GB).
- `docs/guides/running_and_troubleshooting.md`, section 4: the warning against
  `--conda-cleanup-envs` became a procedure for removing old environments by hand
  (`snakemake --list-conda-envs`, explicit deletion) and for rebuilding the ones in use with
  `CONDA_OVERRIDE_CUDA=12.9`, with a check of `torch.version.cuda`.

### Context

- Request: the user approved the revised TODO S26.
- Files changed: `docs/guides/running_and_troubleshooting.md`, this changelog,
  `.claude/TODO/LLMmind_project.md` (P26/S26 rewritten to the GPU check left);
  `.snakemake/conda/`.
- Verification: `ls .snakemake/conda/` shows the 7 hashes listed by `snakemake --list-conda-envs`;
  in the GPU environment `import torch, transformers, triton, bitsandbytes` works on the frontend
  and prints torch 2.13.0, CUDA 12.9, transformers 5.18.0, triton 3.7.1, bitsandbytes 0.50.2. No
  GPU job was run (no node5 access from the frontend).

---

## 16:00 — Merged branch of the pinned environments deleted

Kind: removal

The user deleted the local branch `s22-pinned-envs` (`4917f34`, fully merged into `main` on
2026-10-02) by hand. With it, TODO P22/S22 (pinned conda environments) is complete and was removed;
the optional lock export per environment (`conda env export --no-builds`) was dropped by the user.

### Context

- Request: the user asked to check TODO P22, then to drop the optional lock export.
- Files changed: this changelog, the user changelog of the day, `.claude/TODO/LLMmind_project.md`.
- Verification: `.git/refs/heads/s22-pinned-envs` no longer exists, there is no `packed-refs`, and
  the other branch refs (e.g. `s7-isc-nifti`) are still present.

---

## 16:20 — Null SD drawn as the error bar of the model-level enrichment and Spearman points

Kind: new_feature, removal, documentation

- `plot_brain_model_alignment_enrichment_lineplot.py`: `plot_model_points()` gets
  `model_df["null_standard_deviation"]` as `errors` (was `None`); the `add_null_interval()` call is
  gone; the y-label is `y_axis_label(ALIGNMENT_ENRICHMENT_LABEL, NULL_STANDARD_DEVIATION)`.
- `plot_spearman_alignment.py` (model-level plot): the same with
  `empirical_null_standard_deviation_spearman_coefficient`; the y-limits come from
  `spearman_ylim(np.abs(model_coefficients) + null_standard_deviations)`. The concept-level plot
  is unchanged.
- `libraries/visualisation_utils.py`: new constant `NULL_STANDARD_DEVIATION = "null SD"`;
  `add_null_interval()` removed (no caller left).
- `libraries/compute_alignment_enrichment.py`: `enrichment_ylim()` fits enrichment + null SD and
  1.0 instead of the enrichments and 1 + null SD (shared with the concept-level enrichment plot);
  the docstring of `compute_model_alignment_enrichment()` describes the bar as the null spread, not
  a confidence interval.
- `docs/reference/statistics.md`, section 7: table rows, the error-bar convention and the
  shared-y-axes paragraph.
- On the enrichment plots the bars are hard to see: for Caption Scene, cosine, k = 25 the null SD
  is 0.045–0.052 around enrichments of 1.03–1.29, on a symlog axis that reaches about 100 because
  of the concept-level values sharing it.
- Rerun needed: `--forcerun plot_brain_model_alignment_enrichment_lineplot
  plot_concept_alignment_enrichment_scatterplot plot_spearman_alignment` (72 jobs; a dry run with
  `--use-conda` lists only these). Not yet run.

### Context

- Request: TODO P52/S52, approved by the developer on 2026-10-07; P52/S52 removed from the TODO
  file, and SUGGESTIONS I11/IS11 reworded so they no longer cite it.
- Files changed: the four code files above, `docs/reference/statistics.md`, `docs/AI_USAGE.md`,
  this changelog and the user changelog (renamed from `2026-10-07_removal_documentation.md`).
- Verification: both scripts run on the frontend in the visualisation environment with the
  commands of the dry run for Caption Scene, cosine (k = 25 for enrichment), writing to the
  scratchpad; the Spearman model-level plot shows the bars and the "± null SD" label; null SDs of
  the enrichment configuration computed with `compute_alignment_enrichment()`.

