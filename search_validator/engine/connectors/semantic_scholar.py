import time

import requests

from ..schema import new_row

NAME = "Semantic Scholar"
URL = "https://api.semanticscholar.org/graph/v1/paper/search"
FIELDS = "title,authors,year,abstract,venue,externalIds,publicationTypes"

TRANSLATION = {
    "version": "S2-v0.1",
    "status": "PILOT-UNTESTED",
    "note": "Conceptual Boolean passed through as query=; Semantic Scholar's own query parser handles it, not tested for equivalence with the other connectors.",
}


def translate(text):
    return text


def run(query_id, spec, config):
    q = translate(spec["text"])
    headers = {"x-api-key": config.semantic_scholar_api_key} if config.semantic_scholar_api_key else {}
    # Without a registered key, Semantic Scholar shares one rate-limit pool
    # across every anonymous caller worldwide (~1 req/sec, sometimes tighter).
    # This sleep is deliberately more conservative than the other connectors'
    # default for that reason.
    sleep_seconds = config.sleep_seconds if config.semantic_scholar_api_key else max(config.sleep_seconds, 1.1)

    rows, offset, limit, total_hits = [], 0, 100, None
    hard_cap = min(config.download_cap, 1000)  # the basic search endpoint doesn't paginate past 1000
    while total_hits is None or offset < min(total_hits, hard_cap):
        params = {"query": q, "limit": limit, "offset": offset, "fields": FIELDS}
        resp = requests.get(URL, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if total_hits is None:
            total_hits = data.get("total", 0)
        results = data.get("data", [])
        for r in results:
            authors = "; ".join(a.get("name", "") for a in (r.get("authors") or []))
            doi = (r.get("externalIds") or {}).get("DOI", "") or ""
            abstract = r.get("abstract", "") or ""
            rows.append(new_row(
                query_id, spec["family"], spec["substream"], NAME, q,
                id=r.get("paperId", ""), doi=doi, title=r.get("title", "") or "",
                authors=authors, year=r.get("year", ""), source_name=r.get("venue", ""),
                publication_type=", ".join(r.get("publicationTypes") or []), language="",
                url=f"https://www.semanticscholar.org/paper/{r.get('paperId', '')}",
                abstract_available="Y" if abstract else "N", abstract=abstract,
            ))
        offset += limit
        time.sleep(sleep_seconds)
        if not results or not data.get("next"):
            break
    if total_hits and total_hits > hard_cap:
        print(f"  [Semantic Scholar] NOTE: total hits ({total_hits}) exceed this endpoint's "
              f"1000-record pagination limit; only the first {hard_cap} were retrieved. Use "
              f"the bulk search endpoint if you need the full set.")
    return q, rows, total_hits or 0
