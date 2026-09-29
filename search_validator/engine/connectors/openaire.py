import time

import requests

from ..schema import new_row

NAME = "OpenAIRE"
URL = "https://api.openaire.eu/graph/v3/research-products"

TRANSLATION = {
    "version": "OAIRE-v0.1",
    "status": "PILOT-UNTESTED",
    "note": ("Conceptual Boolean passed through unchanged; also mid-API-migration "
             "as of 2026 — treat zero hits with suspicion, not as a finding. Check "
             "https://graph.openaire.eu/docs if this endpoint starts erroring."),
}


def translate(text):
    return text


def run(query_id, spec, config):
    q = translate(spec["text"])
    rows, page, page_size, total_hits = [], 1, 100, None
    while total_hits is None or (page - 1) * page_size < min(total_hits, config.download_cap):
        params = {"search": q, "pageSize": page_size, "page": page}
        resp = requests.get(URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        header = data.get("header", {})
        if total_hits is None:
            total_hits = header.get("numFound", header.get("total", 0))
        results = data.get("results", [])
        for r in results:
            title = r.get("mainTitle") or r.get("title", "") or ""
            doi = next((p.get("value", "") for p in (r.get("pids") or [])
                        if p.get("scheme", "").lower() == "doi"), "")
            authors = "; ".join(a.get("fullName", "") for a in (r.get("authors") or []))
            abstract = ""
            desc = r.get("descriptions") or r.get("description")
            if isinstance(desc, list) and desc:
                abstract = desc[0]
            elif isinstance(desc, str):
                abstract = desc
            rows.append(new_row(
                query_id, spec["family"], spec["substream"], NAME, q,
                id=r.get("id", ""), doi=doi, title=title, authors=authors,
                year=(r.get("publicationDate", "") or "")[:4],
                source_name=NAME, publication_type=r.get("type", ""), language="",
                url=r.get("id", ""), abstract_available="Y" if abstract else "N",
                abstract=abstract,
            ))
        page += 1
        time.sleep(config.sleep_seconds)
        if not results:
            break
    return q, rows, total_hits or 0
