# Clean run duration: how long a full run takes, rule by rule

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../AI_USAGE.md).*

This page estimates how long a **clean run** of the whole workflow takes (every output rebuilt,
e.g. `snakemake --forceall`). It assumes the usual command on **node5** (1× RTX A5000 24 GB,
251 GB RAM):

```bash
snakemake --use-conda --cores 4 --resources gpu=1
```

**Short answer: about 29 hours (27–34 h) if the models are already in `resources/models/`, and
about 1.5 h more if they have to be downloaded.** The Caption Scene registration to MNI and
per-run extraction have not been measured on node5 yet; their figures are estimates (section 2b).

## 1. Where the numbers come from

- **Job counts**: dry run of the workflow, `snakemake -n --forceall` (about 40,900 jobs before
  checkpoints), plus the jobs added by the caption_scene checkpoint (8 subjects, 1,664 BOLD runs,
  1,000 stimuli).
- **Durations**: the start and `Finished jobid` timestamps of every job in the 328 node5 logs in
  `.snakemake/log/` (up to 2026-10-05 11:05). For each rule, the table
  uses the **most recent run** in which that rule ran, so the figures match the current code as
  closely as possible. Where that run executed only a few of the rule's jobs (the 2026-10-02 and
  2026-10-05 runs for the model rules), the table keeps the last run that executed them all.
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
| `export_nsd_stimuli` | 1 | 7.9 min | | 7.9 min | 2026-10-05 |
| `make_nsd_manifest` | 1 | 6.5 min | | 6.5 min | 2026-10-05 |
| `write_nsd_parcel_manifest` | 1 | 8 s | | 8 s | 2026-09-24 |
| `assemble_nsd_bold` (4 worker processes) | 1 | 11.4 h | | 11.4 h | 2026-09-24 |
| `write_nsd_isc_manifest` | 1 | 9 s | | 9 s | 2026-09-24 |
| `compute_nsd_isc` | 1 | 9.4 min | | 9.4 min | 2026-09-24 |
| **caption_scene** | | | | | |
| `make_caption_scene_manifest` (checkpoint) | 1 | 2.3 h | | 2.3 h | 2026-10-02 |
| `fetch_mni_template` | 1 | not measured | | <1 min (guess) | — |
| `register_caption_scene_t1w` (4 threads) | 8 | ~2–3 min (estimate) | | ~20 min | estimate from the frontend test |
| `compute_caption_scene_sampling_coordinates` | 8 | not measured | | <30 min (guess) | — |
| `extract_caption_scene_run_parcels` | 1,664 | ~30 s (estimate) | | ~14 h | estimate from the frontend test |
| `extract_caption_scene_parcels` (collects the run flags) | 1 | not measured | | <1 min (guess) | — |
| `write_caption_scene_isc_manifest` | 1 | not measured | | <1 min (guess) | — |
| `compute_caption_scene_isc` | 1,000 | 2 s | 7 s | 39 min | 2026-09-24 |
| `write_caption_scene_stimuli_transcripts` | 1 | 13 s | | 13 s | 2026-09-24 |
| `finish_caption_scene_isc` | 1 | 2 s | | 2 s | 2026-09-24 |
| **narratives** | | | | | |
| `rename_narratives_stimuli_transcipts` | 1 | 1 s | | 1 s | 2026-06-19 |
| `write_narratives_problematic_stimuli` | 1 | 22 s | | 22 s | 2026-10-02 |
| `write_narratives_parcel_manifest` | 1 | 9 s | | 9 s | 2026-10-05 |
| `extract_narratives_parcels` | 1 | 98 min | | 98 min | 2026-10-02 |
| `write_narratives_isc_manifest` | 1 | 4 s | | 4 s | 2026-10-05 |
| `compute_narratives_isc` | 1 | 62 s | | 62 s | 2026-06-19 |
| `mark_narratives_isc_done` | 1 | <1 s | | <1 s | 2026-06-19 |
| **nature_stories** | | | | | |
| `write_nature_stories_excluded_stimuli` | 1 | 15 s | | 15 s | 2026-10-02 |
| `convert_nature_stories_textgrids` | 1 | 11 s | | 11 s | 2026-10-02 |
| `verify_nature_stories_stimuli` | 1 | not measured | | <1 min (guess) | — |
| `write_nature_stories_parcel_manifest` | 1 | 5 s | | 5 s | 2026-10-05 |
| `extract_nature_stories_parcels` | 1 | 32 min | | 32 min | 2026-10-05 |
| `write_nature_stories_isc_manifest` | 1 | 10 s | | 10 s | 2026-10-05 |
| `compute_nature_stories_isc` | 1 | 6 s | | 6 s | 2026-10-05 |
| `mark_nature_stories_isc_done` | 1 | <1 s | | <1 s | 2026-10-05 |
| **ISC nearest neighbours and reliability (all 4 datasets)** | | | | | |
| `create_isc_manifest` (checkpoint) | 4 | 2 s | 3 s | 8 s | 2026-09-28 |
| `create_isc_dataframe` | 4 | 2 s | 4 s | 8 s | 2026-09-28 |
| `compute_isc_nearest_neighbours` | 4 | 2 s | 2 s | 6 s | 2026-09-28 |
| `compute_isc_reliability` | 4 | 9 s (1 job) | | ~1 min | 2026-10-05 |
| `aggregate_isc_reliability` | 1 | not measured | | <1 min (guess) | — |

`compute_narratives_isc` failed in the 2026-10-02 run (see the developer changelog of
2026-10-05), so its figure still comes from June 2026. The Caption Scene estimates come from the
frontend tests of 2026-10-02 (registration about 1.5 min per subject with 8 threads; extraction
about 30 s per run, about 16 CPU-hours in total). The rules marked "guess" only read or write
small tables. The single-job rules of NSD and nature_stories took longer on 2026-10-02 and
2026-10-05 than before, probably because they ran next to other disk-heavy jobs.

### 2c. Model–brain alignment and statistics

| Rule | Jobs | Median | Max | Total | Measured in |
|---|---:|---:|---:|---:|---|
| `compute_llm_mind_alignment_score` | 768 | 1 s | 13 s | 18 min | 2026-09-29 |
| `relabel_llm_similarity_and_compute_relabelled_llm_alignment_score` | 300 | 16 s | 24 s | 53 min | 2026-09-29 |
| `compute_empirical_p_value` | 768 | 4 s | 7 s | 41 min | 2026-09-30 |
| `compute_hypergeometric_p_value` | 768 | 1 s | 11 s | 20 min | 2026-09-29 |
| `aggregate_all_p_value_outputs` | 1 | 3.3 min | | 3.3 min | 2026-10-01 |
| `compute_spearman_alignmentwith_empirical_p_value` | 300 | 1.8 min | 2.2 min | 5.2 h | 2026-09-29 |
| `aggregate_all_spearman_alignment_scores` | 1 | 2 s | | 2 s | 2026-09-29 |

### 2d. Model–model alignment and statistics

| Rule | Jobs | Median | Max | Total | Measured in |
|---|---:|---:|---:|---:|---|
| `compute_llm_llm_alignment_score` | 11,184 | 1 s | 8 s | 3.7 h | 2026-09-29 |
| `relabel_llm_similarity_and_compute_relabelled_llm_llm_alignment_score` | 4,038 | 13 s | 17 s | 9.8 h | 2026-09-30 |
| `compute_llm_llm_empirical_p_value` | 11,184 | 3 s | 7 s | 9.6 h | 2026-09-30 |
| `compute_llm_llm_hypergeometric_p_value` | 11,184 | 1 s | 4 s | 4.7 h | 2026-09-30 |
| `aggregate_all_llm_llm_p_value_outputs` | 1 | 51 min | | 51 min | 2026-10-01 |

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

The whole run is about **69 job-hours** of work (about 75 with downloads). It does not simply
take 69/4 h, for three reasons:

1. **`assemble_nsd_bold` runs 4 worker processes** (`number_of_workers`) for 11.4 h.
   Snakemake counts it as one core, so up to 3 other jobs run alongside it and share the CPUs.
   The 11.4 h were measured while it ran alone on all 4 cores; its duration while sharing the
   CPUs has not been measured yet.
2. **`get_embeddings` runs one job at a time** (`resources: gpu=1`). Its 3.2 h mostly overlap with
   the CPU jobs.
3. **The many short alignment and statistics jobs** (about 40,000 jobs of 1–15 s each) averaged
   3.7 jobs in parallel in the runs of 2026-09-28 and 2026-09-29.

| Stage | Elapsed time |
|---|---:|
| Model downloads (only if `resources/models/` is empty; 4 at a time) | ~1.5 h |
| `assemble_nsd_bold` (measured alone on all cores) | 11.4 h |
| Rest of the brain data processing (caption_scene ~6 h: manifest 2.3 h, then ~14 job-h of run extraction 4 at a time; narratives and nature_stories ~2.3 h, in parallel with the caption_scene manifest) | ~6 h |
| Embeddings (GPU); mostly overlap with the stage above | ~0–1 h extra |
| Alignment, statistics and plots (~36 job-h at 3.7 in parallel) | ~10 h |
| Final aggregation steps (one job at a time at the end) | ~1 h |
| **Total, models already downloaded** | **~29 h (27–34 h)** |
| **Total, models downloaded too** | **~30.5 h** |

As a check against real runs: the 2026-09-24 run (mostly brain data processing, including
`assemble_nsd_bold`) took 15.3 h. The 2026-09-29 run (embeddings and all downstream steps,
26,153 jobs) took 7.9 h. The 2026-09-30 run (27,294 jobs, including the new model–model
relabelled null) took 8.8 h before it got stuck on the hung job.

## 4. How to update these numbers

Each `.snakemake/log/*.snakemake.log` written on node5 names the host in its first lines
(`host: node5`; `Host: node5` in the header of Snakemake 9 logs). For every job
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
passes them through an argument file, so it can run. No duration changed.

### 2026-10-01 13:55 — `aggregate_all_llm_llm_p_value_outputs` measured: 4 h 10 min

The first complete run of the rule, on node5 (09:45:33–13:55:48, log
`.snakemake/log/2026-10-01T094228.002030.snakemake.log`), took 4 h 10 min, not the ~15 min
guessed above. It handled the 11,184 results one at a time on one core, about 1.4 s each, most of
it reading the 40-million-row relabelled files of Caption Scene and NSD.

### 2026-10-01 16:40 — both aggregation rules made faster

Both `aggregate_all_p_value_outputs` and `aggregate_all_llm_llm_p_value_outputs` now skip a
redundant duplicate check and process the results with 4 worker processes (`threads: 4`). On the
frontend, under heavy load from other users, the LLM-brain summary went from 23 min to 6 min,
and a 180-result LLM-LLM sample from 4.5 min to 2.4 min, with identical output. The new node5
durations are estimates until the next run measures them: ~5 min (was 16 min) and ~1 h, 1–2 h
(was 4 h 10 min). With the measured 4 h 10 min replacing the ~15 min guess and then the speed-up, the
whole run is ~26 h instead of ~25 h; the final aggregation stage is ~1.5 h instead of ~0.5 h.

### 2026-10-01 20:53 — faster aggregation durations measured on node5

The first run with the faster code (log `.snakemake/log/2026-10-01T195630.133465.snakemake.log`)
replaced the estimates of the entry above with measurements: `aggregate_all_llm_llm_p_value_outputs`
took 50 min 35 s (19:59:22–20:49:57; was 4 h 10 min) and `aggregate_all_p_value_outputs` 3 min 16 s
(20:49:57–20:53:13; was 16 min). The final aggregation stage is ~1 h instead of the estimated
~1.5 h; the total stays at ~26 h.

### 2026-10-05 11:10 — page regenerated for the current workflow: ~29 h

The file was renamed from `2026-10-01_0926_clean_run_duration.md` to `clean_run_duration.md`
(living reference pages carry no date in their name), and the tables were brought up to date with
the workflow and the node5 logs up to 2026-10-05 11:05:

- **Caption Scene (registration to MNI, 2026-10-02):** `split_caption_scene_bold_by_run_manifest` (5.3 h)
  was removed; the new registration and per-run extraction rules add about 15 job-hours, mostly
  `extract_caption_scene_run_parcels` (1,664 runs, ~30 s each, estimated from the frontend tests).
  `make_caption_scene_manifest` took 2.3 h on 2026-10-02 (was 67 min). The Caption Scene stage
  is ~6 h instead of ~3 h.
- **nature_stories:** measured for the first time (2026-10-02 and 2026-10-05): about 33 min in
  total, mostly `extract_nature_stories_parcels` (32 min), instead of the "<1 h" guess.
- **narratives:** `extract_narratives_parcels` took 98 min on 2026-10-02 (was 42 min in June).
- **New rules:** `compute_isc_reliability` and `aggregate_isc_reliability`; about 1 min
  in total.
- **NSD:** `export_nsd_stimuli` and `make_nsd_manifest` took 7.9 and 6.5 min on 2026-10-05 (were
  98 s and 23 s).
- The short answer said ~25 h while section 3 said ~26 h since 2026-10-01 16:40; both now say
  ~29 h (27–34 h), ~30.5 h with downloads.

The Caption Scene figures stay estimates until the rerun started on 2026-10-05 at 09:49 finishes.

### 2026-10-06 10:30 — no rule reserves cores any more

The `threads:` directives were removed from every rule (developer request, 2026-10-06, after the
run of 2026-10-05 stalled: three hung jobs held 3 of the 4 cores and `assemble_nsd_bold` waited
for all 4). The internal worker count now comes from `number_of_workers` (4) in the config:
`assemble_nsd_bold` keeps 4 workers but no longer runs alone, and `register_caption_scene_t1w`
uses 4 threads instead of 8 (it was already capped at 4 by `--cores 4`). The durations are
unchanged until the next run measures them with other jobs sharing the CPUs. Before this change,
`assemble_nsd_bold` reserved all 4 cores (`threads: workflow.cores`) and nothing else ran next to
it, which is why the dataset-processing run of 2026-09-24 averaged only 1.5 jobs in parallel.

### 2026-10-06 16:30 — TODO IDs and dated notes moved out of the body

TODO references were removed from the tables and from this section, the run-specific notes of the
short answer, section 1 and section 3 were rewritten to describe the current state (the
`assemble_nsd_bold` history moved to the entry above), and the AI attribution block was replaced
by the note under the title.
