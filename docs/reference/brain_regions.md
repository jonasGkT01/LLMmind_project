# Brain regions: modality-specific ISC

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../AI_USAGE.md).*

Besides the whole cortex, every brain-model analysis is also run on the region of the model's
own modality: language models on a language region, vision models on a visual region. This
page describes how the regions are defined, how their ISC is taken from the whole-cortex ISC, and
where the results go. It is written from the code (`config/config.yaml`, `atlas: regions:`;
`workflow/isc_nearest_neighbours/scripts/extract_region_isc_dataframe.py`; the Snakefiles).

## 1. Why

Every ISC vector has one value for each of the 200 Schaefer parcels, and on the whole cortex every
model is compared with all of them. Most parcels have nothing to do with the stimulus modality, so
they add noise and could hide an alignment that exists in the cortex of that modality. The region
analysis asks the same questions on the parcels of the matching modality only.

## 2. The regions

Each region is a list of 1-based Schaefer label IDs, in `config/config.yaml` under
`atlas: regions:`, keyed by stimulus type; each ID has its 7-network parcel name as a comment.

| Region | Parcels | Label IDs | Source |
|---|---|---|---|
| `vision` | 29 | 1–14, 101–115 | the `Vis` network of the 7-network Schaefer atlas used by the pipeline |
| `language` | 17 | 15, 16, 44, 70, 77, 78, 85, 87 (left); 116, 117, 119, 149, 153, 163, 181, 189, 190 (right) | the `Language` (8 parcels) and `Aud` (9 parcels) networks of the Kong 2022 17-network version of the Schaefer atlas |

**Language region.** The 7-network and 17-network Yeo labels have no language network. The Kong
2022 version of the Schaefer parcellation (CBIG repository,
`stable_projects/brain_parcellation/Schaefer2018_LocalGlobal/Parcellations/FreeSurfer5.3/fsaverage/label/{lh,rh}.Schaefer2018_200Parcels_Kong2022_17Networks_order.annot`)
has one, `Language`, in the inferior frontal gyrus, the lateral temporal cortex and the lateral
and medial prefrontal cortex. Its `Aud` network (superior temporal cortex, parietal operculum,
insula) is included too, because the Narratives and Nature Stories stimuli are spoken stories. In
our 7-network labels these 17 parcels belong to `SomMot`, `SalVentAttn`, `Cont`, `Default` and
`Limbic`.

**Mapping from Kong to our labels.** The Kong version has the same 200 parcels as ours, with other
network labels and another order. This was checked on 2026-10-14 on fsaverage, with the 7-network
annotation in `resources/atlases/atl-schaefer2018/fsaverage/`: the vertices of every one of our
parcels lie 100% inside one Kong parcel. Each Kong `Language` or `Aud` parcel was matched to our
parcel with the same vertices, once, by hand; the pipeline needs no Kong file. The Kong parcel
name of each language ID is in the comment next to it in the config.

## 3. From the whole-cortex ISC to the region ISC

**What the whole-cortex ISC holds.** `results/mind/{dataset}/isc_dataframe.parquet` has one row
per concept (index `concept`) and one column, `isc`: a float32 vector of 200 values without NaN,
in all four datasets (checked on 2026-10-14). Position `i` of the vector holds Schaefer label
`i + 1`, in the 7-network order (1–100 left hemisphere, 101–200 right), in every dataset:
`build_parcel_matrix()` (`workflow/libraries/fmri_processing.py`, Narratives and NSD) and
`extract_caption_scene_parcels.py` map label `l` to position `l - 1`, and the fsaverage annotation
order used for Nature Stories (`extract_nature_stories_parcels.py`) is the label order of
`resources/atlases/schaefer_2018/Schaefer2018_200Parcels_7Networks_order.txt`. A region is
therefore a fixed set of positions in vectors that already exist.

**The rule.** `extract_region_isc_dataframe` (`workflow/isc_nearest_neighbours/Snakefile`) runs
once per dataset and stimulus type of that dataset:

- input `results/mind/{dataset}/isc_dataframe.parquet`;
- output `results/{stimuli_type}_mind/{dataset}/isc_dataframe.parquet`;
- parcels `config["atlas"]["regions"][stimuli_type]`, chosen by the stimulus type written in the
  output path, so a `language_mind` file can only hold the language parcels.

`language_mind` is written for Narratives, Nature Stories and Caption Scene, `vision_mind` for NSD
and Caption Scene (the stimulus types of `config[dataset]["stimuli_dir"]`).

**The script** (`extract_region_isc_dataframe.py`):

1. reads the whole-cortex dataframe and stacks the `isc` column into a concepts × 200 matrix;
2. stops if the vectors do not have `n_rois` values, or if the region IDs are not unique or not
   between 1 and `n_rois`;
3. keeps the columns `ID - 1` of the region, in increasing label order, and drops all others;
4. writes the result with the layout of the input: same index, same concepts in the same order,
   one column `isc` with vectors of 17 (language) or 29 (vision) float32 values.

The ISC values are copied, not recomputed: a region ISC is exactly a sub-vector of the
whole-cortex ISC. The other parcels are dropped, not set to 0: zeros would leave the cosine
similarity unchanged, but they would enter the mean of the Pearson similarity and the ranks of
the Spearman similarity.

**Brain neighbours.** `compute_isc_nearest_neighbours` reads `results/{mind}/{dataset}/`, with
`mind` one of `mind`, `language_mind`, `vision_mind`, so the same rule and script compute the
neighbours of a region ISC as for the whole cortex, next to it:
`results/{stimuli_type}_mind/{dataset}/isc_{cosine,pearson,spearman}_nearest_neighbours.parquet`.
Its check stops the job on a NaN or constant vector.

## 4. Region results

Every brain-model result of a region is written next to the whole-cortex one, with the stimulus
type appended to the top-level directory, summary-table or plot-folder name; the file names inside
are the same as for the whole cortex.

| Whole cortex | Language region | Visual region |
|---|---|---|
| `results/mind/{dataset}/` | `results/language_mind/{dataset}/` | `results/vision_mind/{dataset}/` |
| `results/alignment_scores/` | `results/alignment_scores_language/` | `results/alignment_scores_vision/` |
| `results/spearman_alignment_scores/` | `results/spearman_alignment_scores_language/` | `results/spearman_alignment_scores_vision/` |
| `results/tsv_summaries/all_model_brain_alignment_scores.tsv` | `..._language.tsv` | `..._vision.tsv` |
| `results/tsv_summaries/all_spearman_alignment_scores.tsv` | `..._language.tsv` | `..._vision.tsv` |
| `results/pictures/<plot folder>/` | `results/pictures/<plot folder>_language/` | `results/pictures/<plot folder>_vision/` |

- A `_language` result holds only the language models and the datasets with language stimuli; a
  `_vision` result only the vision models and the datasets with vision stimuli.
- The region is given only by the directory or table name: inside, the file names and the TSV
  columns are those of the whole cortex. A file copied elsewhere loses its region.
- Model-model results have no region version (they do not involve the brain), and neither have the
  two heatmaps (`alignment_heatmaps/`, `alignment_p_value_heatmaps/`): they take every model of the
  dataset from the model-model results, while a region has brain results for one modality only,
  so on Caption Scene the p-value heatmap would stop in `model_level_significance()`.
- With the current config a region run adds 612 score jobs (360 language, 252 vision), 300
  relabelling and 300 Spearman jobs, as many as the whole cortex has.

**How a model is kept to its own region.** One wildcard, `region_suffix` (`""`, `_language` or
`_vision`, from `REGION_SUFFIXES` in `workflow/Snakefile`), is appended to the result paths.
`mind_dir(wildcards)` gives the brain directory of every brain-model job: `results/mind` for an
empty suffix, `results/{stimuli_type}_mind` when the suffix is the job's own stimulus type, and a
`ValueError` otherwise. The model input and `mind_dir()` read the same `{stimuli_type}` wildcard,
so even a target written by hand cannot compare a vision model with the language region.
`pairings_in()` keeps, for each suffix, the pairings of its stimulus type, and every summary
table and plot is built only from the files with its own suffix.

## 5. Interpretation

- **Fewer dimensions.** Region vectors have 17 or 29 values instead of 200, so the similarities
  between concepts are noisier, especially for the 11–18 concepts of Nature Stories and
  Narratives.
- **Multiple testing.** In a region the Benjamini-Hochberg family of a (dataset, similarity, *k*)
  is the models of one modality: on Caption Scene 24 language or 14 vision models instead of 38
  (see [`statistics.md`](statistics.md), section 5).
- **Region choice.** The visual region is the 7-network `Vis` network, which covers early and
  extrastriate visual cortex; ventral temporal parcels outside it are not included. The language
  region is defined from the Kong 2022 group-level networks, not from a functional localiser.
- **Group atlas and individual language cortex.** The location of language cortex varies across
  individuals much more than that of visual cortex: language regions defined in each subject
  with a localiser are more selective than group-analysis regions on the same data (Fedorenko,
  Hsieh, Nieto-Castañón, Whitfield-Gabrieli & Kanwisher 2010, *J Neurophysiol* 104:1177–1194,
  doi:10.1152/jn.00032.2010). The datasets have no language localiser, so the region cannot be
  defined per subject, and its parcels miss part of each subject's language cortex. This
  misalignment also lowers the leave-one-out ISC in those parcels. Two consequences: a lack of
  alignment in the language region does not show that there is none, while a positive result
  remains informative; and a comparison of the visual and language regions mixes modality with
  how well the atlas fits each region. The coarse 200-parcel resolution absorbs part of the
  variability, since each parcel averages over a large patch of cortex.

## Changes

Changes to the method described above, oldest first. Each entry gives when the change happened,
what changed and why. The sections above always describe the current code.

### 2026-10-14 15:30 — page created

The region analysis was added to the pipeline, and this page written from its code.

### 2026-10-14 17:45 — summary tables moved to `results/tsv_summaries/`

The summary tables (`all_*.tsv`) are now written to `results/tsv_summaries/` instead of
`results/`; the paths on this page were updated.

### 2026-10-16 12:57 — limitation of the group-level language region documented

Section 5 has a new point: a group atlas fits individual language cortex poorly (Fedorenko et
al. 2010), so a null result in the language region is ambiguous and the visual-vs-language
comparison is confounded by atlas fit. Raised by a collaborator; no code or result changed.
