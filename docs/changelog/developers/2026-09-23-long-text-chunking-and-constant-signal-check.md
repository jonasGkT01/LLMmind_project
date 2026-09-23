# 2026-09-23 — Long-text chunking stops at the end of the text; float32-based constant-signal check in ISC

Follow-up to `2026-09-23-nsd-invalid-coords-and-positive-isc-manifest.md`,
addressing the two code points the external review of commit `60bb6c5` left
open.

## Long-text chunking: no redundant final chunk

- `llm_nearest_neighbours/scripts/get_embeddings.py`, `embed_long_text()`
  - The loop `for start in range(0, n_tokens, step)` kept going after a chunk
    had already reached the end of the text. The extra chunk lay entirely
    inside the previous one. It re-embedded tokens that were already covered
    and gave them extra weight in the length-weighted mean.
  - The loop now breaks once `start + chunk_token_length >= n_tokens`.
- When the old loop over-ran: with `step = chunk_token_length - overlap`, it
  added one redundant chunk exactly when `n_tokens > step` and
  `0 < n_tokens mod step <= overlap`. The CLI default is `--chunk_overlap 256`
  (not overridden by the `get_embeddings` rule), and
  `chunk_token_length = max_length - 1` when the tokenizer has a BOS token.
- Checked by simulating the loop with `chunk_token_length = 511` and
  `overlap = 128` (step 383). The old loop added a redundant chunk for 400,
  511, 800, 894 and 2,000 tokens, but not for 100, 383, 512 or 895. The new
  loop drops exactly that chunk, and every token is still inside some chunk.
- **Impact on existing outputs:**
  - Embeddings change for text stimuli whose token count meets the condition
    above.
  - The `n_chunks` metadata column in `*_embeddings.parquet` goes down by one
    for those stimuli.
  - Stimuli that fit in a single chunk, and all image stimuli, are unchanged.

## ISC: constant-signal detection

- `libraries/fmri_processing.py`
  - The old check was `np.isclose(x, x[0])` with default tolerances
    (`rtol = 1e-5` against the first sample). On raw-scale BOLD, which the
    pipeline does not z-score, a parcel around 1000 varying by less than about
    0.01 was treated as constant and its correlation set to 0.
  - New `is_constant_signal()`: a signal counts as constant when its range
    over time is at most `8 × float32 eps` (about 9.5e-7) times its maximum
    absolute value. In other words, it varies only by float32 rounding noise.
    All-zero and exactly constant parcels are still caught.
  - `compute_leave_one_out_isc()` and `safe_pearsonr()` both use it, so they
    stay equivalent as the docstring says (`safe_pearsonr` is currently not
    called anywhere).
- Verified on synthetic data (8 subjects × 20 TRs):
  - normal-amplitude signals: output identical to the old implementation
    (max abs difference `0.0`);
  - all-zero and exactly constant parcels: still 0;
  - a parcel around 1000 with a shared signal of range about 0.008: the old
    check gave 0, the new one gives ISC 0.94.
- **Impact on existing outputs:** only parcels the old tolerance wrongly
  flagged change. How many there are in the real data has not been checked.

## Rerunning

Both scripts are called from `shell:` rules, so Snakemake will not rerun
them by itself. The NSD and Caption Scene manifests have to be regenerated
anyway (see the previous entry), so ISC is recomputed for those datasets
downstream of that. For Narratives, Nature Stories and the text embeddings,
force the ISC and embedding rules, e.g.:

```bash
snakemake --use-conda --cores <N> --forcerun get_embeddings compute_narratives_isc compute_nature_stories_isc
```

## Not changed

- NSD ISC still treats each presentation as its own observation, including
  repeats by the same subject. This is a deliberate methodological choice.
  The manuscript should report the number of observations and the number of
  distinct subjects separately.

---

*AI disclosure: this changelog entry, and the code changes it describes,
were written by an AI coding assistant.*

- *Tool: Claude Code, VS Code extension.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`, 1M-token context).*
- *Date: 2026-09-23.*
- *Basis: an external review of commit `60bb6c5`, which the assistant first
  checked against the code and the data on disk, then the developer's
  instructions (Jonas Salvalaggio) in the same session.*
- *Verification: only the synthetic checks listed above. No pipeline stage
  was run with the new code, and the effect on the real data was not
  measured.*
- *Review status: not yet reviewed by the developer at the time of writing.*
