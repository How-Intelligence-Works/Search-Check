# Validation and connector status

Search Check separates **software validation** from **live connector compatibility**.

## Core software

The repository includes synthetic tests for core behaviors such as conservative deduplication and benchmark matching. These tests can be run locally with:

```bash
python -m pytest
```

A passing core test suite does not certify any external database or API.

## Connector status

All 15 connectors are retained in the alpha:

- OpenAlex
- PubMed
- Europe PMC
- ERIC
- OpenAIRE
- CORE
- Semantic Scholar
- World Bank Documents & Reports
- DOAJ
- RePEc
- BASE
- Lens
- Scopus
- Web of Science
- Embase

Each connector carries version/status metadata. In this release, `PILOT-UNTESTED` means:

> the connector implementation is included, but its live behavior against the upstream service has not been certified for this release.

It does **not** mean that the connector is invalid, deprecated, or scheduled for removal.

## Why status is release-specific

External scholarly services change independently of Search Check. API endpoints, authentication, institutional entitlements, query syntax, response schemas, rate limits, and service policies may change at any time. A connector that works in one release can later require maintenance.

For a formal research use, the relevant evidence is therefore the recorded run itself: whether the request succeeded, what query was executed, what the source returned, and whether any error or truncation was recorded.

Search Check should expose failures rather than silently substituting stale or unrelated results.

## Public-alpha meaning

Public alpha means the software is available for inspection and real-world testing while compatibility and interaction details continue to be refined. It is not a scientific certification of a search strategy or of any upstream database.
