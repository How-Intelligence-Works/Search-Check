import time
from urllib.parse import quote

import requests

from ..schema import new_row

NAME = "DOAJ"
URL = "https://doaj.org/api/search/articles"

TRANSLATION = {
    "version": "DOAJ-v0.1",
    "status": "PILOT-UNTESTED",
    "note": ("Conceptual Boolean URL-encoded and passed as a path segment — DOAJ's "
             "search supports Elasticsearch-style query syntax, so AND/OR/quoted "
             "phrases should carry over, but this hasn't been piloted."),
}


def translate(text):
    return text


def run(query_id, spec, config):
    q = translate(spec["text"])
    rows, page, page_size, total_hits = [], 1, 100, None
    while total_hits is None or (page - 1) * page_size < min(total_hits, config.download_cap):
        url = f"{URL}/{quote(q)}"
        params = {"page": page, "pageSize": page_size}
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if total_hits is None:
            total_hits = int(data.get("total", 0) or 0)
        results = data.get("results", [])
        for r in results:
            bibjson = r.get("bibjson", {})
            title = bibjson.get("title", "") or ""
            if not title:
                continue
            authors = "; ".join(a.get("name", "") for a in (bibjson.get("author") or []))
            doi = next((i.get("id", "") for i in (bibjson.get("identifier") or [])
                        if i.get("type", "").lower() == "doi"), "")
            year = str(bibjson.get("year", "") or "")
            journal = (bibjson.get("journal") or {}).get("title", "") or ""
            abstract = bibjson.get("abstract", "") or ""
            url_field = next((l.get("url", "") for l in (bibjson.get("link") or [])), "")
            rows.append(new_row(
                query_id, spec["family"], spec["substream"], NAME, q,
                id=r.get("id", ""), doi=doi, title=title, authors=authors, year=year,
                source_name=journal, publication_type="article", language="",
                url=url_field, abstract_available="Y" if abstract else "N", abstract=abstract,
            ))
        page += 1
        time.sleep(config.sleep_seconds)
        if not results:
            break
    return q, rows, total_hits or 0
