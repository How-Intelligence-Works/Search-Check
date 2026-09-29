"""
Every connector module exposes the same four names, so the runner never
needs a special case per database:

    NAME             — display name used in logs and exported rows
    TRANSLATION       — dict with version/status/note (see translate.py docstring)
    translate(text)  — conceptual Boolean -> this database's query syntax
    run(query_id, spec, config) -> (translated_query, rows, total_hits)

Adding a sixth database means adding one file here and one line in REGISTRY
below. It should never require touching the runner, anchors, sampling, or
summary modules.
"""

from . import (openalex, pubmed, europe_pmc, eric, openaire, core, semantic_scholar,
               scopus, wos, world_bank, doaj, repec, base, lens, embase)

REGISTRY = {
    "openalex": openalex,
    "pubmed": pubmed,
    "europe_pmc": europe_pmc,
    "eric": eric,
    "openaire": openaire,
    "core": core,
    "semantic_scholar": semantic_scholar,
    "scopus": scopus,
    "wos": wos,
    "world_bank": world_bank,
    "doaj": doaj,
    "repec": repec,
    "base": base,
    "lens": lens,
    "embase": embase,
}
