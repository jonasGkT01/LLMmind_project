# 2026-10-02 — Caption Scene now aligned to MNI; repeated presentations averaged in the ISC

**Caption Scene brain data are now put into standard (MNI) space before the brain regions are
measured.** The dataset's BOLD files are in each participant's own anatomical space. Until now the
standard-space brain atlas was laid over them without any alignment, so each "region" covered a
different part of the brain in each participant. The pipeline now aligns each participant's
anatomical scan to the MNI template with ANTs, and uses that alignment to read the BOLD data at the
right place for every atlas region. A check image per participant
(`results/mind/caption_scene/registration/sub-*_t1w_to_mni_qc.png`) shows the aligned brain with the
template's outlines on top. In a test on one image, the region-by-region brain response changed
almost completely (correlation 0.16 between old and new), so all Caption Scene results change.

**NSD and Caption Scene: each participant's repeated viewings of an image are averaged first.**
The brain response of an image (ISC) compares each participant with the others. Participants saw
some images two or three times, and each viewing used to count as a separate participant, so a
person was partly compared with themselves. Now the repeats are averaged, so every participant
counts once. NSD results change moderately (median ISC 0.043 → 0.047 in a test).

**What you need:** the anatomical scans `V1/sub-*/anat/sub-*_ses-01_run-001_T1w.nii.gz` must be
present (they come with the dataset), and the pipeline downloads the MNI template the first time.
The cropped Caption Scene volumes in
`results/mind/caption_scene/intermediate_files/single_stimulus_bold/` (about 121 GB) are no longer
written or used and can be deleted.

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-02, Claude Opus 5.5: written for TODO entries S10 and S31 (approved by the developer on 2026-09-30), implemented when the developer asked to go on with S10 and S31.*
- *Files changed: see the developer changelog entry of the same name.*
- *Review status: not yet reviewed by the developer.*
