# Nature Stories stimuli: where the transcripts come from and how they match the fMRI data

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../AI_USAGE.md).*

The Nature Stories inputs come from two separate public releases: the fMRI data from one, the
word-level transcripts from another. This page records where each comes from, how the workflow
uses the transcripts, and the check that both releases describe the same stimuli.

## 1. Sources

| Files | Release | Downloaded by |
|---|---|---|
| `responses/S*_BOLD.hdf`, `responses/run_onsets.json`, `mappers/`, `stimuli/*.wav` | "Nature Story Listening 3T fMRI Data", Huth, de Heer, Deniz, Gong, Gallant, Theunissen (Gallant and Theunissen labs), 11 subjects; G-Node GIN, DOI `10.12751/g-node.t4wew2` | `public_datasets`, rule `download_nature_stories_dataset` |
| `stimuli/textgrids/<story>.TextGrid` | "An fMRI dataset during a passive natural language listening task", LeBel, Wagner, Jain, … Huth, *Sci. Data* 10, 555 (2023); OpenNeuro `ds003020`, DOI `10.18112/openneuro.ds003020.v4.0.0`, folder `derivatives/TextGrids` | `public_datasets`, rule `download_nature_story_stimuli` (`aws s3 cp --no-sign-request` from `s3://openneuro.org/ds003020/derivatives/TextGrids`) |

`ds003020` is a different, later Huth lab dataset (Moth Radio Hour stories, its own subjects). Its
84 stories include all 11 Nature Stories stories. The G-Node archive contains the audio of each
story but no transcript or word alignment, which is why the TextGrids are taken from `ds003020`.

The TextGrids hold a `phone` and a `word` tier. Some are in Praat's long text format and some in
its "chronological" format; `convert_nature_stories_textgrids.py` reads both.

## 2. How the workflow uses them

Rule `convert_nature_stories_textgrids` (script `convert_nature_stories_textgrids.py`) keeps only
the **word sequence** of each story: it takes the `word` tier, drops empty intervals and
non-speech labels (`sp`, `{ns}`, `{br}`, `{lg}`, `{ls}`, `sentence_start`, `sentence_end`), lowercases
the words and writes them, space-separated, to `stimuli/transcripts/<story>.txt`. These transcripts
are the text given to the language models.

The word timings are discarded, and no rule reads the G-Node `.wav` files. The brain side uses
whole stories (see [`fmri_preprocessing.md`](fmri_preprocessing.md)), so nothing aligns individual
words to TRs.

## 3. Check that both releases describe the same stimuli

Done on 2026-10-09 on the downloaded files, with the workflow's own TextGrid parser.

- **TR counts.** `ds003020/derivatives/respdict.json` gives the number of TRs recorded for each
  story. The G-Node data trim 10 TRs at each end of each story before z-scoring, so a G-Node story
  length plus 20 should equal the `ds003020` count.
- **Durations.** The end time (`xmax`) of each TextGrid was compared with the duration of the
  matching G-Node `.wav` file (mapping in `run_onsets.json`, `stimuli_mapping`).

| Story | G-Node TRs + 20 | `ds003020` TRs | G-Node `.wav` (s) | TextGrid end (s) |
|---|---|---|---|---|
| alternateithicatom | 363 | 363 | 706.7 | 706.7 |
| avatar | 387 | 387 | 754.3 | 754.2 |
| howtodraw | 374 | 374 | 728.3 | 728.3 |
| legacy | 420 | 420 | 820.0 | 820.0 |
| life | 450 | 450 | **808.8** | **880.3** |
| myfirstdaywiththeyankees | 378 | 378 | 736.9 | 736.9 |
| naked | 442 | 442 | 865.0 | 865.0 |
| odetostepfather | 424 | 424 | 828.1 | 828.1 |
| souls | 375 | 375 | 730.0 | 730.0 |
| undertheinfluence | 324 | 324 | 627.7 | 627.7 |
| wheretheressmoke (test) | 311 | 311 | 601.9 | 601.9 |

G-Node lengths are those of the corrected `new_run_onsets.json` (see the
[README](../../README.md#input-files-not-produced-by-the-download)).

Findings:

- **Same stimulus versions.** All 11 TR counts agree exactly, and for 10 stories the TextGrid ends
  within 0.01 s of the G-Node audio. Both releases scanned the same recordings of the stories.
- **The corrected run onsets are confirmed independently.** The lengths in `new_run_onsets.json`
  match `ds003020`; those of the archive's original `run_onsets.json` do not (alternateithicatom
  365, avatar 386, howtodraw 373 after adding 20).
- **The G-Node audio of `life` is about 71 s short.** The scan of `life` lasts 450 TRs × 2 s =
  900 s. Like every other story, its TextGrid ends about 20 s before the end of the scan, while
  `train_04.wav` stops at 808.8 s. The TextGrid, and so the transcript, matches what was scanned;
  the G-Node `.wav` file is truncated or a different cut.
- **No effect on the results.** The workflow reads neither the timings nor the `.wav` files.

**Not verified:** what the missing 71 s of the `life` audio contain, and whether the TextGrid words
match the audio word for word (only durations were compared).

## Changes

### 2026-10-09 11:35 — page created

New page recording where the Nature Stories TextGrids come from (OpenNeuro `ds003020`, a separate
release from the G-Node fMRI data), how the workflow uses them, and the check that both releases
describe the same stimuli, including the truncated G-Node `life` audio. Written on the developer's
request after the check was run.
