# 2026-09-23 — Stimuli must now have been seen by at least two different participants

## What changed

An image, caption or story is now included in the analysis only if **at
least two different participants** saw or heard it. Before this change,
two recordings were enough, even if both came from the same participant
viewing the same image twice.

The rule exists because the brain-side measure is meant to compare
different people's brain responses. For a stimulus seen by only one person,
it could only compare that person with themselves.

Every recording of an included stimulus still counts, including repeat
viewings by the same participant.

This matters most for two datasets:

- **NSD**: about 1,000 of 66,216 images remain. These are the images that
  were shown to several participants.
- **Caption Scene**: 1,000 of 8,920 stimuli remain. These are the ones seen
  by all 8 participants.

Narratives and Nature Stories are unaffected, because every story there was
heard by many participants.

The same list of excluded stimuli is now used on both sides of the
comparison. It controls which brain responses enter the analysis, and which
stimuli the language/vision models are run on. The two sides always cover
exactly the same stimuli.

NSD processing also no longer saves a full-brain scan for every single
image viewing. It now keeps only the 200 brain-region summaries the
analysis actually uses. The previous approach needed tens of terabytes of
disk space; the results are numerically identical.

## What this means for you

- NSD and Caption Scene results are based on far fewer stimuli than before,
  but each one now reflects agreement between different people.
- NSD now needs very little disk space for its intermediate brain data.
- Neighbourhood sizes (`number_of_neighbours`) must be smaller than the
  number of remaining stimuli (about 1,000 for NSD and Caption Scene).

## Action needed

- Rerun the pipeline for NSD and Caption Scene. Their previous outputs no
  longer match this rule and should be treated as outdated. Snakemake won't
  notice this change on its own, so start the rerun with:

  ```bash
  snakemake --use-conda --cores <N> --forcerun make_nsd_manifest make_caption_scene_manifest
  ```
- The folder `results/mind/nsd_data/single_stimulus_bold_mni/` is no longer
  produced or read. You can delete it to free its disk space (currently
  about 1.8 TB).

---

*AI disclosure: this note was written by an AI coding assistant.*

- *Tool: Claude Code, VS Code extension.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Date: 2026-09-23.*
- *Basis: the developer's instructions in the same session.*
- *Review status: not yet reviewed by the developer at the time of writing.*

*The developer changelog entry of the same name lists exactly what was
tested.*
