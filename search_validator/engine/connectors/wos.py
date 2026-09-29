import time

import requests

from ..schema import new_row

NAME = "Web of Science"
URL = "https://wos-api.clarivate.com/api/wos/"

TRANSLATION = {
    "version": "WOS-v0.1",
    "status": "PILOT-UNTESTED",
    "note": ("Conceptual Boolean passed through wrapped as TS=(...) — Web of Science's "
             "Topic field tag (title+abstract+keywords). WoS's query parser is stricter "
             "about explicit field tags than OpenAlex/PubMed; if this returns nothing, "
             "check whether your Boolean needs adjusting for WoS's own syntax rules."),
}

# SAME CAVEAT AS SCOPUS: field mapping here is built from Clarivate's
# documented Expanded API response shape (deeply nested, XML-derived JSON —
# this API is notorious for that), not verified against a live authenticated
# response, since nobody building this had institutional access. Per-record
# parsing is defensive; a schema mismatch produces a warning and a thinner
# row rather than crashing the run. Smoke-test one query against this
# connector alone before trusting it.


def translate(text):
    # WoS's usrQuery generally expects an explicit field tag; TS= (Topic:
    # title+abstract+keywords) is the closest equivalent to the
    # title/abstract search the other connectors do by default.
    return f"TS=({text})"


def _get_nested(d, path, default=""):
    cur = d
    for key in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key, {})
    return cur if cur else default


def _parse_record(rec):
    uid = rec.get("UID", "")
    identifiers = _get_nested(rec, ["dynamic_data", "cluster_related", "identifiers", "identifier"], [])
    if isinstance(identifiers, dict):
        identifiers = [identifiers]
    doi = next((i.get("value", "") for i in identifiers if i.get("type") == "doi"), "")

    titles = _get_nested(rec, ["static_data", "summary", "titles", "title"], [])
    if isinstance(titles, dict):
        titles = [titles]
    title = next((t.get("content", "") for t in titles if t.get("type") == "item"), "")
    source_name = next((t.get("content", "") for t in titles if t.get("type") == "source"), "")

    names = _get_nested(rec, ["static_data", "summary", "names", "name"], [])
    if isinstance(names, dict):
        names = [names]
    authors = "; ".join(n.get("full_name") or n.get("wos_standard", "") for n in names
                         if n.get("role") == "author") or \
              "; ".join(n.get("full_name") or n.get("wos_standard", "") for n in names)

    pub_info = _get_nested(rec, ["static_data", "summary", "pub_info"], {})
    year = str(pub_info.get("pubyear", "") or pub_info.get("@pubyear", "") or "")

    doctypes = _get_nested(rec, ["static_data", "summary", "doctypes", "doctype"], [])
    if isinstance(doctypes, str):
        pub_type = doctypes
    elif isinstance(doctypes, list):
        pub_type = ", ".join(doctypes)
    else:
        pub_type = ""

    abstract = _get_nested(rec, ["static_data", "fullrecord_metadata", "abstracts", "abstract",
                                   "abstract_text", "p"], "")
    if isinstance(abstract, list):
        abstract = " ".join(abstract)

    return {"id": uid, "doi": doi, "title": title, "authors": authors, "year": year,
            "source_name": source_name, "publication_type": pub_type, "abstract": abstract}


def run(query_id, spec, config):
    q = translate(spec["text"])
    headers = {"X-ApiKey": config.wos_api_key, "Accept": "application/json"}

    rows, first_record, count, total_hits = [], 1, 100, None
    while total_hits is None or first_record <= min(total_hits, config.download_cap):
        params = {"databaseId": "WOS", "usrQuery": q, "count": count, "firstRecord": first_record}
        resp = requests.get(URL, params=params, headers=headers, timeout=30)
        if resp.status_code in (401, 403):
            raise RuntimeError(
                f"Web of Science returned {resp.status_code} — this almost always means the "
                f"API key isn't entitled for the Expanded API specifically (WoS has several "
                f"API tiers with separate entitlements). Check which WoS API your institution "
                f"actually licenses; see engine/connectors/wos.py for details."
            )
        resp.raise_for_status()
        data = resp.json()
        if total_hits is None:
            total_hits = int(_get_nested(data, ["QueryResult", "RecordsFound"], 0) or 0)
        records = _get_nested(data, ["Data", "Records", "records", "REC"], [])
        if isinstance(records, dict):
            records = [records]
        for rec in records:
            try:
                parsed = _parse_record(rec)
            except Exception as e:
                print(f"  [Web of Science] WARNING: could not parse one record ({e}) — "
                      f"skipping it, not the whole run.")
                continue
            if not parsed["title"]:
                print(f"  [Web of Science] WARNING: record {parsed['id']!r} parsed with no "
                      f"title — likely a schema mismatch, not a real title-less record. "
                      f"Skipping it. If this happens often, the field paths in "
                      f"_parse_record() need checking against a real response.")
                continue
            abstract = parsed["abstract"]
            rows.append(new_row(
                query_id, spec["family"], spec["substream"], NAME, q,
                id=parsed["id"], doi=parsed["doi"], title=parsed["title"],
                authors=parsed["authors"], year=parsed["year"], source_name=parsed["source_name"],
                publication_type=parsed["publication_type"], language="",
                url=f"https://www.webofscience.com/wos/woscc/full-record/{parsed['id']}",
                abstract_available="Y" if abstract else "N", abstract=abstract,
            ))
        first_record += count
        time.sleep(config.sleep_seconds)
        if not records:
            break
    return q, rows, total_hits or 0
