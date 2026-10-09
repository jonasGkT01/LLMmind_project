# Clean run duration: how long a full run takes, rule by rule

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../AI_USAGE.md).*

This page estimates how long a **clean run** of the whole workflow takes (every output rebuilt,
e.g. `snakemake --forceall`). It assumes the usual command on **node5** (1× RTX A5000 24 GB,
251 GB RAM):

```bash
snakemake --use-conda --cores 4 --resources gpu=1
```

**Short answer: about 31 hours (29–34 h) if the models are already in `resources/models/`, and
about 1.5 h more if they have to be downloaded.** Almost every figure is measured on node5; the
critical path is `assemble_nsd_bold` (18.6 h) running next to the Caption Scene per-run
extraction (about 50 job-hours).

## 1. Where the numbers come from

- **Job counts**: dry run of the workflow, `snakemake -n --forceall` (about 40,900 jobs before
  checkpoints), plus the jobs added by the caption_scene checkpoint (8 subjects, 795 runs with
  retained events, 1,000 stimuli).
- **Durations**: the start and `Finished jobid` timestamps of every job in the two node5 runs
  that together rebuilt the whole workflow:
  - `.snakemake/log/2026-10-05T094911.730005.snakemake.log` (2026-10-05 09:49 – 2026-10-06 09:52):
    embeddings, the model–model analyses, narratives, nature_stories, the NSD and Caption Scene
    manifests, and the model–brain analyses of narratives and nature_stories;
  - `.snakemake/log/2026-10-06T101126.178941.snakemake.log` (2026-10-06 10:11 – 2026-10-07 06:25):
    `assemble_nsd_bold`, the Caption Scene registration and extraction, the model–brain analyses
    of NSD and Caption Scene, all aggregations and the plots.

  Rules that neither run executed (model downloads and a few small narratives and nature_stories
  preparation rules) keep the figures of the latest earlier run that executed them, given in the
  "Measured in" column. Where the two runs executed most but not all of a rule's jobs (for
  example 92 of 100 `get_embeddings` jobs), "Total" is scaled to the full job count.
- Durations are wall-clock seconds per job at 1 s resolution. They include conda activation and
  were measured while up to 4 jobs (and the 4 worker processes of `assemble_nsd_bold`) were
  running at the same time.
- "Total" is the job count × the mean duration, i.e. job-hours of work, not elapsed time.
  Section 3 turns job-hours into elapsed time.

## 2. Per-rule durations

Times are given in seconds (s), minutes (min) or hours (h). "Median" and "max" are per job.
"10-05" and "10-06" stand for the two runs of section 1.

### 2a. Model downloads and embeddings

| Rule | Jobs | Median | Max | Total | Measured in |
|---|---:|---:|---:|---:|---|
| `download_pretrained_llm` | 38 | 8.6 min | 17 min | ~5.8 h | 2026-09-29 |
| `get_embeddings` (GPU, one at a time) | 100 | 81 s | 27.8 min | ~4.4 h | 10-05 (92 jobs) |
| `compute_llm_nearest_neighbours` | 100 | 2 s | 6 s | 4 min | 10-05 (95 jobs) |

`download_pretrained_llm` runs only for models that are missing from `resources/models/`. It is
limited by network speed (the 10-05 run downloaded only 5 small models, 45 s each).
`get_embeddings` depends mostly on model size and on the length of the stimuli. The slowest jobs
are the 4-bit 27–31B models: `gemma2_27b` (13–28 min, longest on nature_stories),
`gemma4_31b` (7.5–15 min) and `gemma3_27b` (8.7–11 min). The 8-bit 9–13B models take 4–7.5 min,
and the smaller models take at most about 2 min.

### 2b. Brain data processing

| Rule | Jobs | Median | Max | Total | Measured in |
|---|---:|---:|---:|---:|---|
| **NSD** | | | | | |
| `export_nsd_stimuli` | 1 | 7.9 min | | 7.9 min | 10-05 |
| `make_nsd_manifest` | 1 | 6.5 min | | 6.5 min | 10-05 |
| `write_nsd_parcel_manifest` | 1 | 24 s | | 24 s | 10-05 |
| `assemble_nsd_bold` (4 worker processes) | 1 | 18.6 h | | 18.6 h | 10-06 |
| `write_nsd_isc_manifest` | 1 | 11 s | | 11 s | 10-05 |
| `compute_nsd_isc` | 1 | 4.0 min | | 4.0 min | 10-06 |
| **caption_scene** | | | | | |
| `make_caption_scene_manifest` (checkpoint) | 1 | 2.2 h | | 2.2 h | 10-05 |
| `fetch_mni_template` | 1 | 12 s | | 12 s | 10-05 |
| `register_caption_scene_t1w` (4 threads) | 8 | 3.2 min | 3.6 min | 26 min | 10-06 |
| `compute_caption_scene_sampling_coordinates` | 8 | 32 s | 39 s | 4 min | 10-06 |
| `extract_caption_scene_run_parcels` | 795 | 3.7 min | 5.5 min | 49.9 h | 10-06 |
| `extract_caption_scene_parcels` (collects the run flags) | 1 | <1 s | | <1 s | 10-06 |
| `compute_caption_scene_isc` | 1,000 | 1 s | 3 s | 15 min | 10-06 |
| `write_caption_scene_stimuli_transcripts` | 1 | 6 s | | 6 s | 10-05 |
| `finish_caption_scene_isc` | 1 | 1 s | | 1 s | 10-06 |
| **narratives** | | | | | |
| `rename_narratives_stimuli_transcipts` | 1 | 1 s | | 1 s | 2026-06-19 |
| `write_narratives_problematic_stimuli` | 1 | 22 s | | 22 s | 2026-10-02 |
| `write_narratives_parcel_manifest` | 1 | 9 s | | 9 s | 10-05 |
| `extract_narratives_parcels` | 1 | 89 min | | 89 min | 10-05 |
| `write_narratives_isc_manifest` | 1 | 4 s | | 4 s | 10-05 |
| `compute_narratives_isc` | 1 | 32 s | | 32 s | 10-05 |
| `mark_narratives_isc_done` | 1 | <1 s | | <1 s | 10-05 |
| **nature_stories** | | | | | |
| `write_nature_stories_excluded_stimuli` | 1 | 15 s | | 15 s | 2026-10-02 |
| `convert_nature_stories_textgrids` | 1 | 11 s | | 11 s | 2026-10-02 |
| `verify_nature_stories_stimuli` | 1 | not measured | | <1 min (guess) | — |
| `write_nature_stories_parcel_manifest` | 1 | 5 s | | 5 s | 10-05 |
| `extract_nature_stories_parcels` | 1 | 32 min | | 32 min | 10-05 |
| `write_nature_stories_isc_manifest` | 1 | 10 s | | 10 s | 10-05 |
| `compute_nature_stories_isc` | 1 | 6 s | | 6 s | 10-05 |
| `mark_nature_stories_isc_done` | 1 | <1 s | | <1 s | 10-05 |
| **ISC nearest neighbours (all 4 datasets)** | | | | | |
| `create_isc_manifest` (checkpoint) | 4 | 1 s | 8 s | 11 s | 10-05, 10-06 |
| `create_isc_dataframe` | 4 | 1 s | 4 s | 7 s | 10-05, 10-06 |
| `compute_isc_nearest_neighbours` | 4 | 2 s | 3 s | 9 s | 10-05, 10-06 |

`assemble_nsd_bold` took 11.4 h when it ran alone on all 4 cores (2026-09-24) and 18.6 h on
10-06, when no rule reserved cores any more and 3 `extract_caption_scene_run_parcels` jobs ran
next to it the whole time. Both rules read large BOLD files, so they slow each other down. The
rules marked "guess" only read or write small tables.

### 2c. Model–brain alignment and statistics

| Rule | Jobs | Median | Max | Total | Measured in |
|---|---:|---:|---:|---:|---|
| `compute_llm_mind_alignment_score` | 612 | 2 s | 7 s | 22 min | 10-05, 10-06 |
| `relabel_llm_similarity_and_compute_relabelled_llm_alignment_score` | 300 | 13 s | 2.3 min | 52 min | 10-05, 10-06 |
| `compute_empirical_p_value` | 612 | 4 s | 35 s | 36 min | 10-05, 10-06 |
| `compute_hypergeometric_p_value` | 612 | 2 s | 6 s | 16 min | 10-05, 10-06 |
| `aggregate_all_p_value_outputs` | 1 | 4.1 min | | 4.1 min | 10-06 |
| `compute_spearman_alignmentwith_empirical_p_value` | 300 | 1.7 min | 3.9 min | 6.1 h | 10-05, 10-06 |
| `aggregate_all_spearman_alignment_scores` | 1 | 3 s | | 3 s | 10-06 |

The NSD and Caption Scene jobs (1,000 stimuli) take most of this time: their Spearman jobs take
about 2 min each, against a few seconds for narratives and nature_stories.

### 2d. Model–model alignment and statistics

| Rule | Jobs | Median | Max | Total | Measured in |
|---|---:|---:|---:|---:|---|
| `compute_llm_llm_alignment_score` | 8,802 | 2 s | 1.6 min | 3.9 h | 10-05 |
| `relabel_llm_similarity_and_compute_relabelled_llm_llm_alignment_score` | 4,038 | 13 s | 2.3 min | 10.6 h | 10-05 |
| `compute_llm_llm_empirical_p_value` | 8,802 | 3 s | 11 s | 7.7 h | 10-05 |
| `compute_llm_llm_hypergeometric_p_value` | 8,802 | 1 s | 13 s | 3.2 h | 10-05, 10-06 |
| `aggregate_all_llm_llm_p_value_outputs` | 1 | 2.1 h | | 2.1 h | 10-06 |

`aggregate_all_llm_llm_p_value_outputs` took 51 min on 2026-10-01, when it ran on its own; on
10-06 it ran next to the Caption Scene extraction and `assemble_nsd_bold`.

### 2e. Plots

| Rule | Jobs | Median | Max | Total | Measured in |
|---|---:|---:|---:|---:|---|
| `plot_concept_alignment_scatterplot` | 24 | 2 s | 3 s | 1 min | 10-06 |
| `plot_concept_alignment_enrichment_scatterplot` | 24 | 10 s | 27 s | 6 min | 10-06 |
| `plot_brain_model_alignment_lineplot` | 24 | 2 s | 3 s | 1 min | 10-06 |
| `plot_brain_model_alignment_enrichment_lineplot` | 24 | 10 s | 26 s | 6 min | 10-06 |
| `plot_alignment_heatmap` | 24 | 4 s | 21 s | 4 min | 10-05, 10-06 |
| `plot_empirical_p_value_heatmap` | 24 | 4 s | 8 s | 2 min | 10-06 |
| `plot_spearman_alignment` | 12 | 4 s | 7 s | 1 min | 10-05, 10-06 |

## 3. From job-hours to elapsed time

The whole run is about **115 job-hours** of work (about 121 with downloads): 18.6 h of
`assemble_nsd_bold` and about 96 job-hours of everything else, half of it the Caption Scene
per-run extraction. With 4 job slots, it cannot take less than about 30 h:

1. **`assemble_nsd_bold` runs 4 worker processes** for 18.6 h but counts as one job, so 3 other
   jobs run next to it. It can start a few minutes into the run, after the NSD manifests.
2. **The other jobs keep 3 slots busy while it runs** (about 56 job-hours, most of it the
   Caption Scene extraction, which can start once its manifest is written after about 2.5 h),
   and all 4 slots afterwards: the 10-06 run averaged 4.0 jobs in parallel, and the first 4.7 h
   of the 10-05 run 3.8.
3. **`get_embeddings` runs one job at a time** (`resources: gpu=1`). Its 4.4 h overlap with the
   CPU jobs.

| Stage | Elapsed time |
|---|---:|
| Model downloads (only if `resources/models/` is empty; 4 at a time) | ~1.5 h |
| `assemble_nsd_bold`, with 3 other jobs next to it (Caption Scene extraction, embeddings, narratives, nature_stories, part of the model–model statistics) | 18.6 h |
| Remaining alignment, statistics and plots (~40 job-h at ~3.8 in parallel) | ~11 h |
| Final aggregation steps (one job at a time at the end) | ~0.5–2 h |
| **Total, models already downloaded** | **~31 h (29–34 h)** |
| **Total, models downloaded too** | **~32.5 h** |

As a check against real runs: the 10-05 run did 38.5 job-hours in 15.3 h (from 17:17, three hung
jobs held cores, so it averaged only 1.9 jobs in parallel after the embeddings), and the 10-06 run
did 80.1 job-hours in 20.2 h (4,195 jobs, completed). Run as two parts they took 35.5 h, the
upper end of the range.

## 4. How to update these numbers

Each `.snakemake/log/*.snakemake.log` written on node5 names the host in its first lines
(`host: node5`; `Host: node5` in the header of Snakemake 9 logs). For every job
it prints a `[timestamp]` line followed by `rule <name>:` (or `localrule`, `checkpoint`) and
`jobid: <n>`, and later a `[timestamp]` line followed by `Finished jobid: <n> (Rule: <name>)`.
Pairing the two timestamps by job id gives each job's duration; a job with no `Finished` line
failed or hung. `snakemake -n --forceall` prints the job count per rule.

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

### 2026-10-07 09:10 — measured on two node5 runs that rebuilt everything: ~32 h

The tables now come from the runs of 2026-10-05 09:49 and 2026-10-06 10:11, which together
executed every job of the workflow (the second one completed: 4,195 jobs in 20.2 h). The total
went from ~29 h (27–34 h) to ~32 h (30–35 h), and from about 69 to about 119 job-hours:

- **Caption Scene per-run extraction measured:** `extract_caption_scene_run_parcels` takes
  3.7 min per run, not the ~30 s estimated from the frontend tests, and runs for the 795 runs
  with retained events, not for all 1,664 BOLD runs: 49.9 job-hours instead of ~14. The
  registration (3.2 min per subject), sampling coordinates, MNI template and collecting rules
  were measured for the first time.
- **`assemble_nsd_bold` sharing the CPUs:** 18.6 h with 3 extraction jobs next to it, against
  11.4 h alone; it is now the critical path, with the Caption Scene extraction alongside it.
- **Model-side rules:** `get_embeddings` 4.4 h (was 3.2 h; `gemma2_27b` on nature_stories took
  28 min), `compute_llm_llm_alignment_score` 4.9 h (was 3.7 h), the relabelled LLM-LLM null
  10.6 h (was 9.8 h); `aggregate_all_llm_llm_p_value_outputs` 2.1 h next to other jobs (51 min
  alone).
- **Section 3** now builds the elapsed time around `assemble_nsd_bold` with 3 jobs next to it,
  instead of the earlier sum of stages.

### 2026-10-08 09:43 — ISC reliability rules removed

The rows of `write_caption_scene_isc_manifest`, `compute_isc_reliability` and
`aggregate_isc_reliability` were removed with the rules (about 7 min in all on the 10-05/10-06
runs). The totals above are rounded to the hour and are not changed by this.

### 2026-10-08 09:46 — three neighbourhood sizes instead of four: ~31 h

`caption_scene` and `nsd_data` went from `number_of_neighbours: [5, 25, 50, 100]` to
`[5, 25, 125]`. The job counts of the k-dependent rules were scaled to the counts of a dry run
(`compute_llm_mind_alignment_score` and its two p-value rules 768 → 612, the three model–model
rules 11,184 → 8,802, each brain-model plot rule 30 → 24), keeping the measured per-job durations;
the relabelling rules run once per largest k and keep their counts. The work falls by about 4
job-hours, almost all in the stage after `assemble_nsd_bold`: ~31 h (29–34 h) instead of ~32 h.
The per-job durations at k = 125 are not measured yet.

### 2026-10-09 09:40 — hung jobs no longer expected

The summary said that the estimate leaves out the time lost when a job hangs after writing its
output. The cause of those hangs (reading parquet files through a Python file object, which could
deadlock the process at exit) was fixed, so the sentence was removed. No duration changed.
