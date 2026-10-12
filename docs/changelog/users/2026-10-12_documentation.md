# 2026-10-12 — changes for users

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../../AI_USAGE.md).*

Changes made on this day, in order:

- Documentation corrected where it did not match the code (documentation)
- More documentation corrections after a second check (documentation)

---

## 09:51 — Documentation corrected where it did not match the code

Kind: documentation

The documentation was checked against the code, and a few statements were wrong or incomplete.
Nothing in the pipeline or its results changed, and nothing has to be rerun.

- **Chunk length.** If you set `max_chunk_length` to `null`, Gemma 3 270M, Gemma 3 1B and both
  Gemma 3n models would read texts in chunks of 32,768 tokens, not 2,048 as the
  [guide](../../guides/running_and_troubleshooting.md#3-settings-that-change-many-results) and
  the comment in `config.yaml` said. The default setting (2,048 for every model) is unaffected.
- **Where the model-level p-values are.** They are only in the summary tables
  (`results/all_model_brain_alignment_scores.tsv` and `results/all_model_model_alignment_scores.tsv`),
  not in the per-model files of `results/alignment_scores/`. The README now says so.
- **First run needs one more download.** The README now lists the brain atlas for the Narratives
  dataset, which is downloaded from TemplateFlow on the first run.
- **Black diamonds in the concept-level plots.** A diamond marks a box that is drawn partly or
  wholly flat because its median equals one of its quartiles. It does not mean the values have no
  spread; this is common with 5 neighbours. It also appears in the enrichment plot. See
  [`statistics.md`](../../reference/statistics.md), section 7.
- **Smaller corrections.** The Caption Scene registration takes about 3 minutes per subject;
  Nature Stories always uses every subject, whatever `minimum_subjects_per_stimulus` says; the
  run-duration page lists the three new similarity-comparison plots; and the troubleshooting
  guide now activates a job's environment with your own conda installation.

---

## 10:05 — More documentation corrections after a second check

Kind: documentation

A second check found three more places where the documentation did not describe what the
pipeline does. Again, nothing in the pipeline or its results changed.

- **Changing `similarity_types` is cheap.** The guide said that adding a similarity measure
  recomputes the nearest neighbours of every measure. It does not: they are always computed for
  all three measures, so the setting only decides which analyses and plots are made. Adding a
  measure back runs only its own analyses.
- **Not every step has its own software environment.** A few small steps (writing lists and
  tables, downloading the MNI template, copying the Narratives transcripts) run in the main
  environment. The [guide](../../guides/running_and_troubleshooting.md#4-software-environments)
  lists them.
- **Caption Scene trials without an image**, and scans whose file cannot be read, are left out.
  [`fmri_preprocessing.md`](../../reference/fmri_preprocessing.md) now says so.
