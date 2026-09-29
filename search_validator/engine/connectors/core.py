import time

import requests

from ..schema import new_row

NAME = "CORE"
URL = "https://api.core.ac.uk/v3/search/works/"  # trailing slash required, else 301

TRANSLATION = {
    "version": "CORE-v0.1",
    "status": "PILOT-UNTESTED",
    "note": "Conceptual Boolean passed through as CORE's q= parameter, untested for equivalence.",
}


def translate(text):
    return text


def run(query_id, spec, config):
    q = translate(spec["text"])
    headers = {}
    if config.core_api_key:
        headers["Authorization"] = f"Bearer {config.core_api_key}"
    else:
        print("  [CORE] WARNING: no core_api_key set in project.yml — anonymous CORE "
              "requests are reliably rate-limited (429). Register a free key at "
              "https://core.ac.uk/services/api and add it to project.yml.")

    rows, offset, limit, total_hits = [], 0, 100, None
    while total_hits is None or offset < min(total_hits, config.download_cap):
        params = {"q": q, "limit": limit, "offset": offset}
        resp = requests.get(URL, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if total_hits is None:
            total_hits = data.get("totalHits", 0)
        results = data.get("results", [])
        for r in results:
            title = r.get("title", "") or ""
            if not title:
                continue  # CORE occasionally returns stub records with no title
            authors = "; ".join(a.get("name", "") for a in (r.get("authors") or []))
            year = str(r.get("publishedDate", "") or "")[:4] or str(r.get("yearPublished", "") or "")
            url = ""
            links = r.get("links") or []
            if links:
                url = links[0].get("url", "")
            abstract = r.get("abstract", "") or ""
            rows.append(new_row(
                query_id, spec["family"], spec["substream"], NAME, q,
                id=str(r.get("id", "")), doi=r.get("doi", "") or "", title=title,
                authors=authors, year=year, source_name="CORE",
                publication_type=r.get("documentType", ""), language=r.get("language", "") or "",
                url=url, abstract_available="Y" if abstract else "N", abstract=abstract,
            ))
        offset += limit
        time.sleep(config.sleep_seconds)
        if not results:
            break
    return q, rows, total_hits or 0
