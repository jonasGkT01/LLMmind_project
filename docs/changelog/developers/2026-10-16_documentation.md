# 2026-10-16 — developer changelog

> *Written with AI assistance (Claude Code). See [`docs/AI_USAGE.md`](../../AI_USAGE.md).*

Changes made on this day, in order:

- Limitation of the group-level language region documented (documentation)

---

## 12:57 — Limitation of the group-level language region documented

Kind: documentation

`docs/reference/brain_regions.md`, section 5 ("Interpretation"), has a new point "Group atlas and
individual language cortex". The language region (`atlas: regions: language`) is the Kong 2022
group-level `Language` + `Aud` parcels; language cortex varies in location across individuals far
more than visual cortex, and subject-specific localiser regions are more selective than group
regions (Fedorenko et al. 2010, J Neurophysiol 104:1177–1194, doi:10.1152/jn.00032.2010). None of
the datasets has a language localiser. Consequences documented: a null result in the language
region is ambiguous; the visual-vs-language comparison is confounded by atlas fit; the mismatch
also lowers the leave-one-out ISC of those parcels. No code, config or result changed.

### Context

- Request: a collaborator proposed further region analyses (language-only and auditory-only
  parcels, the complementary 183 parcels, random parcel sets as a reference) and then pointed out
  the individual variability of language cortex, citing Fedorenko et al. 2010. The developer asked
  to record the analyses as suggestions (SUGGESTIONS entries I14–I16) and to document the caveat.
- Files changed: `docs/reference/brain_regions.md`, `docs/AI_USAGE.md`.
- Verification: article metadata and abstract from Crossref (the journal page refused the
  request; the full text was not read). Mean ISC per parcel set computed with numpy/pandas from
  `results/mind/*/isc_dataframe.parquet` (Narratives: language 0.234, auditory 0.410).
