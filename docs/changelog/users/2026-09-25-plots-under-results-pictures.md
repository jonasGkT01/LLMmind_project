# 2026-09-25 — All plots are now in `results/pictures/`

## What changed

- **One place for every picture.** All plots and heatmaps are now saved
  inside `results/pictures/`, not directly in `results/`.
- **Same subfolders as before.** Each kind of plot keeps its own subfolder,
  for example `results/pictures/alignment_heatmaps/` or
  `results/pictures/concept_alignment_enrichment_scatterplots/`. File names
  haven't changed.
- **Existing plots were moved, not redrawn.** In this copy of the project the
  old folders are already inside `results/pictures/`.
- The other results (score tables, embeddings, brain data) stay where they
  were.

## What this means for you

- **Look for plots in `results/pictures/`** from now on. Update any
  shortcuts, scripts or slides that point to the old folders.
- **If you have your own copy of the project with plots already made,** move
  the old folders once so the plots don't all get drawn again:

  ```bash
  mkdir -p results/pictures
  for d in alignment_heatmaps alignment_p_value_heatmaps alignment_lineplots \
           concept_alignment_scatterplots alignment_enrichment_lineplots \
           concept_alignment_enrichment_scatterplots spearman_alignment_lineplots \
           concept_spearman_alignment_scatterplots; do
      [ -d "results/$d" ] && mv "results/$d" results/pictures/
  done
  ```

  If you skip this, nothing breaks. The pipeline simply draws the plots again
  in the new place, and the old folders stay behind until you delete them.

---
*AI disclosure: this note was written by an AI coding assistant.*

- *Tool: Claude Code (Anthropic), VS Code extension.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Date: 2026-09-25.*
- *Basis: the change made in the same session at the developer's request.*
- *Review status: not yet reviewed by the developer at the time of writing.*

*The developer changelog entry of the same name has the technical details.*
