# Search Validator

**Search Validator** is an open-source, benchmark-driven engine for testing whether a literature-search strategy actually retrieves the literatures it is intended to represent across the databases in which it will be executed.

It separates the reusable engine from each study's configuration. A project supplies registered queries, source routes, and (optionally) a benchmark corpus; the engine executes and logs database-specific searches, checks benchmark recovery, creates a reproducible manual relevance sample, deduplicates the retrieved corpus, and produces auditable diagnostics.

## What v0.1 alpha does

- Versioned connectors for OpenAlex, PubMed, Europe PMC, ERIC, OpenAIRE, CORE, Semantic Scholar, World Bank Documents & Reports, DOAJ, RePEc, BASE, Lens, Scopus, Web of Science, and Embase.
- Keeps conceptual queries separate from database-specific translations and logs the exact executed query.
- Benchmark recovery by DOI first, then normalized title + first author + year.
- Calculates benchmark sensitivity **only when indexing status is verified for that database**; unknown indexing is not silently counted as a miss.
- Reproducible first-N + fixed-seed random-N sample for human relevance coding.
- Reports strict precision, broad precision, and a separately labelled weighted relevance yield.
- Conservative cross-database deduplication with complete retrieval provenance.
- HTML validation report plus CSV audit trail.

## Deduplication policy

Automatic identity merges use this hierarchy:

1. exact normalized DOI; or
2. normalized title + publication year + first-author surname, **unless the records carry conflicting non-empty DOIs**.

Title + year alone is never treated as sufficient identity evidence. Such collisions are written to `dedup_review_candidates.csv` for human adjudication. `dedup_provenance.csv` preserves every retrieved occurrence and the query/database that produced it.

## Project format

Copy `examples/paper2_example/` and edit:

- `queries.csv` — `query_id, family, substream, text, anchors, anchor_ids, routes`. `anchor_ids` is preferred for unambiguous benchmark linkage; legacy author-surname `anchors` remains supported.
- `benchmark_corpus.csv` — benchmark metadata. Database-specific indexing columns can be named e.g. `indexed_in_openalex`, `indexed_in_pubmed`, or the legacy `indexed_in_openalex? (Y/N)`.
- `project.yml` — runtime settings and any source credentials you already possess.

## Install and run

```bash
python -m pip install -e .
search-validator --project examples/paper2_example --run Q02.2
search-validator --project examples/paper2_example --deduplicate
search-validator --project examples/paper2_example --anchor-matrix
search-validator --project examples/paper2_example --sample
# Manually code relevance in results/coding_sample.csv
search-validator --project examples/paper2_example --summarize
search-validator --project examples/paper2_example --report
```

For a full registered run, replace `Q02.2` with `all`.

## Output files

- timestamped raw query × database exports
- `search_log.csv` with run ID, exact translated query, translation version/status, counts, truncation, and errors
- `deduplicated_records.csv`
- `dedup_provenance.csv`
- `dedup_review_candidates.csv`
- `anchor_matrix.csv`
- `coding_sample.csv`
- `pilot_summary.csv`
- `validation_report.html`

## Methodological safeguards

Relevance coding is deliberately not automated. The software can retrieve, normalize, sample, match and report; the researcher remains responsible for relevance judgments and KEEP/REVISE/SPLIT/MERGE decisions.

Database query languages are not assumed equivalent. Connectors retain a translation version and status. A connector marked `PILOT-UNTESTED` must be empirically checked before its results are treated as validated for a formal review.

Several connectors require external credentials or institutional entitlement. The software does not grant or bypass access. Public deployments should not be used to submit confidential API credentials unless the deployment is controlled by the researcher.

## Current maturity

`0.1.0a1` is a public-alpha candidate, not a claim of production maturity. The core engine has synthetic tests for deduplication and benchmark matching, but source adapters still require live smoke testing against their upstream APIs. API behavior can change independently of this package.

## License

MIT.
