# 2026-09-23 — Python bytecode no longer tracked; corrections to the chunking and constant-signal entry

Follow-up to `2026-09-23-long-text-chunking-and-constant-signal-check.md`
(commit `ea9145a`), prompted by an external review of that commit. No
pipeline code changed in this entry.

## Python bytecode removed from Git

- `.gitignore`: the path-specific `workflow/libraries/__pycache__/` rule is
  replaced by repository-wide `__pycache__/` and `*.py[cod]` patterns.
- Removed from the index (and deleted from the working tree), since all
  three were committed by mistake:
  - `workflow/llm_nearest_neighbours/scripts/__pycache__/get_embeddings.cpython-313.pyc` (added in `ea9145a`)
  - `workflow/dataset_processing/nsd_data_dataset/scripts/__pycache__/assemble_nsd_bold.cpython-314.pyc` (added in `12181e1`)
  - `workflow/llm_mind_alignment/scripts/__pycache__/aggregate_all_p_value_outputs.cpython-314.pyc` (added in `29b7cc0`)
- After this change, `git ls-files | grep pycache` returns nothing.
- Why only `workflow/libraries/__pycache__/` should appear during a normal
  run: rules call scripts as `python3 <script>.py` from `shell:`, and CPython
  writes bytecode only for imported modules, never for the `__main__`
  script. The scripts import `libraries/` modules, so that is the only cache
  a pipeline run produces. No file in `workflow/` imports
  `get_embeddings`, `assemble_nsd_bold` or `aggregate_all_p_value_outputs`,
  so their caches came from ad-hoc imports during testing.
  `workflow/envs/LLMmind_project/` also contains caches, but that is the
  conda prefix and was already ignored.

## Corrections to the `ea9145a` changelog entries

The code in `ea9145a` is unchanged. Three statements in its documentation
were inaccurate.

### Which embeddings the chunking fix changes

- The entry said that stimuli fitting in a single chunk are unchanged. That
  is wrong: `get_embeddings.py` routes every text stimulus through
  `embed_long_text()`, whatever its length.
- With `L = chunk_token_length` and the default `--chunk_overlap 256`
  (`step = L - 256`), the old loop started a second chunk at `step` for any
  text with `L - 255 <= n_tokens <= L`, although the first chunk already
  covered the whole text. Checked by simulating both loops: for `L = 511`
  every length from 256 to 511 tokens goes from 2 chunks to 1, and for
  `L = 2047` every length from 1,792 to 2,047.
- So short texts whose length falls in that window change too, along with
  the longer texts described in the original entry. Image stimuli are
  unaffected.

### Overlap weighting

- The final embedding is still the chunk-length-weighted mean of
  overlapping chunks. Tokens in an overlap region contribute to two chunk
  embeddings, and tokens at the start and end of the text to only one. The
  fix removes the redundant final chunk. It does not make every token
  count equally, as the user entry claimed.

### Constant-signal threshold

- `is_constant_signal()` treats a signal as constant when
  `ptp(x) <= 8 * eps(float32) * max|x|`, which is about 9.5e-7 relative. At
  a baseline around 1,000 that is a range of about 0.00095, roughly 16
  float32 ulps. It is a near-constancy tolerance, not a test for
  rounding noise only. A real fluctuation smaller than that is still
  zeroed.
- Leaving the tolerance as it is, or switching to an exact check
  (`np.ptp(x, axis=axis) == 0`), is an open methodological decision. It
  should be made after counting how many parcels the current rule zeroes on
  real processed BOLD, which has not been done yet. An exact check would
  still catch all-zero and exactly constant parcels: the leave-one-out mean
  `y` of identical signals is computed the same way at every time point,
  so it stays exactly flat.
- `README.md` (`dataset_processing/<dataset>/` and `llm_nearest_neighbours/`
  sections) has been updated to match. The `ea9145a` entries are left
  as written, with a note at the top pointing here.

## Still to validate

The review recommends checking regenerated results before changing more
code:

- retained stimulus IDs should agree across the manifests, the ISC outputs
  and the embeddings;
- measure how often the constant-signal rule returns 0 on real data;
- compare the new NSD parcel outputs with the previous extraction method on
  representative presentations.

---

*AI disclosure: this changelog entry, and the changes it describes, were
written by an AI coding assistant.*

- *Tool: Claude Code, VS Code extension.*
- *Model: Claude Opus 5.5 (`claude-opus-5-5`, 1M-token context).*
- *Date: 2026-09-23.*
- *Basis: an external review of commit `ea9145a`, which the assistant
  checked against the source (reading `get_embeddings.py` and
  `fmri_processing.py`, and simulating the old and new chunking loops),
  and the developer's instructions (Jonas Salvalaggio) in the same session.*
- *Verification: `git ls-files` shows no tracked bytecode; the chunk-count
  simulation described above. No pipeline stage was run.*
- *Review status: not yet reviewed by the developer at the time of writing.*
