# 2026-09-28 — Spearman as a third similarity type

## What changed

- **Spearman is now a similarity type**, next to cosine and Pearson. Two
  stimuli are similar under Spearman when their values rank their
  dimensions in the same order (parcels for the brain, embedding
  dimensions for the models). The actual size of the values doesn't
  matter.
- Every analysis that ran for cosine and Pearson now also runs for
  Spearman: nearest neighbours, brain-model alignment, model-model
  alignment, enrichment, the Spearman alignment and all plots.
- The new files follow the existing names, with `spearman` where `cosine`
  or `pearson` used to be, for example
  `results/mind/<dataset>/isc_spearman_nearest_neighbours.parquet` and
  `results/<stimuli_type>_models/<dataset>/spearman_nearest_neighbours/`.
- Tied values share their average rank. In the brain data this mostly
  concerns parcels whose ISC was set to 0 because it couldn't be computed.

## What this means for you

- **Watch out for the Spearman alignment with Spearman similarity.** The
  existing Spearman alignment (`spearman_alignment_scores/`,
  `spearman_alignment_lineplots/`) also runs for the new similarity type.
  Its `…spearman-spearman_alignment…` files use Spearman twice: first to
  compare stimuli, then to compare the brain and model similarity
  structures.
- **The next run also redoes the cosine and Pearson analyses.** One step
  computes the neighbours for all three similarity types. Because it now
  has a new output, it rewrites the cosine and Pearson files too, and
  everything that depends on them runs again. The numbers won't change,
  but the run is long: about 11,900 jobs, of which about 4,000 are new
  Spearman work.
- To avoid the reruns that were already waiting for other reasons (for
  example the model embeddings), use:

  ```bash
  snakemake --use-conda --cores <N> --rerun-triggers mtime
  ```

- **To skip Spearman**, either for good or for one run: remove
  `- "spearman"` from `similarity_types` in `config/config.yaml`, or leave
  the file as it is and run

  ```bash
  snakemake --use-conda --cores <N> --config 'similarity_types=["cosine","pearson"]'
  ```

  Nothing is recomputed that way.

---
*AI disclosure: this note was written by an AI coding assistant.*

- *Tool: Claude Code (Anthropic), VS Code extension.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Date: 2026-09-28.*
- *Basis: the developer's instructions in the same session.*
- *Checked: the Spearman numbers were compared against a standard
  statistics library, and Snakemake was test-run without doing any real
  work. No real Spearman results exist yet.*
- *Review status: not yet reviewed by the developer at the time of writing.*

*The developer changelog entry of the same name lists exactly what was
changed and tested.*
