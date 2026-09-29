"""Row schema, run configuration, and small shared helpers.

Nothing in this file is project-specific. If a project needs a different
metadata field, that's a sign the field belongs in a project-level export
step, not here — keep the engine's row shape stable across projects so
results from different studies stay comparable.
"""

import re
from dataclasses import dataclass, field
from datetime import date


ROW_FIELDS = [
    "query_id", "family", "substream", "database", "id", "doi", "title",
    "authors", "year", "source_name", "publication_type", "language",
    "url", "abstract_available", "abstract", "retrieved_query",
    "retrieval_date",
]

LOG_FIELDS = [
    "run_id", "query_id", "database", "translation_version", "translation_status",
    "date_run", "translated_query", "total_hits_reported",
    "records_retrieved", "retrieval_truncated", "export_filename",
    "status", "error_message",
]

CODING_FIELDS = [
    "query_id", "database", "record_id", "title", "year", "sample_type",
    "relevance (relevant/partial/irrelevant — FILL IN)",
    "false_positive_mechanism (FILL IN if irrelevant/partial)",
    "notes (FILL IN)",
]

# Only OpenAlex indexing is treated as verified by default, because that's
# the only field the original Paper 2 benchmark corpus tracks. A project can
# override this (see Config.verified_indexing_databases) once it has
# per-database indexing verification for its own benchmark.
DEFAULT_VERIFIED_INDEXING_DATABASES = {"OpenAlex"}


@dataclass
class Config:
    """Everything about *how* a run behaves, independent of *what* is
    being searched. Loaded from project.yml, with engine-level defaults."""
    contact_email: str = "your-email@example.com"
    download_cap: int = 2000
    max_pages: int = 20
    sleep_seconds: float = 0.34
    out_dir: str = "results"
    core_api_key: str = ""              # free registration: https://core.ac.uk/services/api
    semantic_scholar_api_key: str = ""  # optional free registration: https://www.semanticscholar.org/product/api
    scopus_api_key: str = ""            # requires an institutional subscription; register at
                                         # https://dev.elsevier.com — key alone is often NOT
                                         # sufficient, see scopus_insttoken below
    scopus_insttoken: str = ""          # needed if you're not calling from a recognized
                                         # campus IP range; your institution's library/IT
                                         # office issues this, not you
    wos_api_key: str = ""               # requires an institutional subscription specifically
                                         # to the WoS *Expanded* API (WoS has several API
                                         # tiers with separate entitlements) — register via
                                         # https://developer.clarivate.com
    base_api_key: str = ""              # register at https://www.base-search.net/about/en/api.php
                                         # — access model is inconsistently documented; may also
                                         # require BASE to whitelist your IP separately
    lens_api_key: str = ""              # free for non-commercial/research use, but
                                         # APPROVAL-GATED (not instant); apply at
                                         # https://www.lens.org/lens/user/subscriptions
    embase_api_key: str = ""            # granted case-by-case by Elsevier regardless of an
                                         # embase.com subscription — contact an Elsevier
                                         # Embase representative, a Scopus key will NOT work here
    embase_insttoken: str = ""
    verified_indexing_databases: set = field(
        default_factory=lambda: set(DEFAULT_VERIFIED_INDEXING_DATABASES)
    )


def new_row(query_id, family, substream, database, retrieved_query, **kwargs):
    row = {k: "" for k in ROW_FIELDS}
    row.update({
        "query_id": query_id, "family": family, "substream": substream,
        "database": database, "retrieved_query": retrieved_query,
        "retrieval_date": date.today().isoformat(),
    })
    row.update(kwargs)
    return row


def normalize_title(t):
    return re.sub(r"[^a-z0-9 ]", "", (t or "").lower()).strip()


def normalize_doi(d):
    return (d or "").lower().replace("https://doi.org/", "").strip().strip("/")


def reconstruct_openalex_abstract(inverted_index):
    if not inverted_index:
        return ""
    positions = {}
    for word, idxs in inverted_index.items():
        for i in idxs:
            positions[i] = word
    return " ".join(positions[i] for i in sorted(positions))
