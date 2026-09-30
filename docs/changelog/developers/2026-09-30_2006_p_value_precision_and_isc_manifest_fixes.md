# 2026-09-30 — P-value TSV precision, ISC manifest index, model-embeddings reference page

## Changes

- **P-value TSVs keep 6 significant digits instead of 6 decimals.** `float_format` changed from
  `"%.6f"` to `"%.6g"` in:
  - `workflow/llm_mind_alignment/scripts/compute_empirical_p_value.py` (LLM-brain and LLM-LLM
    empirical p-value files);
  - `workflow/llm_mind_alignment/scripts/compute_hypergeometric_p_value.py` (LLM-brain and
    LLM-LLM hypergeometric p-value files);
  - `workflow/spearman_alignment/scripts/compute_spearman_alignment_with_empirical_p_value.py`
    (model- and concept-level Spearman TSVs).

  With `%.6f`, a hypergeometric p-value below 5e-7 was written as `0.000000`, and values below
  0.001 kept only 1–3 significant digits. As of 2026-09-30, no stored value was 0 (the smallest
  was 3e-6), but 630 hypergeometric p-values were below 0.001. With `%.6g`, small values are
  written in scientific notation (e.g. `3.12e-06`), which `pandas.read_csv` parses unchanged.
  Every float column of these files is affected. Values ≥ 0.1 are written with the same digits
  as before (e.g. `0.708333`, `0.333333`); values in [0.001, 0.1) gain up to two digits; and
  trailing zeros are dropped (`0.04` instead of `0.040000`).
- **`workflow/isc_nearest_neighbours/scripts/create_isc_manifest.py`** writes
  `results/mind/{dataset}/manifests/isc_inputs.tsv` with `index = False`. The unnamed leading
  index column is gone. Its only reader, `isc_npys_from_manifest()` in
  `workflow/isc_nearest_neighbours/Snakefile`, reads the `isc_file` column by name.
- **`workflow/isc_nearest_neighbours/scripts/create_isc_dataframe.py`**: `load_isc_value()`
  calls `np.load()` without `allow_pickle=True`. The ISC files are plain float arrays, so
  pickle loading was never needed.
- **New reference page `docs/reference/model_embeddings.md`**: how `get_embeddings.py` builds
  each stimulus vector, including that the mean pooling of language models includes the BOS
  token that is prepended to every chunk, and that vision models use the CLS token after the
  final norm, without the CLIP projection or classification heads. Linked from `README.md`
  ("Documentation").

## Effect on reruns

No shell command changed, so Snakemake reruns nothing by itself. Existing files keep their old
format until they are regenerated: the p-value files at the next full recomputation (TODO S22),
and `isc_inputs.tsv` when the checkpoint `create_isc_manifest` next runs. Tested on
Nature Stories, with outputs written to a scratch directory:

- both p-value scripts give the same values as before, in the new format;
- the ISC dataframe is identical to the existing one;
- the manifest has the columns `dataset`, `task`, `isc_file` and no index.

Once the p-value files are regenerated, the summary statistics that
`libraries/aggregate_alignment_scores.py` reads from them can change in their last digits
(`observed_average_*`, `empirical_null_mean_*` and the `*_p_value_across_concepts`
statistics), because they are then computed from more precise values.

---

*This entry and the corresponding edits were written by an AI coding assistant.*

- *Tool: Claude Code (Anthropic), VS Code extension.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Date: 2026-09-30.*
- *Basis: a project review requested by the developer; the developer approved these fixes
  (review items 1 and 4) and asked for the embeddings page (item 2).*
- *Review status: not yet reviewed by the developer at the time of writing.*
