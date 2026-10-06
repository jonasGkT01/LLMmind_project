# 2026-10-06 — changes for users

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../../AI_USAGE.md).*

Changes made on this day, in order:

- No step reserves several cores any more (bugfix)
- README: input files not produced by the download (documentation)
- Documentation reorganised (documentation)

---

## 10:30 — No step reserves several cores any more

Kind: `bugfix`

The run of 5 October stopped making progress overnight. Three small jobs had finished their work
but never closed, so they kept 3 of the 4 cores busy. The next step, the NSD parcel extraction,
asked for all 4 cores at once, so it waited forever.

Now no step asks Snakemake for more than one core. The few steps that work in parallel internally
(NSD parcel extraction, Caption Scene T1w registration and the two final summary tables) take
their number of workers from a new setting in `config/config.yaml`:

```yaml
number_of_workers: 4
```

What to know:

- Launch the pipeline as usual, e.g. `snakemake --use-conda --cores 4 --resources gpu=1`.
- While one of these steps runs next to other jobs, the run can briefly use more CPUs than
  `--cores`. Lower `number_of_workers` if that is a problem.
- The Caption Scene registration now uses 4 threads instead of 8.
- This change adds no extra work to the run in progress: relaunching it still has the same 4,195
  jobs left to do.

### Context

- Request: Written after the developer asked why the run had stalled since 01:00 and then asked to remove every rule's core specification.
- Files changed: `config/config.yaml`, the NSD, Caption Scene, LLM-brain and LLM-LLM Snakefiles, `README.md`, `docs/reference/clean_run_duration.md`.

---

## README: input files not produced by the download

Kind: `documentation`

The README now lists the input files you have to extract, copy or correct by hand, because the
`public_datasets` download does not produce them: the Caption Scene run tables (unpack `CSD.rar`),
the Narratives `scan_exclude.json`, and a corrected `new_run_onsets.json` for Nature Stories.

---

## 16:30 — Documentation reorganised

Kind: `documentation`

The documentation was reorganised so that each piece of information lives in one place:

- **`README.md`** is now a short overview: what the pipeline does, where the documentation is
  (a list near the top), how to set it up and run it, and what it produces.
- **`docs/guides/running_and_troubleshooting.md`** is new. It has everything about running: partial
  runs, when Snakemake reruns a step by itself and when you must force it, the settings that
  rebuild many results, the software environments, which models are not supported, and the fixes
  for common failures. One fix was out of date: the manifest steps *do* rerun on their own when
  their code changes (since 5 October); the guide now lists exactly which steps do and which
  don't.
- **The reference pages** (fMRI processing, model embeddings, statistics, run duration) no longer
  mention internal TODO numbers, and notes about how things used to be are now in a "Changes"
  section at the end of each page. The plot conventions (colours, model order, axes) moved from
  the README to the statistics page.
- **Changelogs** are now one file per day, for developers and for users. The file name gives the
  date and the kinds of change made that day, for example
  `2026-10-06_bugfix_documentation.md`. The old entries were merged into these files; their text
  is unchanged.
- **AI attribution** is now in one place, `docs/AI_USAGE.md`: how AI assistants were used, and a
  table with the date and model of the latest AI edit of every file. The other documents only
  keep a one-line note under their title.

Nothing in the pipeline or its results changed.
