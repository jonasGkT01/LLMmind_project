# 2026-09-23 — Fairer handling of long texts and of weak brain signals

> **Correction:** some statements below (which texts change, equal
> weighting, what counts as a flat signal) were inaccurate; see
> [`2026-09-23-untrack-python-bytecode-and-doc-corrections.md`](2026-09-23-untrack-python-bytecode-and-doc-corrections.md).

## What changed

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

## What this means for you

- Language-model results can shift slightly for Narratives and Nature
  Stories, and for any other long text stimuli. Only texts where the extra
  piece used to be added are affected. Short texts and images are unchanged.
- Brain-side scores can change for the few brain regions whose weak
  signal used to be zeroed. All other regions give exactly the same values
  as before.
- Nothing needs to change in your configuration.

## Action needed

Snakemake will not notice these changes by itself. To bring existing
results up to date, rerun the affected steps:

```bash
snakemake --use-conda --cores <N> --forcerun get_embeddings compute_narratives_isc compute_nature_stories_isc
```

NSD and Caption Scene already need a rerun because of the
[two-participant rule](2026-09-23-require-two-subjects-per-stimulus.md).
That rerun picks up this fix too.

---

*AI disclosure: this note was written by an AI coding assistant.*

- *Tool: Claude Code, VS Code extension.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`, 1M-token context).*
- *Date: 2026-09-23.*
- *Basis: an external review of the project and the developer's
  instructions (Jonas Salvalaggio) in the same session.*
- *Review status: not yet reviewed by the developer at the time of writing.*

*The developer changelog entry of the same name lists exactly what was
changed and tested.*
