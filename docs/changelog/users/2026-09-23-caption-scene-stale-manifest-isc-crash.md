# 2026-09-23 — Why Caption Scene stopped with "eligible stimuli have no ISC file", and how to fix it

## What happened

A pipeline run stopped at the step that collects the brain-similarity (ISC)
results for the Caption Scene dataset, with this message:

```
FileNotFoundError: 7920 of 8920 eligible stimuli have no ISC file in results/mind/caption_scene/isc
```

Nothing is broken in the code, and no code was changed. Earlier the same
day, the rule for which images to keep was changed: an image now needs at
least two different participants to have seen it (see
`2026-09-23-require-two-subjects-per-stimulus.md`). Caption Scene has 1,000
such images. The other 7,920 were each seen by only one participant.

The brain results had already been reduced to those 1,000 images. However,
the dataset's list of included and excluded images was still the old one
from 2026-09-13, which counted all 8,920 images. The pipeline noticed the
mismatch and stopped, instead of producing results from an inconsistent set
of images.

## What this means for you

- Caption Scene results can't be produced until the image list is
  regenerated.
- The other datasets are not affected by this particular error. NSD uses the
  same two-participant rule, so it may need the same fix if its image list
  was not regenerated either.

## Action needed

Regenerate the Caption Scene image list. Snakemake won't do this by itself,
so ask for it explicitly. Preview what will run first (`-n`), then run it:

```bash
snakemake --use-conda --cores <N> --forcerun make_caption_scene_manifest -n
snakemake --use-conda --cores <N> --forcerun make_caption_scene_manifest
```

This rebuilds the Caption Scene brain data and the model results that depend
on the image list, so it can take a while.

---

*AI disclosure: this note was written by an AI coding assistant.*

- *Tool: Claude Code, VS Code extension.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Date: 2026-09-23.*
- *Basis: diagnosis of the crash in the same session, from the error the
  developer reported and read-only inspection of the project files.*
- *Review status: not yet reviewed by the developer at the time of writing.*

*The developer changelog entry of the same name lists exactly what was
checked and what was not.*
