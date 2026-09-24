# 2026-09-23 — Diagnosis: `create_isc_manifest` crash on Caption Scene after the two-subject rule

## Summary

No code was changed. This entry records a diagnosis, so that the next person
who hits the same error can find the cause and the fix.

After the two-subject retention change (commit `697af46`, see
`2026-09-23-require-two-subjects-per-stimulus.md`), the checkpoint
`create_isc_manifest` failed for `dataset=caption_scene` with:

```
File "workflow/isc_nearest_neighbours/scripts/create_isc_manifest.py", line 68, in main
    raise FileNotFoundError(...)
FileNotFoundError: 7920 of 8920 eligible stimuli have no ISC file in results/mind/caption_scene/isc,
e.g. ['COCO_train2014_000000000036', 'COCO_train2014_000000000529', ...]
```

## Root cause

The rule filters got out of sync with the files on disk:

| Artefact | State at crash time |
| --- | --- |
| `make_caption_scene_manifest.py` | New code (commit `697af46`, 2026-09-23 10:06): drops stimuli with `subject.nunique() < 2` |
| `intermediate_files/manifest/csd_events_manifest.tsv` | Old output (2026-09-13): 8,920 stimuli, of which 1,000 were seen by 8 subjects and 7,920 by 1 subject |
| `resources/datasets/caption_scene_dataset/V1/excluded_stimuli.txt` | Old output (2026-09-13): 5,164 entries, so 14,084 − 5,164 = 8,920 eligible |
| `results/mind/caption_scene/isc/`, `parcels/` | Already pruned to the 1,000 two-subject stimuli (dir mtime 2026-09-23 10:30) |

`create_isc_manifest.py` builds the expected stimulus set from each
`stimuli_dir` minus `excluded_stimuli`, so it still expected 8,920 ISC files.
The 7,920 it reported as missing are exactly the single-subject stimuli.

The documented `--forcerun make_nsd_manifest make_caption_scene_manifest`
step had not been run. Because the manifest script is called from a
`shell:` rule, Snakemake's code trigger does not see edits to it. Its
outputs were newer than its inputs, so nothing rebuilt it.

The script's missing-ISC check behaved as intended: it stopped the run
instead of silently computing neighbours over a mismatched stimulus set.

## Fix (operational, no code change)

Regenerate the Caption Scene manifest checkpoint, so that
`excluded_stimuli.txt` lists 13,084 stimuli and 1,000 remain eligible:

```bash
snakemake --use-conda --cores <N> --forcerun make_caption_scene_manifest -n   # inspect first
snakemake --use-conda --cores <N> --forcerun make_caption_scene_manifest
```

What to expect downstream:

- The new manifest mtime reschedules `split_caption_scene_bold_by_run_manifest`,
  `extract_caption_scene_parcels`, `compute_caption_scene_isc` and
  `write_caption_scene_stimuli_transcripts`. BOLD splitting is the expensive
  step.
- The language `stimuli_dir` can stay at 8,920 transcripts:
  `eligible_stimuli_in_dir` subtracts `excluded_stimuli` per directory, so
  both the language and vision dirs resolve to the same 1,000 stems.
- `llm_nearest_neighbours` rules take `excluded_stimuli` as an input and
  rerun on its new mtime. Embeddings built over the 8,920-stimulus set
  are stale.
- Cheaper alternative, not tested: run only the manifest script by hand,
  then `snakemake --touch` the downstream Caption Scene outputs to keep the
  existing 1,000 parcel/ISC files. This is only valid if those files were
  produced by the current parcel/ISC code.

## Verification performed

- Counted distinct subjects per `stimulus_id` in the manifest: 1,000 with
  8 subjects and 7,920 with 1. This matches the error's 7,920 / 8,920.
- `results/mind/caption_scene/isc/` holds 1,000 `*_isc_mean.npy` files.
- Line counts: 14,084 images in `All_images_480`, 8,920 transcripts,
  5,164 lines in `excluded_stimuli.txt`.
- Confirmed that `make_caption_scene_manifest.py` (lines 270–306) contains
  the `>= 2` subject filter.

**Not verified:**

- No `snakemake` dry run or rerun: `snakemake` was not on the assistant
  shell's `PATH`.
- The Caption Scene pipeline has not been rebuilt, and the fix above has not
  been confirmed end to end.
- NSD was not checked for the same staleness. If `make_nsd_manifest` was not
  forced either, the same error may appear for `nsd_data`.

## Follow-ups

- Run the forced rebuild for `make_caption_scene_manifest`, and for
  `make_nsd_manifest` if NSD's manifest also predates `697af46`.
- Consider adding the manifest scripts as explicit rule `input:` entries.
  Snakemake would then reschedule these checkpoints when the scripts change,
  and this class of failure would go away.

---

*AI disclosure: this changelog entry and the diagnosis it describes were
written by an AI coding assistant.*

- *Tool: Claude Code (Anthropic), VS Code extension.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`, 1M-token context).*
- *Date: 2026-09-23.*
- *Basis: the traceback pasted by the developer (Jonas Salvalaggio), and
  read-only inspection of the Snakefiles, scripts, manifest, ISC directory,
  file timestamps and git history.*
- *Verification: limited to the checks listed under "Verification
  performed". No commands that modify the pipeline were run.*
- *Review status: not yet reviewed by the developer at the time of writing.
  Review it before committing.*
