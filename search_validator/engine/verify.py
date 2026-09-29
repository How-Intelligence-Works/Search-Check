"""Crossref verification utility — resolves a DOI to confirmed metadata.
Not a search source; use this to clean up ambiguous benchmark identities."""

import requests

CROSSREF_URL = "https://api.crossref.org/works"


def verify_doi(doi, config):
    resp = requests.get(f"{CROSSREF_URL}/{doi}", params={"mailto": config.contact_email}, timeout=30)
    if resp.status_code != 200:
        print(f"Crossref lookup failed ({resp.status_code}) for {doi}")
        return None
    msg = resp.json().get("message", {})
    title = (msg.get("title") or [""])[0]
    authors = msg.get("author", [])
    first_author = authors[0].get("family", "") if authors else ""
    year = None
    for date_field in ("published-print", "published-online", "issued"):
        parts = msg.get(date_field, {}).get("date-parts", [[None]])
        if parts and parts[0][0]:
            year = parts[0][0]
            break
    print(f"DOI:      {doi}\nTitle:    {title}\n1st auth: {first_author}\nYear:     {year}\n"
          f"Journal:  {(msg.get('container-title') or [''])[0]}")
    return {"doi": doi, "title": title, "first_author": first_author, "year": year}
