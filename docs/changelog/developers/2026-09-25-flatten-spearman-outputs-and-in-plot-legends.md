# 2026-09-25 — Flattened Spearman output paths, in-plot legends, no per-concept null SD

## Summary

- The Spearman outputs no longer live under `results/spearman_alignment/`.
  They sit at the top level of `results/`, next to the other alignment
  outputs, with names that follow the kNN alignment files. The 248 existing
  files were moved, not recomputed.
- Every plot that has a legend draws it **inside the axes** (top left). The
  top 25% of the y-range is kept empty for it. Concept names are **never**
  listed; concepts are only colour-coded.
- The model-level significance asterisks moved from above the points (or
  from the top band on concept-level plots) to **two rows just below the
  x-axis**, above each model name.
- The concept-level enrichment and concept-level Spearman plots no longer
  draw a **per-concept null-SD bar**. The model-level error bars are
  unchanged.

## Output paths

`D` = dataset, `M` = model, `S` = stimuli type, `SIM` = similarity type.

| Old | New |
|---|---|
| `results/spearman_alignment/model_level/dataset-D_model-M-S_brain_SIM-similarity_spearman_alignment_empirical.p_value.tsv` | `results/spearman_alignment_scores/dataset-D_model-M-S_brain_empirical_SIM-spearman_alignment_model_level.p_value.tsv` |
| `results/spearman_alignment/concept_level/…` (same basename as above) | `results/spearman_alignment_scores/dataset-D_model-M-S_brain_empirical_SIM-spearman_alignment_concept_level.p_value.tsv` |
| `results/spearman_alignment/model_level_plots/dataset-D_SIM-brain_model_spearman.png` | `results/spearman_alignment_lineplots/dataset-D_SIM-brain_model_spearman_alignment.png` |
| `results/spearman_alignment/concept_level_plots/dataset-D_SIM-concept_spearman_coefficients.png` | `results/concept_spearman_alignment_scatterplots/dataset-D_SIM-concept_spearman_alignment.png` |
| `results/all_spearman_alignment_scores.tsv` | unchanged |

- The TSV names mirror the kNN p-value files
  (`…_brain_empirical_SIM-alignment_score_<k>NN.p_value.tsv`): `empirical`
  moves before the similarity type, the redundant `-similarity_` is
  dropped, and `_model_level` / `_concept_level` take the place of
  `<k>NN`. The level has to be in the filename now, because both levels
  share one directory.
- The plot directories mirror `alignment_lineplots/` and
  `concept_alignment_scatterplots/`, which draw the same kinds of plot.
- Changed: the path strings in `workflow/Snakefile` (`rule all`),
  `workflow/spearman_alignment/Snakefile` (`all_spearman_alignment`,
  `compute_spearman_alignmentwith_empirical_p_value`,
  `aggregate_all_spearman_alignment_scores`) and
  `workflow/visualisation/Snakefile` (`all_visualisation`,
  `plot_spearman_alignment`). Rule names, wildcards and script arguments
  are unchanged. The scripts take their paths as arguments and create
  parent directories themselves.

### Migration of existing outputs

- A one-off Python script moved 232 TSVs and 16 PNGs with `os.rename`, so
  the mtimes were kept. It asserted a regex match on every source name, no
  duplicate targets and no existing targets before moving anything. After
  the move, `results/spearman_alignment/` was removed; it was empty.
- `snakemake -n --cores 1 --rerun-triggers mtime` reports "Nothing to be
  done". The moved files have no Snakemake provenance metadata, which
  shows up as "missing provenance/metadata" for
  `compute_spearman_alignmentwith_empirical_p_value` and
  `plot_spearman_alignment`. That is harmless: those files cannot trigger
  reruns themselves.
- A plain `snakemake -n` (default rerun triggers) wants about 8,100 jobs.
  That comes from issues that were there before this session: changed
  software-env definitions on upstream rules (`download_pretrained_llm`,
  `make_nsd_manifest`, …) and a missing
  `write_nature_stories_excluded_stimuli` output. It is not caused by the
  move.

## Legend inside the axes

In `libraries/visualisation_utils.py`:

- `add_legend` now calls `ax.legend(loc="upper left", fontsize=8,
  framealpha=0.9)`. The previous version placed the legend outside the
  axes (`bbox_to_anchor=(1.01, 1.0)`).
- New `LEGEND_HEADROOM_FRACTION = 0.25` and
  `legend_headroom_top(bottom, data_top)`, which returns
  `bottom + (data_top - bottom)/(1 - LEGEND_HEADROOM_FRACTION)`. Callers use
  it as the upper y-limit, so the data stays in the lower 75% of the axes.
  This was needed because `loc="best"` still put the legend on top of data
  in the dense Caption Scene box-scatterplots (about 1,000 points per model).
- Where it is applied:
  - `plot_brain_model_alignment_lineplot.py` and
    `plot_concept_alignment_scatterplot.py`: `ylim = (0,
    legend_headroom_top(0, 1))`, about 1.33. The ticks are pinned to
    `np.linspace(0, 1, 6)`, so no tick above 1 is shown. The two plots still
    share one y-range.
  - `compute_alignment_enrichment.enrichment_ylim`: the top it computed
    before is passed through `legend_headroom_top`. Both enrichment plots
    still share one y-range. The module now imports
    `libraries.visualisation_utils`, and so matplotlib. Only the two
    enrichment plotting scripts use it.
  - `plot_spearman_alignment.spearman_ylim`: returns `(-limit,
    legend_headroom_top(-limit, limit))`. The range is no longer symmetric.
- Removed `concept_legend_handles`. Every caller now passes only
  `significance_legend_handles()`. `CONCEPT_LEGEND_MAX_CONCEPTS` was
  renamed `DENSE_CONCEPT_THRESHOLD`; it now only switches
  `concept_point_alpha` between 0.85 and 0.30.

## Significance asterisks below the axis

- `annotate_significance(ax, x_positions, p_values, q_values)` replaces
  both the old `annotate_significance(ax, x_positions, y_positions, …)` and
  `annotate_significance_band`. **Its signature changed**: the
  `y_positions` argument is gone.
- It anchors each annotation at `(x, 0)` in `ax.get_xaxis_transform()`,
  with offsets of −5 pt (p-value row, black) and −15 pt (q-value row, red),
  `va="top"` and `annotation_clip=False`.
- It calls `ax.tick_params(axis="x", pad=SIGNIFICANCE_TICK_LABEL_PAD_POINTS)`
  (29 pt) to push the model names below the two rows. The pad is kept in
  `_major_tick_kw`, so it survives the later `set_xticks` /
  `style_model_x_axis` calls that follow `boxplot()`.
- Row order changed: the black p-value row is now **above** the red
  q-value row. Before, red was above black.
- Callers updated: all four kNN brain-model plot scripts and both Spearman
  plots. The heatmaps are untouched.

## No per-concept null SD

- `plot_concept_alignment_enrichment_scatterplot.py`: removed the `vlines`
  call and the `null_standard_deviation` read. The y label is now
  `y_axis_label(ALIGNMENT_ENRICHMENT_LABEL)`, without "± null SD".
- `plot_spearman_alignment.py`, concept-level figure: removed the `vlines`
  call and `concept_errors`. The y-limits come from the coefficients only,
  and the label has no "± null SD".
- `enrichment_ylim` now takes the concept-level maximum from `enrichment`
  alone. The model-level values still include their SD.
- The concept-level `empirical_null_standard_deviation_spearman_coefficient`
  column is still written and still required by
  `plot_spearman_alignment.py`'s input validation, which is shared by both
  levels.

## Rerunning

- The plot scripts run from `shell:` rules, so Snakemake's code trigger
  does not see these changes. To redraw the plots:
  ```bash
  snakemake --use-conda --cores <N> --rerun-triggers mtime \
      --forcerun plot_brain_model_alignment_lineplot plot_concept_alignment_scatterplot \
                 plot_brain_model_alignment_enrichment_lineplot \
                 plot_concept_alignment_enrichment_scatterplot plot_spearman_alignment
  ```
- **Not yet done:** the 80 Spearman TSVs for `narratives` and
  `nature_stories` (40 compute jobs) still predate the null-SD column added
  on 2026-09-24. `plot_spearman_alignment` fails for those two datasets
  until they are rebuilt, which also means the narratives and nature_stories
  Spearman PNGs in `results/` are still the pre-2026-09-24 ones, with no
  concept colours. Add
  `compute_spearman_alignmentwith_empirical_p_value` to `--forcerun`. That
  reruns all 116 compute jobs; to rerun only the stale ones, target their
  files instead.
- At the time of writing, none of the plots in `results/` had been
  regenerated with the new code.

## Verification

- Syntax check of every modified file, plus an AST-based check for unused
  imports. pyflakes is not installed in either env.
- `snakemake -n --cores 1 --rerun-triggers mtime` after the move: nothing
  to do. A `grep` confirmed that no reference to the old paths is left in
  `workflow/`.
- Rendered one plot of each of the six affected types into a scratch
  directory, with the visualisation conda env and the exact commands from
  `snakemake -n -p`: narratives cosine k=5 for the four kNN plots,
  caption_scene cosine for both Spearman plots. Checked by eye: legend
  inside and clear of data, asterisks between axis and model names, no
  concept bars.
- Rendered the narratives concept-level Spearman plot from scratch copies
  of the old-format TSVs with a zero-filled null-SD column, to check the
  concept colours on an 18-concept dataset.
- No automated tests exist for the plots.

## Follow-ups

- With 11–20 concepts (Narratives: 18), `concept_colours` uses tab20, whose
  colours come in dark/light pairs of the same hue. At `s=10` some pairs
  are hard to tell apart. Suggested fix (proposed to the developer, not
  applied): a palette without the paired pastels, and larger markers.
- If `spearman_ylim` hits its cap of 1, the headroom pushes the top to
  about 1.67, and tick labels above 1 are shown. Pin the ticks as in the
  alignment-score plots if that ever happens; on current data the limits
  are about ±0.2 (Caption Scene) and ±0.75 (Narratives).
- This resolves the 2026-09-24 follow-up about the top asterisk band
  overlapping points on the fixed-range concept plots.
- The rule name `compute_spearman_alignmentwith_empirical_p_value`
  (missing underscore) was left as it is, to avoid changing CLI commands
  that are already documented.

---
*AI disclosure: this changelog entry, together with the code changes it
describes, the migration of the existing outputs and the related README
edits, was written by an AI coding assistant.*

- *Tool: Claude Code (Anthropic), VS Code extension, run inside the
  developer's workspace on the lab server.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Date: 2026-09-25.*
- *Basis: explicit instructions from the developer (Jonas Salvalaggio) in
  the same session. The developer asked for the Spearman outputs to sit at
  the top level of `results/` and approved the proposed names before any
  change was made. The developer also asked for legends inside the plot,
  no listed concept names, asterisks near the model names if needed, no
  per-concept relabelling SD, and the same rules for the Spearman plots.
  The assistant chose the legend headroom (25%), the exact asterisk
  placement and row order, keeping the model-level error bars, and
  applying the asterisk move to every brain-model plot.*
- *Verification: limited to the checks listed under "Verification". The
  plots in `results/` were not regenerated.*
- *Review status: not yet reviewed by the developer at the time of writing.
  Review it before committing.*
