# 2026-09-23 — changes for users

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../../AI_USAGE.md).*

Changes made on this day, in order:

- Stimuli must now have been seen by at least two different participants (new_feature)
- Repository cleanup and corrections to the previous note (refactor, documentation)
- Fairer handling of long texts and of weak brain signals (bugfix)
- Tidier code, same results (refactor)
- Fixed a crash in the random-shuffling significance step (bugfix)
- Why Caption Scene stopped with "eligible stimuli have no ISC file", and how to fix it (bugfix)

---

## Stimuli must now have been seen by at least two different participants

Kind: `new_feature`

### What changed

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

### What this means for you

- NSD and Caption Scene results are based on far fewer stimuli than before,
  but each one now reflects agreement between different people.
- NSD now needs very little disk space for its intermediate brain data.
- Neighbourhood sizes (`number_of_neighbours`) must be smaller than the
  number of remaining stimuli (about 1,000 for NSD and Caption Scene).

### Action needed

- Rerun the pipeline for NSD and Caption Scene. Their previous outputs no
  longer match this rule and should be treated as outdated. Snakemake won't
  notice this change on its own, so start the rerun with:

  ```bash
  snakemake --use-conda --cores <N> --forcerun make_nsd_manifest make_caption_scene_manifest
  ```
- The folder `results/mind/nsd_data/single_stimulus_bold_mni/` is no longer
  produced or read. You can delete it to free its disk space (currently
  about 1.8 TB).

### Context

- Basis: the developer's instructions in the same session.

---

## Repository cleanup and corrections to the previous note

Kind: `refactor`, `documentation`

### What changed

**Cleanup.** When Python runs, it saves helper files (in folders called
`__pycache__`) to start faster next time. A few of these were stored in
the project history by mistake. They are gone, and the project is now set
up so they can't be added again.

**Corrections to the
[previous note](2026-09-23_new_feature_bugfix_refactor_documentation.md).**
That note described two fixes. The fixes themselves still stand, but three
things it said were not accurate:

- **Short texts can change too.** It said only long texts were affected.
  In fact, texts just short enough to fit in one piece were also given an
  unnecessary second piece before, so their results can shift as well.
  Images are still unaffected.
- **Not every part of a text counts equally.** Long texts are still cut
  into overlapping pieces, so the parts where two pieces overlap still
  count a little more than the very start and end of the text. The fix
  only removed the extra repeated piece at the end.
- **"Flat" is a small tolerance, not a perfect test.** A brain region still
  gets a score of zero if its signal barely moves, even if the movement is
  real. The margin is tiny (about one part in a million of the signal's
  size), but it is a choice, not a mathematical certainty. Whether to keep
  it will be decided after checking real data.

### What this means for you

- Your results do not change because of this note: no analysis code was
  touched.
- If you rerun embeddings as the previous note suggested, expect some
  short texts to change as well as long ones.

### Action needed

None beyond the rerun already described in the previous note.

### Context

- Basis: an external review of the project and the developer's instructions (Jonas Salvalaggio) in the same session.

---

## Fairer handling of long texts and of weak brain signals

Kind: `bugfix`

> **Correction:** some statements below (which texts change, equal
> weighting, what counts as a flat signal) were inaccurate; see
> [`2026-09-23_new_feature_bugfix_refactor_documentation.md`](2026-09-23_new_feature_bugfix_refactor_documentation.md).

### What changed

This update fixes two small accuracy problems, one on each side of the
brain-model comparison.

**Long texts on the model side.** When a story or transcript is too long
for a language model to read at once, the pipeline cuts it into overlapping
pieces. It runs the model on each piece and averages the results. At the
end of some texts, the pipeline used to add an extra piece that repeated
text the previous piece had already covered. The ending of those texts
therefore counted twice in the average. That repeat is gone, so every part
of a text now counts equally.

**Weak brain signals on the brain side.** A brain region whose recorded
signal is completely flat carries no information. The pipeline gives such
regions a score of zero. The test for "flat" used to be too strict: it also
caught regions with a real but very small fluctuation and set them to zero
by mistake. The test now catches only signals that are flat for real
(identical apart from the smallest rounding differences a computer makes).

### What this means for you

- Language-model results can shift slightly for Narratives and Nature
  Stories, and for any other long text stimuli. Only texts where the extra
  piece used to be added are affected. Short texts and images are unchanged.
- Brain-side scores can change for the few brain regions whose weak
  signal used to be zeroed. All other regions give exactly the same values
  as before.
- Nothing needs to change in your configuration.

### Action needed

Snakemake will not notice these changes by itself. To bring existing
results up to date, rerun the affected steps:

```bash
snakemake --use-conda --cores <N> --forcerun get_embeddings compute_narratives_isc compute_nature_stories_isc
```

NSD and Caption Scene already need a rerun because of the
[two-participant rule](2026-09-23_new_feature_bugfix_refactor_documentation.md).
That rerun picks up this fix too.

### Context

- Basis: an external review of the project and the developer's instructions (Jonas Salvalaggio) in the same session.

---

## Tidier code, same results

Kind: `refactor`

### What changed

This is a housekeeping update to the project's Python scripts. It makes
them easier to read. It does not change what they do.

- **Consistent layout at the top of every script.** Each script lists the
  tools it relies on at the top. That list now always follows the same
  order: Python's built-in tools first, then general data tools (such as
  NumPy and pandas), then brain-imaging and language-model tools, and
  finally the project's own helpers.
- **Shorter explanatory notes.** Many scripts contain notes explaining why
  something is done a certain way. The longer ones have been cut down to
  a line or two, keeping the reason and dropping the extra detail.
- **Cleaner project history.** Python leaves behind temporary helper files
  when it runs. The project is now set up so these can never be saved into
  its history by accident.

### What this means for you

- Nothing changes in how you run the pipeline or in the results it
  produces.
- There is no need to rerun anything.

### Action needed

None.

### Context

- Basis: the developer's (Jonas Salvalaggio) instructions in the same session.

---

## Fixed a crash in the random-shuffling significance step

Kind: `bugfix`

### What changed

On 2026-09-23 a pipeline run stopped early, after about 4% of its steps.
The step that failed builds the "random shuffle" baseline, which is used to
test whether a model's agreement with brain data is better than chance. It
failed first for the Nature Stories dataset with the `bloom_560m` model.

The cause was a newer version of pandas, a data-handling library the step
depends on. The step's software environment had picked up that version
automatically, and one line of code in the step no longer worked with it.
That line has been fixed.

Your data and earlier results were not affected. The step now runs to the
end and produces the expected output.

### What this means for you

- No settings or input files need to change.
- The significance results for brain-vs-model comparisons can now be
  produced again.

### Action needed

Restart the pipeline with your usual command and add `--rerun-incomplete`.
The run that crashed left some half-finished files, and this option tells
Snakemake to redo them:

```bash
snakemake --use-conda --cores <N> --rerun-incomplete
```

Steps that already finished will not be repeated.

### Context

- Basis: diagnosis of the crashed run and the fix applied in the same session, at the developer's request.

---

## Why Caption Scene stopped with "eligible stimuli have no ISC file", and how to fix it

Kind: `bugfix`

### What happened

A pipeline run stopped at the step that collects the brain-similarity (ISC)
results for the Caption Scene dataset, with this message:

```
FileNotFoundError: 7920 of 8920 eligible stimuli have no ISC file in results/mind/caption_scene/isc
```

Nothing is broken in the code, and no code was changed. Earlier the same
day, the rule for which images to keep was changed: an image now needs at
least two different participants to have seen it (see
`2026-09-23_new_feature_bugfix_refactor_documentation.md`). Caption Scene has 1,000
such images. The other 7,920 were each seen by only one participant.

The brain results had already been reduced to those 1,000 images. However,
the dataset's list of included and excluded images was still the old one
from 2026-09-13, which counted all 8,920 images. The pipeline noticed the
mismatch and stopped, instead of producing results from an inconsistent set
of images.

### What this means for you

- Caption Scene results can't be produced until the image list is
  regenerated.
- The other datasets are not affected by this particular error. NSD uses the
  same two-participant rule, so it may need the same fix if its image list
  was not regenerated either.

### Action needed

Regenerate the Caption Scene image list. Snakemake won't do this by itself,
so ask for it explicitly. Preview what will run first (`-n`), then run it:

```bash
snakemake --use-conda --cores <N> --forcerun make_caption_scene_manifest -n
snakemake --use-conda --cores <N> --forcerun make_caption_scene_manifest
```

This rebuilds the Caption Scene brain data and the model results that depend
on the image list, so it can take a while.

### Context

- Basis: diagnosis of the crash in the same session, from the error the developer reported and read-only inspection of the project files.
