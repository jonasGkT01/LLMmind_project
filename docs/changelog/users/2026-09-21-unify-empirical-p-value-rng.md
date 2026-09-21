# 2026-09-21 — Consistency fix for how significance tests generate randomness

## What changed

The pipeline computes two kinds of significance tests by comparing your
real results to many randomly shuffled ("relabelled") versions: one for how
well a model's representations align with brain activity, and one for how
well two models' representations align with each other. Under the hood,
these two tests were generating their random shuffles in two different
ways. We found no evidence this made either test wrong, but there was no
good reason for them to differ, so both now generate their random shuffles
using the same method.

## What this means for you

- The brain-model alignment test's results (per-concept and per-model
  p-values) are **unchanged** — you don't need to do anything for those.
- The model-model alignment test's results will change slightly the next
  time you regenerate them, because its random shuffles are now drawn
  differently. This does not mean anything was wrong with the old numbers —
  a significance test based on random shuffling is expected to give
  slightly different p-values if you draw a different set of random
  shuffles, the same way re-rolling dice gives a different sequence each
  time. The overall conclusions (which model pairs are/aren't
  significantly aligned) should not change.
- As a reminder (unchanged from before): only the overall alignment between
  two models is tested for significance — there isn't a separate
  significance test for each individual concept in the model-model
  comparison.

## Action needed

If you rely on the model-model alignment p-values
(`dataset-*_model-*_model-*_empirical_*-alignment_score_*NN.p_value.tsv`),
regenerate them by rerunning the pipeline so they reflect the corrected,
consistent random-shuffling method. No action is needed for the brain-model
alignment results.
