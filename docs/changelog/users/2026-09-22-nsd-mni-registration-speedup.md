# 2026-09-22 — NSD brain-data processing is dramatically faster

## What changed

The step that prepares NSD (Natural Scenes Dataset) brain scans for
analysis — registering each fMRI scan into a standard brain space (MNI) so
scans from different people can be compared — was taking an extremely long
time to run. We found why and fixed it.

The step processes each individual viewing of an image (there are
hundreds of thousands of these across all 8 participants) one at a time.
For every single one, it was reloading the same reference file from disk
and rebuilding the same internal lookup table from scratch, even though
that file and table never change for a given participant. That repeated,
unnecessary work was the vast majority of the total run time — not the
actual brain-data processing itself.

Two fixes:

- That reference file and lookup table are now loaded once per participant
  and reused for all of that participant's scans, instead of being
  reloaded from scratch for every single viewing.
- This step can now also use multiple processor cores at once to work on
  several scans in parallel, instead of handling them one after another.

## What this means for you

- Preparing NSD data should now take a small fraction of the time it used
  to.
- The results are unchanged — we checked that the new, faster version
  produces byte-for-byte identical output to the old version. Nothing about
  the brain-data analysis itself changed.
- This step will now use more CPU cores than before while it runs (up to
  however many you give the pipeline via `--cores <N>` when you launch it).
  If you're running this alongside other work on a shared machine, keep
  that in mind — the more cores you allow, the faster this step finishes,
  but the more of the machine it will use while it's running.

## Action needed

None. Existing NSD outputs remain valid — you don't need to rerun anything
for correctness. If you do rerun the NSD processing step, expect it to
finish much faster than before.
