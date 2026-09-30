# 2026-09-30 — More precise p-value files, a cleaner ISC manifest, and a page on model embeddings

- **Very small p-values are no longer rounded away.** The per-concept p-value files
  (`results/alignment_scores/*.p_value.tsv`) and the Spearman tables
  (`results/spearman_alignment_scores/*.p_value.tsv`) now keep 6 *significant* digits instead of
  6 decimals. Before, a p-value smaller than 0.0000005 would have been written as `0.000000`,
  and small values lost most of their digits. Very small values now appear in scientific
  notation, such as `3.12e-06`. Spreadsheet programs and `pandas` read this format directly.
- **`isc_inputs.tsv` no longer has an unnamed first column.** The file
  `results/mind/<dataset>/manifests/isc_inputs.tsv` now has just the columns `dataset`, `task`
  and `isc_file`.
- **New page: [`docs/reference/model_embeddings.md`](../../reference/model_embeddings.md).**
  It explains, for the methods section, how each model turns a stimulus into one vector: how long
  texts are split into chunks, that the average over tokens includes the start-of-text (BOS)
  token, and which token vision models use.

Nothing is recomputed automatically. The existing files keep their old format until the
pipeline regenerates them, planned for the next full rerun. The numbers are the same, only
written with more digits. Summary statistics computed from them may change in their last digits.

---

*This entry was written by an AI coding assistant.*

- *Tool: Claude Code (Anthropic), VS Code extension.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Date: 2026-09-30.*
- *Basis: a project review requested by the developer, who approved these changes.*
- *Review status: not yet reviewed by the developer at the time of writing.*

*The developer changelog entry of the same name has the technical details.*
