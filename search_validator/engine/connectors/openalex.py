import re
import time

import requests

from ..schema import new_row, reconstruct_openalex_abstract

NAME = "OpenAlex"
URL = "https://api.openalex.org/works"

TRANSLATION = {
    "version": "OA-v0.1",
    "status": "PILOT-UNTESTED",
    "note": "Strips bare trailing * (relies on OpenAlex stemming); quoted-phrase * kept.",
}


def translate(text):
    def strip_bare_star(match):
        token = match.group(0)
        return token if token.startswith('"') else token.rstrip("*")
    pattern = re.compile(r'"[^"]*\*?"|\b[\w-]+\*?\b')
    return pattern.sub(strip_bare_star, text)


def run(query_id, spec, config):
    q = translate(spec["text"])
    rows, cursor, pages, total_hits = [], "*", 0, None
    while cursor and pages < config.max_pages and len(rows) < config.download_cap:
        params = {"filter": f"title_and_abstract.search:{q}", "per-page": 100,
                  "cursor": cursor, "mailto": config.contact_email}
        resp = requests.get(URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        meta = data.get("meta", {})
        if total_hits is None:
            total_hits = meta.get("count", 0)
        for r in data.get("results", []):
            source = (r.get("primary_location") or {}).get("source") or {}
            authors = "; ".join(a.get("author", {}).get("display_name", "")
                                 for a in r.get("authorships", []))
            abstract = reconstruct_openalex_abstract(r.get("abstract_inverted_index"))
            rows.append(new_row(
                query_id, spec["family"], spec["substream"], NAME, q,
                id=r.get("id", ""), doi=(r.get("doi") or "").replace("https://doi.org/", ""),
                title=r.get("title", "") or "", authors=authors,
                year=r.get("publication_year", ""), source_name=source.get("display_name", ""),
                publication_type=r.get("type", ""), language=r.get("language", ""),
                url=r.get("id", ""), abstract_available="Y" if abstract else "N",
                abstract=abstract,
            ))
        cursor = meta.get("next_cursor")
        pages += 1
        if not data.get("results"):
            break
        time.sleep(config.sleep_seconds)
    return q, rows, total_hits or 0
