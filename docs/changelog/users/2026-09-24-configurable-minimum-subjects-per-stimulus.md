# 2026-09-24 — You can now choose how many subjects must have seen a stimulus

## What changed

A stimulus is used in the analysis only if enough different subjects saw
it. That number used to be fixed at 2 inside the code. It is now a setting
at the top of `config/config.yaml`, next to `number_of_relabellings` and
`random_seed`:

```yaml
minimum_subjects_per_stimulus: 2
```

## What this means for you

- The default is still 2, so results do not change unless you change the
  value.
- Raising it keeps only stimuli seen by more subjects. This applies to
  Caption Scene, NSD and Narratives. Nature Stories already requires every
  subject to have heard every story.
- Changing the value makes Snakemake rebuild the stimulus lists and
  everything that depends on them.

---
*AI disclosure: this note was written by an AI coding assistant.*

- *Tool: Claude Code, VS Code extension.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Date: 2026-09-24.*
- *Basis: the developer's instructions in the same session.*
- *Review status: not yet reviewed by the developer at the time of writing.*

*The developer changelog entry of the same name lists exactly what was
tested.*
