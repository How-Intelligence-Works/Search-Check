import time

import requests

from ..schema import new_row

NAME = "BASE"
URL = "https://api.base-search.net/cgi-bin/BaseHttpSearchInterface.fcgi"

TRANSLATION = {
    "version": "BASE-v0.1",
    "status": "PILOT-UNTESTED",
    "note": ("Conceptual Boolean passed through as query=. BASE's documentation is "
             "genuinely inconsistent on access requirements — some sources describe "
             "a straightforward free-registration API key, others describe an "
             "IP-whitelist model requiring BASE to pre-approve your server's IP "
             "address regardless of having a key. If this returns 403 with a valid "
             "key, that's almost certainly the IP-whitelist issue, not a bad query — "
             "contact BASE (https://www.base-search.net/about/en/contact.php) to ask "
             "about IP registration."),
}


def translate(text):
    return text


def run(query_id, spec, config):
    q = translate(spec["text"])
    if not config.base_api_key:
        print("  [BASE] WARNING: no base_api_key set in project.yml. BASE's access "
              "model for this is inconsistently documented; register at "
              "https://www.base-search.net/about/en/api.php")

    rows, offset, hits_per_page, total_hits = [], 0, 100, None
    while total_hits is None or offset < min(total_hits, config.download_cap):
        params = {"func": "PerformSearch", "query": q, "format": "json",
                   "hits": hits_per_page, "offset": offset}
        if config.base_api_key:
            params["api_key"] = config.base_api_key
        resp = requests.get(URL, params=params, timeout=30)
        if resp.status_code in (401, 403):
            raise RuntimeError(
                f"BASE returned {resp.status_code} — this is likely the IP-whitelist "
                f"issue described in engine/connectors/base.py's TRANSLATION note, not "
                f"a bad key or query. Contact BASE about registering your IP."
            )
        resp.raise_for_status()
        data = resp.json()
        response = data.get("response", data)
        docs = response.get("docs", response.get("results", []))
        if total_hits is None:
            total_hits = int(response.get("numFound", response.get("total", len(docs))) or 0)
        if not docs:
            break
        for d in docs:
            try:
                title = d.get("dctitle", d.get("title", "")) or ""
                if isinstance(title, list):
                    title = title[0] if title else ""
                if not title:
                    continue
                authors_field = d.get("dccreator", d.get("author", []))
                authors = "; ".join(authors_field) if isinstance(authors_field, list) else (authors_field or "")
                doi = ""
                identifiers = d.get("dcidentifier", []) or []
                if isinstance(identifiers, str):
                    identifiers = [identifiers]
                doi = next((i.replace("doi:", "").replace("https://doi.org/", "")
                            for i in identifiers if "doi" in i.lower()), "")
                year = str(d.get("dcyear", d.get("year", "")) or "")[:4]
                abstract = d.get("dcdescription", "") or ""
                if isinstance(abstract, list):
                    abstract = abstract[0] if abstract else ""
                url = d.get("dclink", "") or ""
                if isinstance(url, list):
                    url = url[0] if url else ""
                doc_id = d.get("dcdocid", d.get("id", ""))
            except Exception as e:
                print(f"  [BASE] WARNING: could not parse one record ({e}) — skipping it.")
                continue
            rows.append(new_row(
                query_id, spec["family"], spec["substream"], NAME, q,
                id=str(doc_id), doi=doi, title=title, authors=authors, year=year,
                source_name="BASE", publication_type="", language="",
                url=url, abstract_available="Y" if abstract else "N", abstract=abstract,
            ))
        offset += hits_per_page
        time.sleep(config.sleep_seconds)
    return q, rows, total_hits or 0
