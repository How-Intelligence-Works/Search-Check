import time

import requests

from ..schema import new_row

NAME = "World Bank Documents"
URL = "https://search.worldbank.org/api/v3/wds"

TRANSLATION = {
    "version": "WB-v0.1",
    "status": "PILOT-UNTESTED",
    "note": ("Conceptual Boolean passed through as the qterm= parameter. qterm matches "
             "across title, abstract, report number, and other core fields; untested "
             "for how well it honors complex AND/OR/quoted-phrase structure vs. just "
             "treating it as loose keywords."),
}


def translate(text):
    return text


def run(query_id, spec, config):
    q = translate(spec["text"])
    rows, offset, rows_per_page, total_hits = [], 0, 100, None
    fields = "docdt,count,abstracts,authr,docty,url"
    while total_hits is None or offset < min(total_hits, config.download_cap):
        params = {"format": "json", "qterm": q, "fl": fields, "rows": rows_per_page,
                   "os": offset}
        resp = requests.get(URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if total_hits is None:
            total_hits = int(data.get("total", 0) or 0)
        # WDS returns documents as a dict keyed by document ID, not a list
        documents = data.get("documents", {})
        documents = {k: v for k, v in documents.items() if k != "facets"}
        if not documents:
            break
        for doc_id, doc in documents.items():
            title = doc.get("display_title", "") or doc.get("title", "") or ""
            if not title:
                continue
            abstract = ""
            abstracts = doc.get("abstracts", {})
            if isinstance(abstracts, dict):
                abstract = abstracts.get("cdata!", "") or ""
            authors = doc.get("authr", "") or ""
            if isinstance(authors, list):
                authors = "; ".join(authors)
            year = (doc.get("docdt", "") or "")[:4]
            doc_type = doc.get("docty", "") or ""
            url = doc.get("url", "") or f"https://documents.worldbank.org/curated/en/{doc_id}"
            rows.append(new_row(
                query_id, spec["family"], spec["substream"], NAME, q,
                id=doc_id, doi="", title=title, authors=authors, year=year,
                source_name="World Bank", publication_type=doc_type, language="",
                url=url, abstract_available="Y" if abstract else "N", abstract=abstract,
            ))
        offset += rows_per_page
        time.sleep(config.sleep_seconds)
    return q, rows, total_hits or 0
