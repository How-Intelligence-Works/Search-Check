import time

import requests

from ..schema import new_row

NAME = "RePEc/IDEAS"
URL = "https://ideas.repec.org/cgi-bin/htsearch"

TRANSLATION = {
    "version": "REPEC-v0.1",
    "status": "PILOT-UNTESTED",
    "note": ("Conceptual Boolean passed through as q=. IDEAS's htsearch is an older "
             "ht://Dig-based search engine, not a modern query parser — complex "
             "AND/OR/quoted-phrase Booleans are the most likely thing to behave "
             "differently here than in the other connectors. Worth an early pilot check."),
}

# RePEc/IDEAS is economics-specific — most relevant to queries touching
# bargaining, labor, time poverty, resource depletion (the parts of this
# framework that sit closer to economics than sociology or health.


# NOTE ON CONFIDENCE: htsearch's exact JSON field names (results vs items,
# handle vs id, etc.) were not confirmed against a live response — only the
# base curl invocation was documented where this was built. Field names
# below are reasonable guesses based on RePEc conventions, not verified.
# Treat this one like scopus.py/wos.py: pilot it first, don't trust the
# metadata blind.


def translate(text):
    return text


def run(query_id, spec, config):
    q = translate(spec["text"])
    rows, page, per_page, total_hits = [], 0, 100, None
    while total_hits is None or page * per_page < min(total_hits, config.download_cap):
        params = {"q": q, "cmd": "Search", "fmt": "json", "page": page}
        resp = requests.get(URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if total_hits is None:
            total_hits = int(data.get("total", data.get("matches", 0)) or 0)
        results = data.get("results", data.get("items", []))
        for r in results:
            try:
                title = r.get("title", "") or ""
                if not title:
                    continue
                authors = "; ".join(r.get("authors", [])) if isinstance(r.get("authors"), list) \
                    else (r.get("authors", "") or "")
                handle = r.get("handle", "") or r.get("id", "")
                year = str(r.get("year", "") or "")[:4]
                abstract = r.get("abstract", "") or ""
                url = r.get("url", "") or f"https://ideas.repec.org/{handle}.html"
            except Exception as e:
                print(f"  [RePEc/IDEAS] WARNING: could not parse one record ({e}) — skipping it.")
                continue
            rows.append(new_row(
                query_id, spec["family"], spec["substream"], NAME, q,
                id=handle, doi=r.get("doi", "") or "", title=title, authors=authors,
                year=year, source_name=r.get("series", "") or "RePEc",
                publication_type=r.get("type", ""), language="",
                url=url, abstract_available="Y" if abstract else "N", abstract=abstract,
            ))
        page += 1
        time.sleep(config.sleep_seconds)
        if not results:
            break
    return q, rows, total_hits or 0
