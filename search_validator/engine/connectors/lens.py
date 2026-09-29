import time

import requests

from ..schema import new_row

NAME = "Lens.org"
URL = "https://api.lens.org/scholarly/search"

TRANSLATION = {
    "version": "LENS-v0.1",
    "status": "PILOT-UNTESTED",
    "note": ("Conceptual Boolean sent as Lens's query DSL 'match' query against "
             "title+abstract. Lens's full query syntax is closer to Elasticsearch "
             "than a plain Boolean string — untested whether the raw conceptual "
             "string needs restructuring into their JSON query DSL for complex "
             "AND/OR nesting to actually work as intended."),
}

# Lens access is free for non-commercial/research use but is APPROVAL-GATED,
# not instant self-serve like CORE or Semantic Scholar — you apply, and Lens
# reviews the request (can take days), unlike the others in this engine.


def translate(text):
    return text


def run(query_id, spec, config):
    q = translate(spec["text"])
    if not config.lens_api_key:
        print("  [Lens.org] WARNING: no lens_api_key set. Lens access requires applying "
              "for approval (not instant) at https://www.lens.org/lens/user/subscriptions "
              "— this can take a few days, unlike the other free connectors in this engine.")

    headers = {"Authorization": f"Bearer {config.lens_api_key}", "Content-Type": "application/json"}
    rows, offset, size, total_hits = [], 0, 100, None
    while total_hits is None or offset < min(total_hits, config.download_cap):
        body = {
            "query": {"match": {"full_text": q}},
            "from": offset, "size": size,
            "include": ["lens_id", "title", "authors", "year_published",
                        "external_ids", "source", "abstract"],
        }
        resp = requests.post(URL, json=body, headers=headers, timeout=30)
        if resp.status_code in (401, 403):
            raise RuntimeError(
                f"Lens.org returned {resp.status_code} — either the token is invalid/expired, "
                f"or the account's API access application hasn't been approved yet. Check "
                f"https://www.lens.org/lens/user/subscriptions"
            )
        resp.raise_for_status()
        data = resp.json()
        if total_hits is None:
            total_hits = int(data.get("total", 0) or 0)
        results = data.get("data", [])
        for r in results:
            try:
                title = r.get("title", "") or ""
                if not title:
                    continue
                authors = "; ".join(a.get("display_name", "") for a in (r.get("authors") or []))
                doi = next((e.get("value", "") for e in (r.get("external_ids") or [])
                            if e.get("type", "").lower() == "doi"), "")
                year = str(r.get("year_published", "") or "")
                source_name = (r.get("source") or {}).get("title", "") or ""
                abstract = r.get("abstract", "") or ""
                lens_id = r.get("lens_id", "")
            except Exception as e:
                print(f"  [Lens.org] WARNING: could not parse one record ({e}) — skipping it.")
                continue
            rows.append(new_row(
                query_id, spec["family"], spec["substream"], NAME, q,
                id=lens_id, doi=doi, title=title, authors=authors, year=year,
                source_name=source_name, publication_type="", language="",
                url=f"https://www.lens.org/lens/scholar/article/{lens_id}",
                abstract_available="Y" if abstract else "N", abstract=abstract,
            ))
        offset += size
        time.sleep(config.sleep_seconds)
        if not results:
            break
    return q, rows, total_hits or 0
