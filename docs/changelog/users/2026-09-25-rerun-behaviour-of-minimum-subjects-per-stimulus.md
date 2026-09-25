# 2026-09-25 — What happens when you change `minimum_subjects_per_stimulus`

## What changed

Nothing in how the pipeline works. This note explains what to expect when
you change the `minimum_subjects_per_stimulus` setting in
`config/config.yaml`.

## What this means for you

- **You don't need to delete anything.** Change the value and run
  Snakemake again. It rebuilds every result that depends on the setting.
- **Expect a long run.** For Caption Scene and NSD, both the brain data and
  the model embeddings are recomputed, and the embeddings use the GPU.
  Changing the value from 2 to 3 adds roughly 6,000 jobs.
- **Narratives and Nature Stories are usually not affected.** Nature Stories
  doesn't use this setting. In Narratives every story was heard by at least
  14 subjects, so nothing changes until you set 15 or more.
- **Use a value from 2 to 8.** Below 2 there is nothing to compare between
  subjects, and the pipeline stops with an error. Caption Scene and NSD have
  8 subjects each, so above 8 no stimulus would be left.
- **Preview first.** This command shows what would run for a given value,
  without changing the config file or running anything:

  ```bash
  snakemake -n --cores 8 --rerun-triggers mtime params input code \
      --config minimum_subjects_per_stimulus=3 --quiet rules
  ```

- **One known issue (Narratives, values of 15 or more only).** If you raise
  the value and later lower it again, the Narratives step may stop with a
  "missing output" error. Add `--forcerun write_narratives_parcel_manifest`
  to your command to fix it.

---
*AI disclosure: this note was written by an AI coding assistant.*

- *Tool: Claude Code (Anthropic), VS Code extension.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Date: 2026-09-25.*
- *Basis: the developer's question in the same session, answered by reading
  the workflow code and running dry runs.*
- *Review status: not yet reviewed by the developer at the time of writing.*

*The developer changelog entry of the same name lists exactly what was
checked.*
