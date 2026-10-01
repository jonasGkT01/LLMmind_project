# 2026-10-01 — LLM-LLM aggregation passes its arguments through a file

## Problem

`aggregate_all_llm_llm_p_value_outputs` (`workflow/llm_llm_alignment/Snakefile`) put every input
path on the `python3` command line: 11,184 empirical and 11,184 hypergeometric p-value TSVs,
4,038 relabelled all-k parquets and the 38 `--model_order` keys, about 4.0 MB in total. The kernel
limit on the arguments plus environment of one `execve` (`getconf ARG_MAX`) is 2,097,152 bytes on
both frontend and node5. `bash` therefore failed with `E2BIG` ("Argument list too long") and exited
with status 126 before Python started. Snakemake reported only `CalledProcessError ... exit status
126` with `message: None` (run `.snakemake/log/2026-10-01T092014.485984.snakemake.log`). The
argument list grows with the square of the number of models.

## Changes

- `workflow/llm_llm_alignment/scripts/aggregate_all_llm_llm_p_value_outputs.py`, `main()`:
  `argparse.ArgumentParser(...)` gains `fromfile_prefix_chars = "@"`. An argument `@file` expands
  to the lines of `file`, one argument per line (argparse's default
  `convert_arg_line_to_args`). The arguments, their parsing and the output are unchanged; the
  script can still be called with the arguments on the command line.
- Rule `aggregate_all_llm_llm_p_value_outputs`, shell block: the same arguments are written one per
  line to `args_file=$(mktemp)` with the `printf '%s\n'` builtin (a builtin makes no `execve`, so
  `ARG_MAX` does not apply), then the script is run as `python3 ... @"$args_file"` and the file is
  removed. `mktemp` uses `$TMPDIR`, which Snakemake sets from `resources.tmpdir`. If the script
  fails, the ~4 MB file stays in `$TMPDIR`. Inputs, outputs and params are unchanged.

Not changed: `plot_alignment_heatmap` (~703 LLM-LLM paths per heatmap, ~100 KB) and
`plot_empirical_p_value_heatmap` (two TSVs) are far below the limit. Alternatives considered and
rejected: Snakemake's `script:` directive (breaks the standalone-`argparse`-CLI convention) and
globbing the inputs inside the script (would read files Snakemake did not declare).

## Rerun impact

The shell command changed, so Snakemake's code trigger reruns only this rule. Its output,
`results/all_model_model_alignment_scores.tsv`, did not exist yet. A dry run
(`snakemake -n --sdm conda --cores 1 -- results/all_model_model_alignment_scores.tsv`) plans exactly
one job. No numerical result changes.

## Verification

The rendered `printf` command from the dry run wrote a 26,450-line, 4.0 MB argument file. The
script's own parser read it back as 11,184 + 11,184 + 4,038 paths (all existing), 38 model keys
and the output path. The full rule has not yet been run at the time of writing.

---

*This entry and the corresponding edits were written by an AI coding assistant.*

- *Tool: Claude Code (Anthropic), VS Code extension.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Date: 2026-10-01.*
- *Basis: the developer asked why the project crashed; the fix is TODO entry S33, approved by the
  developer on 2026-10-01 and then removed from the TODO file as solved.*
- *Files changed: `workflow/llm_llm_alignment/Snakefile`,
  `workflow/llm_llm_alignment/scripts/aggregate_all_llm_llm_p_value_outputs.py`.*
- *Review status: not yet reviewed by the developer at the time of writing.*
