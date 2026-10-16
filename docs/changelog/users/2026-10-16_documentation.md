# 2026-10-16 — changes for users

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../../AI_USAGE.md).*

Changes made on this day, in order:

- Limitation of the language region documented (documentation)

---

## 12:57 — Limitation of the language region documented

Kind: documentation

The language region used in the analysis comes from a standard brain atlas averaged over many
people. Language areas sit in somewhat different places in different people, much more than visual
areas do, so the atlas misses part of each person's language cortex. This means that finding no
alignment in the language region does not prove there is none, and that comparing the language
and visual regions is not a perfectly fair comparison. This is now explained in
`docs/reference/brain_regions.md`, section 5. Nothing in the pipeline or its results changed.
