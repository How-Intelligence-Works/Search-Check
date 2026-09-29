# Pre-release peer review — v0.1.0a1

This audit was performed before packaging the GitHub and Hugging Face releases.

## Corrected before release

1. **Deduplication was missing.** Added conservative DOI-first / title+year+first-author deduplication, full occurrence provenance, and a human-review file for ambiguous title+year collisions.
2. **Conflicting DOIs could have been collapsed by bibliographic similarity.** The deduplicator now refuses that auto-merge.
3. **Benchmark sensitivity denominator was methodologically wrong.** Unknown-indexing and verified-not-indexed anchors are no longer counted in the sensitivity denominator. Sensitivity is computed only from recovered + verified-indexed-but-missed anchors.
4. **Weighted partial relevance was labelled precision.** Outputs now report strict precision, broad precision, and a separately named weighted relevance yield.
5. **OpenAlex-style display-name authors could fail title+author+year anchor matching.** First-author surname normalization now handles both `Surname, Given` and display-name forms.
6. **Repeated runs could overwrite exports and make the log point ambiguously at current data.** Raw exports are timestamped and the log records a UTC run ID and absolute export path.
7. **A failed latest rerun could silently fall back to an older successful export.** Anchor analysis now treats a failed latest run as unavailable rather than substituting stale results.
8. **Summary could hide failed source runs.** The latest run per query/database is now represented even when it failed.
9. **Benchmark linkage by author surname alone was ambiguous.** `anchor_ids` is now supported and preferred, while the legacy author-surname field remains compatible.
10. **Generic projects could not express database-specific indexing verification cleanly.** Benchmark columns such as `indexed_in_pubmed` and `indexed_in_europe_pmc` are now recognized when the database is declared verified in project settings.
11. **Public web execution needed safe ZIP handling.** The Hugging Face app rejects path-traversal ZIP members and is designed around download-and-retain outputs rather than permanent project storage.

## Tests performed

- Python compilation across the GitHub and Hugging Face packages.
- Editable local package installation using the existing environment.
- Synthetic unit tests for DOI deduplication, conflicting-DOI non-merging, provenance retention, and display-name benchmark matching.
- Hugging Face app import and project-template ZIP generation.

## Remaining limitations that are intentionally not hidden

- Live scholarly API calls could not be executed in the packaging environment because outbound DNS/network access is unavailable there. Connector translations remain versioned and `PILOT-UNTESTED` where appropriate; live smoke tests are still required before formal review use.
- Gated connectors (e.g. Scopus, Web of Science, Embase, Lens/BASE depending on access) require the researcher's own entitlement/credentials and cannot be certified without those credentials.
- Deduplication is deliberately conservative and is not a substitute for human adjudication of ambiguous bibliographic identities.
- The web alpha is job/session oriented, not a multi-user persistent project-management system.
