# 2026-10-12 — developer changelog

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../../AI_USAGE.md).*

Changes made on this day, in order:

- Living documentation corrected after a check against the code (documentation)
- Second check: rules without their own environment, `similarity_types` reruns, Caption Scene selection (documentation)

---

## 09:51 — Living documentation corrected after a check against the code

Kind: documentation

The README, the guide and the five reference pages were checked claim by claim against the code,
`config/config.yaml`, the `config.json`/`tokenizer_config.json` of the 38 downloaded models and
the current outputs under `results/mind/`. Corrections:

- **Chunk length with `max_chunk_length: null`** (`docs/guides/running_and_troubleshooting.md`,
  section 3; comment above `max_chunk_length` in `config/config.yaml`). Both said Gemma 3/3n/4
  fall back to 2048. `get_safe_max_length()` (`get_embeddings.py`) keeps every candidate below
  100,000 among `tokenizer.model_max_length`, `config.max_position_embeddings` and
  `config.text_config.max_position_embeddings`. `gemma3_270m`/`gemma3_1b` declare 32768 and
  `gemma3n_e2b`/`gemma3n_e4b` 32768 in `text_config`, so they would get 32768. Gemma 3 4B/12B/27B
  (default 131072) and Gemma 4 (131072 or 262144) fall back to 2048, and so does BLOOM (no
  value). The table now names `text_config` too. Only a comment changed in the config; with
  the current value of 2048 nothing reruns.
- **Model-level p-value location** (`README.md`, Outputs): `results/alignment_scores/` holds only
  per-concept p-values; `model_level_empirical_p_value` is computed in
  `libraries/aggregate_alignment_scores.py` and written only to the summary TSVs.
- **Atlas downloads** (`README.md`, Input data): added the MNI152NLin2009cAsym Schaefer atlas
  that `extract_narratives_parcels.py` downloads from TemplateFlow since 2026-10-09.
- **Degenerate-box marker** (`docs/reference/statistics.md`, section 7):
  `mark_degenerate_boxplot_statistics()` fires when Q1 ≈ Q3 or the median ≈ Q1 or Q3, in all
  three concept-level plots (`plot_concept_distributions()`), not only for boxes with no spread in
  the alignment and Spearman plots.
- **Register time** (guide, section 1): `register_caption_scene_t1w` about 3 min per subject
  (median 3.2 min in `clean_run_duration.md`), not about 2 min.
- **Nature Stories and `minimum_subjects_per_stimulus`** (`docs/reference/fmri_preprocessing.md`,
  step 1): `write_nature_stories_parcel_manifest()` writes every subject × story, so the setting
  does not apply; the page now says so, as the guide and README did.
- **Similarity-comparison plots** (`docs/reference/clean_run_duration.md`, section 2e): rows for
  the three rules added on 2026-10-09 (8 + 8 + 4 jobs), with guessed durations.
- **Debugging a failed job** (guide, section 6): activate with
  `source "$(conda info --base)/bin/activate"`, as `.envrc` does, instead of
  `/opt/conda/miniconda3/bin/activate`; the rule environments are built by the user's conda
  (`~/miniforge3`).
- **Headings**: `## 8. Changes` (`statistics.md`) and `## 5. Changes`
  (`clean_run_duration.md`) became `## Changes`, as in the other living documents. No links
  pointed to the old anchors.

Each living document records its change in its `## Changes` section.

### Context

- Request: check the documentation for errors and for disagreements with the code, then fix what
  was found.
- Files changed: `README.md`, `config/config.yaml` (comment only),
  `docs/guides/running_and_troubleshooting.md`, `docs/reference/statistics.md`,
  `docs/reference/fmri_preprocessing.md`, `docs/reference/clean_run_duration.md`,
  `docs/AI_USAGE.md`.
- Verification: model context lengths read from `resources/models/*/config.json` and
  `tokenizer_config.json`; job counts recomputed from `workflow/Snakefile` pairings; stimulus
  counts from `results/mind/*/manifests/isc_inputs.tsv`; the smallest Narratives story (`lucy`,
  14 subjects) from `results/mind/narratives/manifests/isc_manifest.tsv`. The `AI_USAGE.md` table
  was compared with every file header: no missing or outdated row.

---

## 10:05 — Second check: rules without their own environment, `similarity_types` reruns, Caption Scene selection

Kind: documentation

A second pass over the same pages found three more statements that did not match the code:

- **Rules without a `conda:` environment** (`README.md`, Setup;
  `docs/guides/running_and_troubleshooting.md`, section 4). Both said every rule declares one.
  Fifteen rules do not and run in the base environment: the nine `run:` rules
  (`write_{narratives,nature_stories,nsd}_{parcel,isc}_manifest`,
  `write_narratives_problematic_stimuli`, `write_nature_stories_excluded_stimuli`,
  `verify_nature_stories_stimuli`), `fetch_mni_template` (`curl`),
  `rename_narratives_stimuli_transcipts` (`cp`) and the flag rules `mark_narratives_isc_done`,
  `mark_nature_stories_isc_done`, `finish_caption_scene_isc` and `extract_caption_scene_parcels`.
  The guide lists them; the README says it in one line and links there.
- **`similarity_types` and reruns** (guide, section 3). It said adding a metric reruns
  `compute_llm_nearest_neighbours` and `compute_isc_nearest_neighbours` and rewrites every
  metric's files (and quoted about 11,900 jobs for adding `spearman`). Both rules have three fixed
  outputs (cosine, Pearson, Spearman) and no param that depends on `similarity_types`, and the
  startup check in `workflow/Snakefile` accepts only those three values, so changing the list
  never reruns them; it only adds or drops the downstream jobs of that metric (`PAIRINGS`,
  `LLM_LLM_PAIRINGS`, `SPEARMAN_PAIRINGS`, plots). The job count was removed.
- **Caption Scene selection** (`docs/reference/fmri_preprocessing.md`, step 1).
  `make_caption_scene_manifest.py` also drops events whose `Image` is empty or `none`, and skips
  runs whose BOLD file fails `is_valid_nifti()` (count printed as "Skipped N unreadable or
  corrupted BOLD files").
- **README wording** (Input data): the 09:51 addition of the Narratives atlas had left
  "respectively" pairing three items with four download sources; the sentence now names each
  source with what it downloads. Found in a final check, which also verified every relative link
  and anchor of the README, guides, reference pages and changelogs (one old link,
  `README.md#code-conventions` in the 2026-09-23 developer changelog, points to a section that no
  longer exists; left as it is, since changelogs record past states).

### Context

- Request: check the documentation once more, then fix everything found; then a last check.
- Files changed: `README.md`, `docs/guides/running_and_troubleshooting.md`,
  `docs/reference/fmri_preprocessing.md`, `docs/AI_USAGE.md`.
- Verification: rules without `conda:` listed by parsing every Snakefile; the fixed outputs of the
  two neighbour rules read from their Snakefiles and scripts; the event filter read from
  `make_caption_scene_manifest.py`. Also checked on this pass, with no change needed: the input
  paths of the README, the error messages quoted in the guide, the base environment's pandas
  2.3.3 and snakemake 9.27.0, the statistic names of `results/all_model_brain_alignment_scores.tsv`,
  the Narratives task groups and transcript renaming, the TextGrid cleaning, the NSD 1 mm MNI
  mapping and the Nature Stories mapper handling.
