# 2026-10-06 — developer changelog

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../../AI_USAGE.md).*

Changes made on this day, in order:

- `threads:` removed from every rule; internal workers from `number_of_workers` (bugfix)
- README: input files not produced by the download (documentation)
- Documentation restructured: slim README, running guide, daily changelogs, central AI attribution (documentation)

---

## 10:30 — `threads:` removed from every rule; internal workers from `number_of_workers`

Kind: `bugfix`

### Problem

The run started on 2026-10-05 at 09:49 stalled at 38,484 of 42,679 steps. Three
`compute_llm_llm_hypergeometric_p_value` jobs had written their complete output but their Python
process never exited (main thread blocked in `futex`), so Snakemake kept 3 of the 4 cores
reserved for them. Every remaining job depended on `assemble_nsd_bold`, which declared
`threads: workflow.cores` (4) and so could never be scheduled on the single free core. Snakemake
looped on job selection from 01:06 until the jobs were killed at about 09:55.

### Changes

- `config/config.yaml`: new top-level key `number_of_workers: 4`.
- The `threads:` directive was removed from the four rules that had one. Each now takes
  `params: number_of_workers = config["number_of_workers"]` and passes it where it used
  `{threads}`:
  - `assemble_nsd_bold` (`workflow/dataset_processing/nsd_data_dataset/Snakefile`): was
    `workflow.cores`; `--jobs {params.number_of_workers}`.
  - `register_caption_scene_t1w` (`workflow/dataset_processing/caption_scene_dataset/Snakefile`):
    was 8 (capped by Snakemake at `--cores`); `antsRegistrationSyNQuick.sh -n
    {params.number_of_workers}`.
  - `aggregate_all_p_value_outputs` (`workflow/llm_mind_alignment/Snakefile`) and
    `aggregate_all_llm_llm_p_value_outputs` (`workflow/llm_llm_alignment/Snakefile`): were 4;
    `--threads {params.number_of_workers}`.
- No script changed: `assemble_nsd_bold.py --jobs` and the aggregators' `--threads` keep their
  names and meaning.

### Behaviour

- Snakemake now counts every job as one core, so no job waits for several free cores. The four
  rules above may use up to `number_of_workers` CPUs while counted as one, so the run can briefly
  exceed `--cores` (e.g. 4 + 3 = 7 busy processes on node5's 4-CPU Slurm allocation).
- No extra reruns: none of the four rules had produced its output in the current rerun yet
  (`register_caption_scene_t1w` outputs are missing, `assemble_nsd_bold` and the aggregations
  were still queued), so the new param and shell commands add no job.
- Not addressed: why the three hypergeometric jobs hung at exit.

### Verification

- `grep` finds no `threads:` or `workflow.cores` left in the project's Snakefiles.
- `snakemake --use-conda --cores 4 --resources gpu=1 --rerun-incomplete -n --quiet rules` on the
  frontend parses the workflow and schedules 4,195 jobs, the same number the stalled run still had
  to do, among them the 3 killed hypergeometric jobs, `assemble_nsd_bold`, the 8
  `register_caption_scene_t1w` jobs and 795 `extract_caption_scene_run_parcels` jobs (more are
  added after the Caption Scene checkpoint).

### Context

- Request: Written after the developer asked why the run had stalled since 01:00 and then asked to remove every rule's core specification; the developer chose a fixed worker count from the config over running these steps single-process.
- Files changed: `config/config.yaml`, `workflow/dataset_processing/nsd_data_dataset/Snakefile`, `workflow/dataset_processing/caption_scene_dataset/Snakefile`, `workflow/llm_mind_alignment/Snakefile`, `workflow/llm_llm_alignment/Snakefile`, `README.md`, `docs/reference/clean_run_duration.md`.

---

## README: input files not produced by the download

Kind: `documentation`

New `README.md` section "Input files not produced by the download", under "Input data": the input
files that come from the public datasets but that the `public_datasets` project does not produce
(`caption_scene_dataset/V1/stimuli/CSD/`, extracted from `CSD.rar`; `narratives_dataset/scan_exclude.json`,
copied from the Narratives DataLad dataset; `nature_stories_dataset/responses/new_run_onsets.json`,
a corrected copy of `run_onsets.json` with six story boundaries shifted by 1–2 TRs, with the table
of original and corrected values and how to re-derive them).

### Context

- Request: the developer asked for a list of the publicly obtainable input files that
  `public_datasets` does not generate, and where they come from. This entry was written later the
  same day, during the restructuring below, since the README change had none.
- Files changed: `README.md`.

---

## 16:30 — Documentation restructured: slim README, running guide, daily changelogs, central AI attribution

Kind: `documentation`

### Problem

An external review of the documentation found that `README.md` (46 KB) mixed overview, methods,
rerun mechanics, troubleshooting, plot specifications and dated migration notes, duplicating the
reference pages. The duplication had already produced a contradiction: the troubleshooting entry
"Results don't change after editing a dataset's inclusion rules" still said that the manifest
scripts run from `shell:` rules and are not rerun when their code changes, which the
`code_version()` rerun trigger of 2026-10-05 had made false; the Narratives entry called the
manifest rules "`run:` rules without params". The reference pages also carried TODO IDs, dated
"before/since" notes and large AI attribution blocks, and the changelog had one file per change
and audience (64 developer and 63 user files).

### Changes

- `README.md` cut to an overview (21 KB, 7 KB of which is the unchanged "Input data" section):
  purpose, documentation index (moved near the top), layout, short module and dataset
  descriptions, models, setup, minimal run commands, outputs. "LLMs" in the
  opening sentence replaced by "models", with a note that `llm` in names means any model.
- New `docs/guides/running_and_troubleshooting.md`, the single home for: run variations;
  parallelism and `number_of_workers`; when Snakemake reruns a job, with the full lists of rules
  covered by `code_version()` (2 `make_*_manifest`, 7 `write_*_manifest`, 4 `aggregate_*`) and of
  those not covered (plots, embedding/ISC code, `create_isc_manifest`,
  `write_narratives_problematic_stimuli`, `write_nature_stories_excluded_stimuli`, and the
  config values and files the manifests read); `similarity_types`,
  `minimum_subjects_per_stimulus` and `max_chunk_length` (table moved from the README); pinned
  environments and the upgrade procedure; multimodal and MoE limitations; troubleshooting, with
  the two stale entries rewritten, the "rule envs don't pin library versions" sentence corrected
  (only unlisted dependencies are unpinned), and the dated stale-output notes gathered without
  dates under "Leftover outputs from older versions".
- `docs/reference/statistics.md`: the plot layout conventions (titles, legend, model order,
  colours, colour-vision checks, degenerate boxes, shared and `symlog` y-axes) and the note on
  Spearman alignment under the `spearman` similarity moved here from the README, plus a line
  saying that "scatterplot" names are historical.
- `docs/reference/fmri_preprocessing.md`: TODO IDs removed (P9, P10, P30, P31, S30, S31); the
  "before 2026-10-02" notes moved to a new `## Changes` section; the constant-signal tolerance
  moved here from the README; the "Basis" and "Not verified" notes of the attribution block moved
  into the sources.
- `docs/reference/clean_run_duration.md`: TODO IDs removed (S30, S31, S33, S34); the short
  answer, section 1 and section 3 no longer refer to a run in progress (the `assemble_nsd_bold`
  history moved to its `## Changes` entry).
- `docs/reference/model_embeddings.md`: sources and "not verified" note moved into a new section
  6; `## Changes` section added; `--pool` mentioned; chunk-length link points to the guide.
- Changelogs: the 127 per-change files were merged, by a script, into one file per day and
  audience, named `YYYY-MM-DD_<kinds>.md`, where the kinds come from the fixed list `new_feature`,
  `bugfix`, `optimisation`, `refactor`, `removal`, `documentation`. Each change is a `##` section
  with its time (when the old file name had one), its kinds, its body (headings demoted by one
  level, text unchanged; a check confirmed that every body line of the old files is present) and a
  `### Context` list keeping the "Request", "Basis", "Files changed", "Verification" and similar
  notes of the old attribution blocks. Tool, model, date and review-status lines were dropped;
  links between entries now point to the day files.
- New `docs/AI_USAGE.md`: the AI attribution policy and a table of every AI-written or AI-edited
  file (documentation, code, environment files, `.gitignore`, and the project's TODO and
  SUGGESTIONS lists) with role, date and model of the latest AI edit, and review status. Every
  documentation file now carries only the one-line note under its title, linking there; the
  attribution blocks at the end were removed (including the 15 "Review it before committing"
  lines). Code headers are unchanged.
- `LLMmind/.claude/CLAUDE.md`, section 1: rules updated for daily changelog files and the central
  attribution file.
- `LLMmind/.claude/TODO/LLMmind_project.md`: P43/S43 rewritten (the `fmri_preprocessing.md` half is
  solved), and the S7 link to the old changelog file updated.

- `README.md`: the "Code conventions" section was removed at the developer's request, after the
  restructuring; the layout rules are kept in `LLMmind/.claude/CLAUDE.md`, section 4, outside this
  repository.

### Not changed

- No code, config or result file. The `scatterplot` rule and folder names stay; renaming them
  would need a plot rerun.

### Context

- Request: the developer pasted an external review of the documentation and asked for an opinion,
  then approved: fixing the stale manifest/rerun text; splitting the README into an overview plus
  a guide, keeping `README.md` at the project root and the documentation index inside it; removing
  TODO IDs and dated notes from the reference pages; one changelog file per day per audience,
  named after the date and the kinds of work done; and one central AI attribution file with a list
  of every file, its latest AI edit and the model.
- Files changed: `README.md`, `docs/AI_USAGE.md` (new), `docs/guides/running_and_troubleshooting.md`
  (new), the four `docs/reference/*.md` pages, every file under `docs/changelog/`,
  `LLMmind/.claude/CLAUDE.md`, `LLMmind/.claude/TODO/LLMmind_project.md`.
