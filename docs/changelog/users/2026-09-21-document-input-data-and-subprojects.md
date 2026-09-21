# 2026-09-21 — README now explains what data you need and what each part does

## What changed

The `README.md` file has two new sections:

- **Subprojects** — a plain description of what each piece of the pipeline
  actually does, from turning raw brain scans into "mind" representations,
  through extracting model embeddings, to scoring alignment and making the
  final plots.
- **Input data** — a checklist of exactly which raw data files need to exist,
  and where, before you can run the project for the first time, plus a new
  "Organising the input data on disk" section showing how to get them into
  place.

## What this means for you

If you've ever wondered "what files do I actually need before I can run
this?" or "what does the `llm_llm_alignment` folder even do?", the README
now answers both directly instead of you having to dig through the code or
ask around.

The Input data section also spells out which things you *don't* need to
worry about providing yourself — pretrained model weights and the brain
atlas download automatically the first time they're needed (as long as
you have internet access), and the `results/` folder is entirely generated
by the pipeline.

## Action needed

None for existing setups that already work. If you're setting up a fresh
checkout of the project, follow the new "Organising the input data on disk"
section in the README before your first run — it walks through linking the
downloaded datasets into the right place.
