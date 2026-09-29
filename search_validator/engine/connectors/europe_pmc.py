import time

import requests

from ..schema import new_row

NAME = "Europe PMC"
URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

TRANSLATION = {
    "version": "EPMC-v0.1",
    "status": "PILOT-UNTESTED",
    "note": ("Conceptual Boolean passed through unchanged. Not yet confirmed "
             "equivalent to the OpenAlex/PubMed translations — piloting should "
             "establish that, not this comment."),
}


def translate(text):
    return text


def run(query_id, spec, config):
    q = translate(spec["text"])
    rows, cursor_mark, pages, total_hits = [], "*", 0, None
    while cursor_mark and pages < config.max_pages and len(rows) < config.download_cap:
        params = {"query": q, "format": "json", "pageSize": 100, "cursorMark": cursor_mark,
                   "resultType": "core", "email": config.contact_email}
        resp = requests.get(URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if total_hits is None:
            total_hits = data.get("hitCount", 0)
        results = data.get("resultList", {}).get("result", [])
        for r in results:
            abstract = r.get("abstractText", "") or ""
            rows.append(new_row(
                query_id, spec["family"], spec["substream"], NAME, q,
                id=r.get("id", ""), doi=r.get("doi", ""), title=r.get("title", ""),
                authors=r.get("authorString", ""), year=r.get("pubYear", ""),
                source_name=r.get("journalTitle", ""), publication_type=r.get("pubType", ""),
                language=r.get("language", ""),
                url=f"https://europepmc.org/article/{r.get('source','')}/{r.get('id','')}",
                abstract_available="Y" if abstract else "N", abstract=abstract,
            ))
        next_cursor = data.get("nextCursorMark")
        pages += 1
        if not next_cursor or next_cursor == cursor_mark or not results:
            break
        cursor_mark = next_cursor
        time.sleep(config.sleep_seconds)
    return q, rows, total_hits or 0
