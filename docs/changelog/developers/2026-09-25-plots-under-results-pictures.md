# 2026-09-25 — All plot outputs moved under `results/pictures/`

## Summary

The 8 plot and heatmap output directories moved from `results/<dir>/` to
`results/pictures/<dir>/`. Subfolder names and filenames are unchanged. The
existing PNGs were moved with `mv`, not regenerated.

## Changes

| Old | New |
|---|---|
| `results/alignment_heatmaps/` | `results/pictures/alignment_heatmaps/` |
| `results/alignment_p_value_heatmaps/` | `results/pictures/alignment_p_value_heatmaps/` |
| `results/alignment_lineplots/` | `results/pictures/alignment_lineplots/` |
| `results/concept_alignment_scatterplots/` | `results/pictures/concept_alignment_scatterplots/` |
| `results/alignment_enrichment_lineplots/` | `results/pictures/alignment_enrichment_lineplots/` |
| `results/concept_alignment_enrichment_scatterplots/` | `results/pictures/concept_alignment_enrichment_scatterplots/` |
| `results/spearman_alignment_lineplots/` | `results/pictures/spearman_alignment_lineplots/` |
| `results/concept_spearman_alignment_scatterplots/` | `results/pictures/concept_spearman_alignment_scatterplots/` |

- `workflow/visualisation/Snakefile`: 16 paths. These are the 8 in the
  module's own target list and the `output:` of `plot_alignment_heatmap`,
  `plot_empirical_p_value_heatmap`, `plot_concept_alignment_scatterplot`,
  `plot_brain_model_alignment_lineplot`,
  `plot_concept_alignment_enrichment_scatterplot`,
  `plot_brain_model_alignment_enrichment_lineplot` and
  `plot_spearman_alignment` (2 outputs).
- `workflow/Snakefile`: the 8 plot paths in `rule all`.
- No script changes. Every plotting script already calls
  `Path(...).parent.mkdir(parents=True, exist_ok=True)`.
- **Not moved:**
  - NSD stimulus PNGs from `export_nsd_stimuli.py`. They are pipeline inputs,
    not plots.
  - The separate `pca_plot` project.

## Snakemake state

- `snakemake -n --rerun-triggers mtime`: "Nothing to be done". `mv` keeps
  mtimes, so the moved files are accepted as up to date.
- `.snakemake/metadata` is keyed by output path. The moved PNGs therefore have
  no provenance record, which Snakemake reports as "missing
  provenance/metadata" for the plot rules. Until each plot is rebuilt once,
  the `code`/`params`/`software-env` triggers can't fire for them. This
  doesn't matter much here: plot-script edits never fired those triggers
  anyway (see the README's `--forcerun` note).
- A dry run with the default triggers schedules 8,141 jobs. The move is not
  the cause. The causes already existed: changed conda environment
  definitions, and the uncommitted LLM–LLM pairing change in
  `workflow/Snakefile`. The plot jobs appear only as downstream "input files
  updated by another job".

## Migration for other checkouts

A checkout that already has the old directories should move them once to
avoid redrawing every plot:

```bash
mkdir -p results/pictures
for d in alignment_heatmaps alignment_p_value_heatmaps alignment_lineplots \
         concept_alignment_scatterplots alignment_enrichment_lineplots \
         concept_alignment_enrichment_scatterplots spearman_alignment_lineplots \
         concept_spearman_alignment_scatterplots; do
    [ -d "results/$d" ] && mv "results/$d" results/pictures/
done
```

Without this, Snakemake draws the plots again at the new paths and leaves the
old directories in place.

## Commit note

The `rule all` edits in `workflow/Snakefile` sit next to uncommitted work by
someone else (LLM–LLM self-pairs across stimuli types). Stage the hunks
separately (`git add -p workflow/Snakefile`) if the two are meant to go into
different commits.

---
*AI disclosure: the code change, the directory move, this changelog entry and
the related README edit were made by an AI coding assistant, at the
developer's request.*

- *Tool: Claude Code (Anthropic), VS Code extension; Snakemake 9.21.0.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Date: 2026-09-25.*
- *Decision made by the assistant: placing `pictures/` under `results/` rather
  than at the project root. The request only named the directory.*
- *Verification: grep for leftover old paths in Snakefiles and scripts (none),
  and the two dry runs above. No real run after the move.*
- *Review status: not yet reviewed by the developer at the time of writing.
  The change is uncommitted.*
