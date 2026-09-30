# 2026-09-30 — The brain-model summary table has a new name

- `results/all_alignment_scores.tsv` is now called
  **`results/all_model_brain_alignment_scores.tsv`**, so it pairs with
  `results/all_model_model_alignment_scores.tsv`.
- Its content is exactly the same. The existing file was renamed, not recomputed.
- If you load the table in your own scripts, or ask Snakemake for it by name, use the new
  name:

  ```bash
  snakemake --use-conda --cores <N> results/all_model_brain_alignment_scores.tsv
  ```

---

*This entry was written by an AI coding assistant.*

- *Tool: Claude Code (Anthropic), VS Code extension.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Date: 2026-09-30.*
- *Basis: the rename the developer asked for in the same session.*
- *Review status: not yet reviewed by the developer at the time of writing.*

*The developer changelog entry of the same name has the technical details.*
