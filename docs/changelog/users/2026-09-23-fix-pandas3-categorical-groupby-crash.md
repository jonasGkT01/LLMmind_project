# 2026-09-23 — Fixed a crash in the random-shuffling significance step

## What changed

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

## What this means for you

- No settings or input files need to change.
- The significance results for brain-vs-model comparisons can now be
  produced again.

## Action needed

Restart the pipeline with your usual command and add `--rerun-incomplete`.
The run that crashed left some half-finished files, and this option tells
Snakemake to redo them:

```bash
snakemake --use-conda --cores <N> --rerun-incomplete
```

Steps that already finished will not be repeated.

---

*AI disclosure: this note was written by an AI coding assistant.*

- *Tool: Claude Code, VS Code extension.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Date: 2026-09-23.*
- *Basis: diagnosis of the crashed run and the fix applied in the same
  session, at the developer's request.*
- *Review status: not yet reviewed by the developer at the time of writing.*

*The developer changelog entry of the same name lists exactly what was
tested.*
