# 2026-09-30 — `all_alignment_scores.tsv` renamed to `all_model_brain_alignment_scores.tsv`

## Change

- The brain-model summary table is now `results/all_model_brain_alignment_scores.tsv`, so
  its name pairs with `results/all_model_model_alignment_scores.tsv`. The content and
  format are unchanged.
- `workflow/llm_mind_alignment/scripts/aggregate_all_p_value_outputs.py`: the option
  `--all_alignment_scores_tsv` is now `--all_model_brain_alignment_scores_tsv`, matching
  `--all_model_model_alignment_scores_tsv` in the LLM-LLM script.
- Updated the path in: `workflow/Snakefile` (`rule all`),
  `workflow/llm_mind_alignment/Snakefile` (`all_llm_mind_alignment` and the output
  `all_model_brain_alignment_scores_tsv` of `aggregate_all_p_value_outputs`),
  `workflow/visualisation/Snakefile` (the inputs of the five plot rules that read the
  model-level p-values), and a comment in `workflow/libraries/compute_statistics.py`.
- `README.md`: the example target and "Outputs".
- The existing file was moved with `mv`, so its modification time is unchanged.
  `all_spearman_alignment_scores.tsv` keeps its name.

## Effect on reruns

The aggregation rule's shell command and output path changed, and so did the input path of
the plot rules. Snakemake will therefore rerun `aggregate_all_p_value_outputs` (already due
after S23) and the plot rules that read the table. Both are light and give the same numbers.
Older changelog entries keep the old name, because they describe the state at their date.

---

*This entry and the corresponding edits were written by an AI coding assistant.*

- *Tool: Claude Code (Anthropic), VS Code extension, on the lab server.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Date: 2026-09-30.*
- *Basis: the developer (Jonas Salvalaggio) asked for the rename. They wrote the singular
  `…_alignment_score.tsv`; the plural was used to match
  `all_model_model_alignment_scores.tsv`.*
- *Verification: a search confirmed that no reference to the old name remains outside the
  historical changelog entries. No Snakemake dry run was made, because every dry run
  rewrites the Narratives QC files (TODO P28).*
- *Review status: not yet reviewed by the developer at the time of writing.*

*The user changelog entry of the same name gives a plain-language summary.*
