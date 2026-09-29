import time

import requests

from ..schema import new_row

NAME = "Scopus"
URL = "https://api.elsevier.com/content/search/scopus"

TRANSLATION = {
    "version": "SCOPUS-v0.1",
    "status": "PILOT-UNTESTED",
    "note": ("Conceptual Boolean passed through as Scopus's query= parameter. Scopus's "
             "native syntax favors explicit field codes (e.g. TITLE-ABS-KEY(...)) — if "
             "results look thin, try wrapping the whole query in TITLE-ABS-KEY(...) "
             "explicitly rather than relying on the default field."),
}

# UNLIKE the other connectors, this one's field mapping is SCHEMA-UNVERIFIED
# against a live response — built from Elsevier's documented Scopus Search
# API response shape, but nobody building this had institutional access to
# confirm it against a real authenticated call. Per-record parsing is
# wrapped defensively so a wrong field path degrades to a warning and a
# thinner row, not a crash. Run one query against this connector alone and
# check the output before trusting it for a real pilot.


def translate(text):
    return text


def _parse_entry(entry):
    doi = entry.get("prism:doi", "") or ""
    title = entry.get("dc:title", "") or ""
    # STANDARD view (the default, unentitled tier) typically returns only the
    # first/corresponding author via dc:creator, not a full author list —
    # a full list usually requires COMPLETE view, which needs higher
    # entitlement than a base subscription may grant.
    authors = entry.get("dc:creator", "") or ""
    year = (entry.get("prism:coverDate", "") or entry.get("prism:publicationDate", "") or "")[:4]
    source_name = entry.get("prism:publicationName", "") or ""
    pub_type = entry.get("subtypeDescription", "") or ""
    url = entry.get("prism:url", "") or ""
    scopus_id = entry.get("dc:identifier", "") or ""
    return {
        "id": scopus_id, "doi": doi, "title": title, "authors": authors,
        "year": year, "source_name": source_name, "publication_type": pub_type, "url": url,
    }


def run(query_id, spec, config):
    q = translate(spec["text"])
    headers = {"X-ELS-APIKey": config.scopus_api_key, "Accept": "application/json"}
    if config.scopus_insttoken:
        headers["X-ELS-Insttoken"] = config.scopus_insttoken

    rows, start, count, total_hits = [], 0, 25, None  # 25/page matches Elsevier's documented example
    while total_hits is None or start < min(total_hits, config.download_cap):
        params = {"query": q, "start": start, "count": count, "view": "STANDARD"}
        resp = requests.get(URL, params=params, headers=headers, timeout=30)
        if resp.status_code in (401, 403):
            raise RuntimeError(
                f"Scopus returned {resp.status_code} — this almost always means the API key "
                f"isn't recognized as belonging to a subscribing institution (no campus "
                f"network/VPN, and no valid X-ELS-Insttoken set). An API key alone is not "
                f"sufficient; see engine/connectors/scopus.py for details."
            )
        resp.raise_for_status()
        data = resp.json().get("search-results", {})
        if total_hits is None:
            total_hits = int(data.get("opensearch:totalResults", 0) or 0)
        entries = data.get("entry", [])
        for entry in entries:
            try:
                parsed = _parse_entry(entry)
            except Exception as e:
                print(f"  [Scopus] WARNING: could not parse one record ({e}) — skipping it, "
                      f"not the whole run. This is the kind of thing that needs a live schema check.")
                continue
            if not parsed["title"]:
                print(f"  [Scopus] WARNING: record {parsed['id']!r} parsed with no title — "
                      f"likely a schema mismatch, not a real title-less record. Skipping it.")
                continue
            abstract = entry.get("dc:description", "") or ""
            rows.append(new_row(
                query_id, spec["family"], spec["substream"], NAME, q,
                id=parsed["id"], doi=parsed["doi"], title=parsed["title"],
                authors=parsed["authors"], year=parsed["year"], source_name=parsed["source_name"],
                publication_type=parsed["publication_type"], language="", url=parsed["url"],
                abstract_available="Y" if abstract else "N", abstract=abstract,
            ))
        start += count
        time.sleep(config.sleep_seconds)
        if not entries:
            break
    return q, rows, total_hits or 0
