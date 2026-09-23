# 2026-09-23 — NSD invalid-coordinate handling; ISC manifest built from eligible stimuli

Follow-up to `2026-09-23-require-two-subjects-per-stimulus.md`, prompted by an
external review of commit `697af46`.

## NSD: invalid transform coordinates re-masked after every volume

- `nsd_data_dataset/scripts/assemble_nsd_bold.py`
  - `nsdcode.interp_wrapper()` sets invalid (non-finite) coordinates to `1` in
    place and marks them invalid only in the output of that one call.
    `map_occurrence_to_mni()` reused one copy of the coordinates for every
    volume of an occurrence, so from the second volume on, invalid locations
    would have been sampled as if they were valid.
  - `get_subject_mni_transform()` now records the invalid mask once per
    subject and stores all-finite coordinates, which `interp_wrapper()` has
    nothing to change in. `map_occurrence_to_mni()` re-applies the mask
    (→ `badval`) after every interpolation. The `reusable` flag and the
    per-occurrence copy are removed.
- **Impact on existing outputs: none.** None of the 8 subjects' func1pt8→MNI
  transforms contains an invalid coordinate (0 of 7,221,032 for each), so the
  old copy path never ran and the output is unchanged.
- Verified on a synthetic volume and transform with 50 invalid coordinates:
  - new output vs `interp_wrapper()` called with fresh raw coordinates for
    each volume: maximum absolute difference `0.0`;
  - the old reuse pattern differed by about 925 and 1,068 on volumes 2 and 3.

## ISC manifest: built from the eligible stimuli, not from the ISC directory

- `isc_nearest_neighbours/scripts/create_isc_manifest.py` now takes
  `--stimuli_dirs`.
  - The eligible set is every stimulus file stem in each directory minus
    `excluded_stimuli`. This is the same selection as
    `get_embeddings.load_stimuli()`.
  - It raises an error if the modality directories disagree, or if any
    eligible stimulus has no ISC file.
  - ISC files for stimuli that are not eligible are ignored and counted.
- `isc_nearest_neighbours/Snakefile`, `create_isc_manifest`: adds the
  `stimuli_ready` input and the `stimuli_dirs` param.
- Verified on the current on-disk data:
  - Caption Scene 8,920 rows, Narratives 18, Nature Stories 11: unchanged.
  - NSD now fails with `65701 of 66216 eligible stimuli have no ISC file`,
    because only 515 ISC files from a partial old-filter run exist. The
    previous version would have quietly written a 515-row manifest.
- `snakemake -n --cores 32` resolves.

## Not changed (review points left to the developer)

- NSD and Caption Scene `number_of_neighbours` stay `[5, 25, 50, 100]`.
  Previously they were `[5,50,250,500,1000]` (NSD) and
  `[5,50,500,2500,5000]` (Caption Scene). With about 1,000 retained stimuli,
  `k ≤ 999` is valid, so 250 and 500 could be restored. This is an
  experimental-design choice.
- NSD extraction failures still stop the job; no observation is ever
  dropped, so the two-subject criterion evaluated on presentations holds for
  what reaches the ISC. If observation-level QC exclusion is added later, the
  subject count must be re-checked after it.

---

*AI disclosure: written, with the code changes above, by Claude Code
(Anthropic, VS Code extension), model Claude Opus 5.5 (`claude-opus-5-5`),
2026-09-23, on instructions from Jonas Salvalaggio. Verification is limited to
the checks listed. Not yet reviewed by the developer.*
