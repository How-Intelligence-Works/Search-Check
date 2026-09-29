import time

import requests

from ..schema import new_row

NAME = "ERIC"
URL = "https://api.ies.ed.gov/eric/"

TRANSLATION = {
    "version": "ERIC-v0.1",
    "status": "PILOT-UNTESTED",
    "note": "Conceptual Boolean passed through unchanged. Same untested caveat as Europe PMC.",
}


def translate(text):
    return text


def run(query_id, spec, config):
    q = translate(spec["text"])
    rows, start, rows_per_page, total_hits = [], 0, 200, None
    while total_hits is None or start < min(total_hits, config.download_cap):
        params = {"search": q, "format": "json", "rows": rows_per_page, "start": start}
        resp = requests.get(URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if total_hits is None:
            total_hits = data.get("total", data.get("numFound", 0))
        docs = data.get("docs", data.get("response", {}).get("docs", []))
        for d in docs:
            def first(field):
                v = d.get(field)
                return v[0] if isinstance(v, list) else (v or "")
            abstract = first("description")
            authors_field = d.get("author")
            if isinstance(authors_field, list):
                authors = "; ".join(authors_field)
            else:
                authors = authors_field or ""
            rows.append(new_row(
                query_id, spec["family"], spec["substream"], NAME, q,
                id=d.get("id", ""), doi="", title=first("title"), authors=authors,
                year=first("publicationdateyear"), source_name="ERIC",
                publication_type=first("publicationtype"), language=first("language"),
                url=f"https://eric.ed.gov/?id={d.get('id','')}",
                abstract_available="Y" if abstract else "N", abstract=abstract,
            ))
        start += rows_per_page
        time.sleep(config.sleep_seconds)
        if not docs:
            break
    return q, rows, total_hits or 0
