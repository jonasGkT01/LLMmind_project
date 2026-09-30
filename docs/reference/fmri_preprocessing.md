# fMRI preprocessing: what the dataset authors did, and what this workflow does

This page describes, for each of the four fMRI datasets, how the BOLD data were processed
**before** this workflow receives them, and the few steps the workflow **itself** applies before
computing the brain representations (the per-stimulus, 200-parcel ISC vectors). Use it as the
source for the methods section.

## 1. Preprocessing by the dataset authors

| | Narratives | Caption Scene (CSD) | Nature Stories | NSD |
|---|---|---|---|---|
| Files used | `derivatives/afni-smooth/sub-*/func/*_space-MNI152NLin2009cAsym_res-native_desc-clean_bold.nii.gz` | `V1/derivatives/pp_data/sub-*/func/*_task-CSD_run-*.nii.gz` | `responses/S*_BOLD.hdf` (`zRresp`, `zPresp`) | `nsddata_timeseries/ppdata/subj*/func1pt8mm/timeseries/*.nii.gz` |
| Space | MNI152NLin2009cAsym (`sform_code` 3) | **each subject's native anatomical space** (`sform_code` 1, 2.5 mm) | native cortical voxels (pycortex mask) | native functional space, 1.8 mm (`sform_code` 1) |
| TR | 1.5 s | 2.0 s | 2.0 s | 1.333 s (temporally resampled) |
| Motion / distortion / slice timing | fMRIPrep: realignment, susceptibility distortion correction, normalisation | FSL: slice timing, `topup` distortion correction, rigid motion correction, BBR alignment to the subject's anatomy, one-step resampling | done upstream (not detailed in the dataset README) | one temporal resampling (slice timing) and one spatial resampling (motion, EPI distortion, gradient non-linearity) |
| Spatial smoothing | 6 mm FWHM (AFNI `3dBlurToFWHM`, `desc-sm6`) | none described | none described | none |
| Confound regression | AFNI `3dTproject`: 6 motion parameters, first 5 aCompCor components (CSF + WM), cosine high-pass basis (128 s) | none described | none described | none |
| Detrending | **yes**: `3dTproject -polort 2` (polynomial trends up to 2nd order), output `desc-clean` | none described | **yes** (README: "detrended") | none described. Values are raw scanner units (`int16`, in-brain mean ≈ 600). The in-brain mean drifts by ~0.07 % over one run (checked on subj01, session 4, run 6). |
| Z-scoring / scaling | none (`3dTproject` run without `-norm`) | none described | **yes**: z-scored per story and voxel along time, after trimming 10 TRs at each end | none |

Sources:

- Narratives: Nastase et al., *Sci. Data* 8, 250 (2021), and the authors' code
  (`code/run_regression.py`, `code/run_smoothing.py`, `code/slurm_smoothing.sh` in
  <https://github.com/snastase/narratives>).
- Caption Scene: "A large-scale fMRI dataset for vision-language semantic association",
  *Sci. Data* (2026), doi:10.1038/s41597-026-07248-6. Trial: caption 3 s, blank 3 s, image 3 s,
  fixation 3 s; 12 s in total; 8 subjects.
- Nature Stories: the dataset's `README.md`, section "Preprocessing".
- NSD: Allen et al., *Nat. Neurosci.* 25, 116–126 (2022), and the NSD Data Manual. The file
  properties were read from the released files.

## 2. What this workflow does

The workflow adds **no** detrending, filtering, confound regression, smoothing or z-scoring. Its
steps are listed below.

**1. Stimulus selection.** A stimulus is kept only if at least `minimum_subjects_per_stimulus`
(= 2) different subjects saw it, and it is not in the dataset's `excluded_stimuli.txt`.

- Narratives: the 10 `problematic_subtasks` of `config.yaml` (the schema sub-stories and the two
  scrambled "Not the Fall" versions) are dropped, and scans listed in `scan_exclude.json` are
  excluded. That leaves 18 stories.
- Caption Scene: events flagged `Blank` or `Unmatch` in the run tables are dropped.

**2. Stimulus windows**, only for the event-related datasets:

- Caption Scene: `start_vol = round((onset + onset_shift_s) / TR)` and
  `n_vols = ceil(event_duration_s / TR)` = ceil(12 / 2) = **6 volumes**, with `onset_shift_s = 0`.
  The windows are recorded per event in `csd_events_manifest.tsv`.
- NSD: from the design files, `start_vol = onset volume + onset_shift_volumes` (= 0) and
  `n_vols = ceil(4 s / 1.333 s)` = **3 volumes**. They are recorded in `nsd_occurrence_manifest.tsv`.
- Narratives and Nature Stories: whole stories. Nature Stories' concatenated `zRresp` is split
  back into stories with `new_run_onsets.json`, and the test story comes from `zPresp`.

**3. Into template space.**

- Narratives: already in MNI.
- NSD: each presentation is mapped `func1pt8 → MNI` (1 mm) with NSD's own transforms (`nsdcode`,
  cubic interpolation).
- Nature Stories: native voxels are mapped to fsaverage with the dataset's `mappers`, keeping only
  voxels with finite data and renormalising the rows.
- Caption Scene: **no normalisation is applied**. The MNI atlas is resampled directly onto the
  native grids. This is a known error, tracked as TODO P31, and the Caption Scene results are to be
  regenerated after it is fixed.

**4. Parcellation.** Schaefer 2018, 200 parcels, 7 networks: the MNI volume atlas, resampled with
nearest neighbour onto the BOLD grid, or the fsaverage atlas for Nature Stories. Each parcel's time
series is the **unweighted mean of its voxels** (or vertices).

**5. Equal lengths.** Narratives truncates all subjects of a story to the shortest run. The other
datasets require equal lengths and stop with an error otherwise.

**6. ISC.** For each stimulus and parcel: the Pearson correlation between each subject (NSD: each
presentation) and the mean of all others, averaged over subjects. It is set to 0 when either time
series is constant. The 200 values form the stimulus's brain representation.

### Why z-scoring would change (almost) nothing, and what it means for cosine similarity

- **ISC is Pearson-based.** Pearson's r between two time series is unchanged if either series is
  shifted by a constant or multiplied by a positive constant. Z-scoring a parcel time series is
  exactly such a transformation (subtract its mean, divide by its SD). So:
  - z-scoring the **held-out** subject's series changes nothing;
  - z-scoring the **other** subjects' series *before* averaging them into the reference is not
    quite a no-op. Their average becomes a weighted average, each subject weighted by 1/SD.
    Z-scoring therefore changes the leave-one-out ISC only if subjects' SDs differ within a
    parcel, and only through that re-weighting of the reference, never through the correlation
    itself. If all subjects of a parcel have the same SD, it changes nothing at all.

  For Nature Stories this question does not arise, since the data are already z-scored upstream.
- **Cosine similarity is applied later, to different data.** The brain-side cosine, Pearson and
  Spearman similarities (`libraries/compute_similarity.py`) compare the **200-value ISC vectors of
  two stimuli**, not BOLD time series. Z-scoring the BOLD time series reaches that step only
  through the small re-weighting above, which changes the ISC values themselves. Cosine *would* change if the **ISC vectors** themselves
  were z-scored, e.g. across parcels: cosine is not invariant to subtracting a mean, and on
  mean-centred, unit-variance vectors cosine becomes equal to Pearson. The workflow does not do
  this. It computes cosine on the raw ISC vectors, and Pearson (mean-centred) and Spearman (ranks)
  as the two alternatives.
- **Voxel-level z-scoring is different.** Z-scoring *voxels before* averaging them into parcels
  changes the parcel signal, because it gives every voxel equal weight regardless of its variance.
  That is what Nature Stories' upstream z-scoring does. It is part of that dataset's preprocessing,
  not something this workflow adds.

### Why the workflow does not detrend

- Narratives and Nature Stories are already detrended upstream.
- For NSD and Caption Scene, the ISC is computed on windows of only 3 and 6 volumes. Removing a
  linear trend *inside* such a window would take away most of its degrees of freedom: with 3
  points, one residual degree of freedom remains, and every correlation becomes ±1. Drift
  correction would therefore have to be applied to whole runs before cropping. The drift within one
  window is negligible compared with the stimulus response: for NSD, the in-brain mean drifts by
  about 0.07 % over a whole run. The current approach is kept (decision of 2026-09-30).
- The short windows themselves (a correlation over 3 or 6 time points) are a separate
  methodological question, tracked as TODO P30.

---

*This page was written by an AI coding assistant.*

- *Tool: Claude Code (Anthropic), VS Code extension, on the lab server.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Date: 2026-09-30.*
- *Basis: the developer (Jonas Salvalaggio) asked for a short document separating the dataset
  authors' preprocessing from the workflow's own processing (TODO P9), with the missing facts
  checked online. The dataset rows come from the sources listed above. The Caption Scene space and
  the NSD file properties were checked on the local files. The workflow rows come from the code:
  `make_caption_scene_manifest.py`, `make_nsd_manifest.py`, `assemble_nsd_bold.py`,
  `extract_*_parcels.py`, `libraries/fmri_processing.py`, the dataset Snakefiles and
  `config/config.yaml`.*
- *Not verified: the Narratives confound list (6 motion + 5 aCompCor + cosine 128 s) is taken
  from the paper as summarised by a search engine, since the full text could not be fetched. The
  `-polort 2` detrending and the 6 mm smoothing were read directly from the authors' scripts.*
- *Review status: not yet reviewed by the developer at the time of writing.*
