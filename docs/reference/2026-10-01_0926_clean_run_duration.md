# Clean run duration: how long a full run takes, rule by rule

> *Written with AI assistance (Claude Code). See the [AI attribution](#ai-attribution) note at the end.*

This page estimates how long a **clean run** of the whole workflow takes (every output rebuilt,
e.g. `snakemake --forceall`). It assumes the usual command on **node5** (1× RTX A5000 24 GB,
251 GB RAM):

```bash
snakemake --use-conda --cores 4 --resources gpu=1
```

**Short answer: about 25 hours (24–30 h) if the models are already in `resources/models/`, and
about 1.5 h more if they have to be downloaded.**

## 1. Where the numbers come from

- **Job counts**: dry run of the current workflow, `snakemake -n --forceall` (40,964 jobs before
  checkpoints), plus the jobs added by the caption_scene checkpoint (795 BOLD runs, 1,000
  stimuli, read from `results/mind/caption_scene/intermediate_files/manifest/`).
- **Durations**: the start and `Finished jobid` timestamps of every job in the 323 node5 logs in
  `.snakemake/log/` (263,056 finished jobs in total). For each rule, the table uses the **most
  recent run** in which that rule ran, so the figures match the current code as closely as
  possible.
- Durations are wall-clock seconds per job at 1 s resolution. They include conda activation and
  were measured while up to 4 jobs were running at the same time.
- "Total" is the job count × the mean duration, i.e. job-hours of work, not elapsed time.
  Section 3 turns job-hours into elapsed time.

## 2. Per-rule durations

Times are given in seconds (s), minutes (min) or hours (h). "Median" and "max" are per job.

### 2a. Model downloads and embeddings

| Rule | Jobs | Median | Max | Total | Measured in |
|---|---:|---:|---:|---:|---|
| `download_pretrained_llm` | 38 | 8.6 min | 17 min | ~5.8 h | 2026-09-29 (4 jobs) |
| `get_embeddings` (GPU, one at a time) | 100 | 56 s | 12.9 min | ~3.2 h | 2026-09-29 |
| `compute_llm_nearest_neighbours` | 100 | 2 s | 7 s | 5 min | 2026-09-29 |

`download_pretrained_llm` runs only for models that are missing from `resources/models/`. It is
limited by network speed. `get_embeddings` depends mostly on model size. The slowest jobs are the
4-bit 27–31B models: `gemma2_27b` (8.8–12.9 min), `gemma3_27b` (5.9–9.9 min) and `gemma4_31b`
(8.3–9.7 min). The 8-bit 9–13B models take 3.5–6 min, and models up to 7B take less than 1 min.

### 2b. Brain data processing

| Rule | Jobs | Median | Max | Total | Measured in |
|---|---:|---:|---:|---:|---|
| **NSD** | | | | | |
| `export_nsd_stimuli` | 1 | 98 s | | 98 s | 2026-09-24 |
| `make_nsd_manifest` | 1 | 23 s | | 23 s | 2026-09-24 |
| `write_nsd_parcel_manifest` | 1 | 8 s | | 8 s | 2026-09-24 |
| `assemble_nsd_bold` (uses all 4 cores) | 1 | 11.4 h | | 11.4 h | 2026-09-24 |
| `write_nsd_isc_manifest` | 1 | 9 s | | 9 s | 2026-09-24 |
| `compute_nsd_isc` | 1 | 9.4 min | | 9.4 min | 2026-09-24 |
| **caption_scene** | | | | | |
| `make_caption_scene_manifest` (checkpoint) | 1 | 67 min | | 67 min | 2026-09-24 |
| `split_caption_scene_bold_by_run_manifest` | 795 | 24 s | 34 s | 5.3 h | 2026-09-24 |
| `extract_caption_scene_parcels` | 1 | 25 min | | 25 min | 2026-09-24 |
| `compute_caption_scene_isc` | 1,000 | 2 s | 7 s | 39 min | 2026-09-24 |
| `write_caption_scene_stimuli_transcripts` | 1 | 13 s | | 13 s | 2026-09-24 |
| `finish_caption_scene_isc` | 1 | 2 s | | 2 s | 2026-09-24 |
| **narratives** | | | | | |
| `rename_narratives_stimuli_transcipts` | 1 | 1 s | | 1 s | 2026-06-19 |
| `write_narratives_problematic_stimuli` | 1 | 11 s | | 11 s | 2026-09-23 |
| `write_narratives_parcel_manifest` | 1 | 6 s | | 6 s | 2026-06-19 |
| `extract_narratives_parcels` | 1 | 42 min | | 42 min | 2026-06-19 |
| `write_narratives_isc_manifest` | 1 | 4 s | | 4 s | 2026-06-19 |
| `compute_narratives_isc` | 1 | 62 s | | 62 s | 2026-06-19 |
| `mark_narratives_isc_done` | 1 | <1 s | | <1 s | 2026-06-19 |
| **nature_stories** | | | | | |
| `write_nature_stories_excluded_stimuli` | 1 | 4 s | | 4 s | 2026-09-28 |
| `convert_nature_stories_textgrids`, `verify_nature_stories_stimuli`, `write_nature_stories_parcel_manifest`, `extract_nature_stories_parcels`, `write_nature_stories_isc_manifest`, `compute_nature_stories_isc`, `mark_nature_stories_isc_done` | 1 each | not measured | | <1 h (guess) | never in a node5 log |
| **ISC nearest neighbours (all 4 datasets)** | | | | | |
| `create_isc_manifest` (checkpoint) | 4 | 2 s | 3 s | 8 s | 2026-09-28 |
| `create_isc_dataframe` | 4 | 2 s | 4 s | 8 s | 2026-09-28 |
| `compute_isc_nearest_neighbours` | 4 | 2 s | 2 s | 6 s | 2026-09-28 |

The narratives figures come from June 2026 and may not match the current scripts exactly. The
nature_stories rules have no recorded timing. The guess assumes they cost about as much as the
narratives rules, which do the same steps.

### 2c. Model–brain alignment and statistics

| Rule | Jobs | Median | Max | Total | Measured in |
|---|---:|---:|---:|---:|---|
| `compute_llm_mind_alignment_score` | 768 | 1 s | 13 s | 18 min | 2026-09-29 |
| `relabel_llm_similarity_and_compute_relabelled_llm_alignment_score` | 300 | 16 s | 24 s | 53 min | 2026-09-29 |
| `compute_empirical_p_value` | 768 | 4 s | 7 s | 41 min | 2026-09-30 |
| `compute_hypergeometric_p_value` | 768 | 1 s | 11 s | 20 min | 2026-09-29 |
| `aggregate_all_p_value_outputs` | 1 | 3.3 min | | 3.3 min | 2026-10-01 (16 min before S34) |
| `compute_spearman_alignmentwith_empirical_p_value` | 300 | 1.8 min | 2.2 min | 5.2 h | 2026-09-29 |
| `aggregate_all_spearman_alignment_scores` | 1 | 2 s | | 2 s | 2026-09-29 |

### 2d. Model–model alignment and statistics

| Rule | Jobs | Median | Max | Total | Measured in |
|---|---:|---:|---:|---:|---|
| `compute_llm_llm_alignment_score` | 11,184 | 1 s | 8 s | 3.7 h | 2026-09-29 |
| `relabel_llm_similarity_and_compute_relabelled_llm_llm_alignment_score` | 4,038 | 13 s | 17 s | 9.8 h | 2026-09-30 |
| `compute_llm_llm_empirical_p_value` | 11,184 | 3 s | 7 s | 9.6 h | 2026-09-30 |
| `compute_llm_llm_hypergeometric_p_value` | 11,184 | 1 s | 4 s | 4.7 h | 2026-09-30 |
| `aggregate_all_llm_llm_p_value_outputs` | 1 | 51 min | | 51 min | 2026-10-01 (4 h 10 min before S34) |

### 2e. Plots

| Rule | Jobs | Median | Max | Total | Measured in |
|---|---:|---:|---:|---:|---|
| `plot_concept_alignment_scatterplot` | 30 | 2 s | 3 s | 1 min | 2026-09-30 |
| `plot_concept_alignment_enrichment_scatterplot` | 30 | 9 s | 22 s | 6 min | 2026-09-30 |
| `plot_brain_model_alignment_lineplot` | 30 | 2 s | 2 s | 1 min | 2026-09-30 |
| `plot_brain_model_alignment_enrichment_lineplot` | 30 | 9 s | 23 s | 6 min | 2026-09-30 |
| `plot_alignment_heatmap` | 30 | 4.5 s | 10 s | 3 min | 2026-09-29 |
| `plot_empirical_p_value_heatmap` | 30 | 7 s | 13 s | 4 min | 2026-09-29 |
| `plot_spearman_alignment` | 12 | 4 s | 10 s | 1 min | 2026-09-29 |

## 3. From job-hours to elapsed time

The whole run is about **57 job-hours** of work (about 63 with downloads). It does not simply
take 56/4 h, for three reasons:

1. **`assemble_nsd_bold` takes all 4 cores** (`threads: workflow.cores`) for 11.4 h. Nothing else
   runs alongside it. This is the main reason the dataset-processing run of 2026-09-24 averaged
   only 1.5 jobs in parallel.
2. **`get_embeddings` runs one job at a time** (`resources: gpu=1`). Its 3.2 h mostly overlap with
   the CPU jobs, as long as Snakemake does not schedule them during `assemble_nsd_bold`.
3. **The many short alignment and statistics jobs** (about 40,000 jobs of 1–15 s each) averaged
   3.7 jobs in parallel in the runs of 2026-09-28 and 2026-09-29.

| Stage | Elapsed time |
|---|---:|
| Model downloads (only if `resources/models/` is empty; 4 at a time) | ~1.5 h |
| `assemble_nsd_bold` (alone on all cores) | 11.4 h |
| Rest of the brain data processing (caption_scene ~3 h, narratives and nature_stories ~1–2 h, mostly in parallel) | ~3 h |
| Embeddings (GPU); mostly overlap with the stage above | ~0–1 h extra |
| Alignment, statistics and plots (~36 job-h at 3.7 in parallel) | ~10 h |
| Final aggregation steps (one job at a time at the end) | ~1 h |
| **Total, models already downloaded** | **~26 h (25–31 h)** |
| **Total, models downloaded too** | **~28 h** |

As a check against real runs: the 2026-09-24 run (mostly brain data processing, including
`assemble_nsd_bold`) took 15.3 h. The 2026-09-29 run (embeddings and all downstream steps,
26,153 jobs) took 7.9 h. The 2026-09-30 run (27,294 jobs, including the new model–model
relabelled null) took 8.8 h before it got stuck on the hung job.

## 4. How to update these numbers

Each `.snakemake/log/*.snakemake.log` written on node5 starts with `host: node5`. For every job
it prints a `[timestamp]` line followed by `rule <name>:` and `jobid: <n>`, and later a
`[timestamp]` line followed by `Finished jobid: <n> (Rule: <name>)`. Pairing the two timestamps
by job id gives each job's duration. `snakemake -n --forceall` prints the job count per rule.

## 5. Changes

Changes to the estimate, oldest first. Each entry gives when the change happened, what changed
and why. The tables above always show the current estimate.

### 2026-10-01 09:19 — `aggregate_all_llm_llm_p_value_outputs` had never finished

In the 2026-09-30 run, one `compute_llm_llm_hypergeometric_p_value` job wrote its output at 19:22
but its process never exited, so the run was stuck for about 14 h and then failed on 2026-10-01
at 09:19. The rule's duration was therefore only a guess (~15 min, assuming it costs about as
much as `aggregate_all_p_value_outputs`). A hung job like that one is not included in the
estimate.

### 2026-10-01 09:37 — `aggregate_all_llm_llm_p_value_outputs` can run

The restart at 09:20 failed in `aggregate_all_llm_llm_p_value_outputs` itself, with exit status
126: its 26,000 input paths made a 4 MB command line, above Linux's 2 MB limit. The rule now
passes them through an argument file (TODO entry S33), so it can run. No duration changed.

### 2026-10-01 13:55 — `aggregate_all_llm_llm_p_value_outputs` measured: 4 h 10 min

The first complete run of the rule, on node5 (09:45:33–13:55:48, log
`.snakemake/log/2026-10-01T094228.002030.snakemake.log`), took 4 h 10 min, not the ~15 min
guessed above. It handled the 11,184 results one at a time on one core, about 1.4 s each, most of
it reading the 40-million-row relabelled files of Caption Scene and NSD.

### 2026-10-01 16:40 — both aggregation rules made faster (TODO entry S34)

Both `aggregate_all_p_value_outputs` and `aggregate_all_llm_llm_p_value_outputs` now skip a
redundant duplicate check and process the results with 4 worker processes (`threads: 4`). On the
frontend, under heavy load from other users, the LLM-brain summary went from 23 min to 6 min,
and a 180-result LLM-LLM sample from 4.5 min to 2.4 min, with identical output. The new node5
durations are estimates until the next run measures them: ~5 min (was 16 min) and ~1 h, 1–2 h
(was 4 h 10 min). With the measured 4 h 10 min replacing the ~15 min guess and then S34, the
whole run is ~26 h instead of ~25 h; the final aggregation stage is ~1.5 h instead of ~0.5 h.

### 2026-10-01 20:53 — S34 aggregation durations measured on node5

The first run with the S34 code (log `.snakemake/log/2026-10-01T195630.133465.snakemake.log`)
replaced the estimates of the entry above with measurements: `aggregate_all_llm_llm_p_value_outputs`
took 50 min 35 s (19:59:22–20:49:57; was 4 h 10 min) and `aggregate_all_p_value_outputs` 3 min 16 s
(20:49:57–20:53:13; was 16 min). The final aggregation stage is ~1 h instead of the estimated
~1.5 h; the total stays at ~26 h.


---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-01, Claude Opus 5.5: replaced the S34 duration estimates with the node5 measurements of the 19:56 run, after the developer reported that the run had completed.*
- *Edit history: see [`docs/changelog/`](../changelog/).*
- *Review status: not yet reviewed by the developer.*
