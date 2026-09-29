import re
import time
import xml.etree.ElementTree as ET

import requests

from ..schema import new_row

NAME = "PubMed"
ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

TRANSLATION = {
    "version": "PM-v0.1",
    "status": "PILOT-UNTESTED",
    "note": "Tags bare terms/phrases with [tiab]; AND/OR/NOT pass through natively.",
}


def translate(text):
    def tag_term(match):
        token = match.group(0)
        if token.upper() in ("AND", "OR", "NOT") or token in ("(", ")"):
            return token
        return f"{token}[tiab]"
    pattern = re.compile(r'"[^"]*\*?"|\(|\)|\bAND\b|\bOR\b|\bNOT\b|[\w-]+\*?')
    return pattern.sub(tag_term, text)


def _fetch_abstracts(pmids, config):
    out = {}
    for i in range(0, len(pmids), 200):
        batch = pmids[i:i + 200]
        params = {"db": "pubmed", "id": ",".join(batch), "rettype": "abstract",
                   "retmode": "xml", "email": config.contact_email}
        resp = requests.get(EFETCH_URL, params=params, timeout=30)
        time.sleep(config.sleep_seconds)
        if resp.status_code != 200:
            continue
        try:
            root = ET.fromstring(resp.content)
        except ET.ParseError:
            continue
        for article in root.findall(".//PubmedArticle"):
            pmid_el = article.find(".//PMID")
            pmid = pmid_el.text if pmid_el is not None else None
            parts = [el.text or "" for el in article.findall(".//AbstractText")]
            if pmid:
                out[pmid] = " ".join(parts).strip()
    return out


def run(query_id, spec, config):
    q = translate(spec["text"])
    pmids, retstart, retmax, total_hits = [], 0, 200, None
    while total_hits is None or retstart < min(total_hits, config.download_cap):
        params = {"db": "pubmed", "term": q, "retmode": "json", "retstart": retstart,
                   "retmax": retmax, "email": config.contact_email}
        resp = requests.get(ESEARCH_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json().get("esearchresult", {})
        total_hits = int(data.get("count", 0))
        ids = data.get("idlist", [])
        pmids.extend(ids)
        retstart += retmax
        time.sleep(config.sleep_seconds)
        if not ids:
            break

    abstracts = _fetch_abstracts(pmids, config)
    rows = []
    for i in range(0, len(pmids), 200):
        batch = pmids[i:i + 200]
        params = {"db": "pubmed", "id": ",".join(batch), "retmode": "json",
                   "email": config.contact_email}
        resp = requests.get(ESUMMARY_URL, params=params, timeout=30)
        time.sleep(config.sleep_seconds)
        resp.raise_for_status()
        result = resp.json().get("result", {})
        for pmid in batch:
            item = result.get(pmid, {})
            if not item:
                continue
            doi = next((a.get("value", "") for a in item.get("articleids", [])
                        if a.get("idtype") == "doi"), "")
            authors = "; ".join(a.get("name", "") for a in item.get("authors", []))
            abstract = abstracts.get(pmid, "")
            rows.append(new_row(
                query_id, spec["family"], spec["substream"], NAME, q,
                id=f"PMID:{pmid}", doi=doi, title=item.get("title", ""), authors=authors,
                year=(item.get("pubdate") or "")[:4], source_name=item.get("fulljournalname", ""),
                publication_type=", ".join(item.get("pubtype", [])), language="",
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                abstract_available="Y" if abstract else "N", abstract=abstract,
            ))
    return q, rows, total_hits or 0
