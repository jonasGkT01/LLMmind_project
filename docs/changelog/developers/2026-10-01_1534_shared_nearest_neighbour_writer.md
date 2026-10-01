# 2026-10-01 — One shared writer for the LLM and ISC nearest-neighbour files

## Change

`compute_llm_nearest_neighbours.py` and `compute_isc_nearest_neighbours.py` repeated the same three
blocks (cosine, Pearson, Spearman: `compute_blockwise_topk_from_embeddings()` then
`write_nearest_neighbours_parquet()`). They differed only in the loader and the argument names.

- `workflow/libraries/compute_nearest_neighbours.py` gains
  `write_all_nearest_neighbours(embedding_matrix, concepts, number_of_neighbours, output_path_by_similarity_type)`.
  For each similarity type in the dict it looks up the normaliser with
  `compute_similarity.normalize_fn_for_similarity_type()` (which rejects unknown types), computes
  the top-k and writes the Parquet, freeing the arrays before the next type, as before. The library
  now imports `normalize_fn_for_similarity_type` from `libraries.compute_similarity`.
- The two scripts keep their argument parsing and their own loader (`extract_embedding_matrix` /
  `dataframe_to_embedding_matrix`) and make one call with `{"cosine": …, "pearson": …, "spearman": …}`.
  The loaders are not merged.
- Command-line arguments and Snakefile rules are unchanged, so nothing reruns.
- `compute_blockwise_topk_from_embeddings()` docstring: the reference to "the *_from_parquet readers
  above", which no longer exist, is removed (TODO S20 item 1).

Adding a similarity type now needs only an entry in
`compute_similarity.NORMALIZE_FUNCTIONS_BY_SIMILARITY_TYPE`, a new argument in each script and the
rule outputs.

## Verification

The original (`d3db409`) and new scripts were run on the Narratives `bloom_1b1` embeddings (k = 5)
and on the Narratives (k = 5) and NSD (k = 100) ISC dataframes. All nine Parquet outputs were
byte-identical (`cmp`), and two of them also byte-identical to the files in `results/`.

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-01, Claude Opus 5.5: written for TODO entries S18 and S20 (item 1), approved by the developer on 2026-09-30; implemented on 2026-10-01 after the developer asked which solutions could be done while the S34 check was running ("proceed").*
- *Files changed: `workflow/libraries/compute_nearest_neighbours.py`, `workflow/llm_nearest_neighbours/scripts/compute_llm_nearest_neighbours.py`, `workflow/isc_nearest_neighbours/scripts/compute_isc_nearest_neighbours.py`.*
- *Review status: not yet reviewed by the developer.*
