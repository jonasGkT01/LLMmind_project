# 2026-09-21 — Small cleanup to the alignment plotting scripts

## What changed

We tidied up the two scripts that generate the Spearman alignment plot and
the concept-alignment enrichment plot. This was a behind-the-scenes cleanup,
not a change to how the analysis works.

## What this means for you

- **No change to your results.** The plots you generate, and the summary
  numbers printed alongside them (n, min, median, max, etc.), look exactly
  the same as before.
- The code behind these two plots is now easier to maintain, which reduces
  the chance of the two plots' summary output drifting out of sync in future
  updates.

## Action needed

None. You can keep using these plotting scripts exactly as before.
