import time

import requests

from ..schema import new_row

NAME = "Embase"
URL = "https://api.elsevier.com/content/embase/article"

TRANSLATION = {
    "version": "EMBASE-v0.1",
    "status": "PILOT-UNTESTED",
    "note": ("Conceptual Boolean passed through as query=. Same caveat as Scopus: "
             "Embase's native syntax favors explicit field/thesaurus terms (Emtree "
             "indexing) over plain-text Boolean, so results may look thin without "
             "adapting the query to Embase's own conventions."),
}

# Gated even beyond a normal institutional subscription: Elsevier grants full
# Embase API access "on a case-by-case basis, regardless of subscription to
# embase.com" — you need to contact an Elsevier Embase representative, not
# just register for a key the way Scopus/WoS technically allow.


def translate(text):
    return text


def run(query_id, spec, config):
    q = translate(spec["text"])
    headers = {"X-ELS-APIKey": config.embase_api_key, "Accept": "application/json"}
    if config.embase_insttoken:
        headers["X-ELS-Insttoken"] = config.embase_insttoken

    rows, start, count, total_hits = [], 0, 25, None
    while total_hits is None or start < min(total_hits, config.download_cap):
        params = {"query": q, "start": start, "count": count}
        resp = requests.get(URL, params=params, headers=headers, timeout=30)
        if resp.status_code in (401, 403):
            raise RuntimeError(
                f"Embase returned {resp.status_code} — full Embase API access is granted "
                f"case-by-case by Elsevier regardless of an embase.com subscription; a key "
                f"that works for Scopus will NOT automatically work here. Contact an "
                f"Elsevier Embase representative via https://dev.elsevier.com/embase_apis.html"
            )
        resp.raise_for_status()
        data = resp.json()
        # Response shape assumed to mirror Scopus's search-results/entry structure,
        # per Elsevier's shared API conventions — NOT verified against a live call.
        results = data.get("search-results", data.get("results", {}))
        entries = results.get("entry", []) if isinstance(results, dict) else results
        if total_hits is None:
            total_hits = int(results.get("opensearch:totalResults", len(entries)) or 0) \
                if isinstance(results, dict) else len(entries)
        if not entries:
            break
        for entry in entries:
            try:
                title = entry.get("dc:title", entry.get("title", "")) or ""
                if not title:
                    continue
                authors = entry.get("dc:creator", entry.get("authors", "")) or ""
                doi = entry.get("prism:doi", entry.get("doi", "")) or ""
                year = (entry.get("prism:coverDate", "") or "")[:4]
                source_name = entry.get("prism:publicationName", "") or ""
                abstract = entry.get("dc:description", "") or ""
                embase_id = entry.get("dc:identifier", "") or ""
            except Exception as e:
                print(f"  [Embase] WARNING: could not parse one record ({e}) — skipping it.")
                continue
            rows.append(new_row(
                query_id, spec["family"], spec["substream"], NAME, q,
                id=embase_id, doi=doi, title=title, authors=authors, year=year,
                source_name=source_name, publication_type="", language="",
                url=entry.get("prism:url", "") or "",
                abstract_available="Y" if abstract else "N", abstract=abstract,
            ))
        start += count
        time.sleep(config.sleep_seconds)
    return q, rows, total_hits or 0
