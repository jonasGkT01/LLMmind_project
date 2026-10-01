# 2026-10-01 — Fixed: the model-model summary table step crashed

## What happened

The step that combines all model-model results into
`results/all_model_model_alignment_scores.tsv` crashed with "exit status 126" and no other message.
It handed the program the names of more than 26,000 files at once. That list (about 4 MB) is
longer than Linux lets any program receive when it starts (2 MB), so the program never started.
Your data and results were not affected.

## What changed

The step now writes the list of files into a temporary file and gives the program that file
instead. The results are exactly the same, and nothing else has to be recomputed.

## What to do

Restart the pipeline as usual on node5. Only this one step runs, and it creates
`results/all_model_model_alignment_scores.tsv` and then the plots that need it.

---

*Written by an AI coding assistant: Claude Code (Anthropic), VS Code extension, model Claude Opus
5.5 (`claude-opus-5-5`), 2026-10-01, after the developer asked why the project crashed. Files
changed: `workflow/llm_llm_alignment/Snakefile`,
`workflow/llm_llm_alignment/scripts/aggregate_all_llm_llm_p_value_outputs.py`. Not yet reviewed by
the developer at the time of writing.*

*The developer changelog entry of the same name has the technical details.*
