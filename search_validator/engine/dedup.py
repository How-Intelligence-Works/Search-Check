"""Deterministic cross-database deduplication with full provenance.

Conservative auto-merge hierarchy:
  1. normalized DOI exact match
  2. normalized title + publication year + first-author surname

Title+year without author is deliberately *not* auto-merged. That pattern is
written to dedup_review_candidates.csv for human review because it can collapse
distinct works (editorials, translations, annual reports, common titles).
"""
import csv
import hashlib
import os
from collections import defaultdict

from .schema import ROW_FIELDS, normalize_doi, normalize_title
from .results import latest_logs

DEDUP_FIELDS = [
    "canonical_id", "doi", "title", "authors", "year", "source_name",
    "publication_type", "language", "url", "abstract_available", "abstract",
    "query_ids", "families", "substreams", "databases", "source_record_ids",
    "occurrence_count", "dedup_basis",
]
PROVENANCE_FIELDS = ["canonical_id"] + ROW_FIELDS
REVIEW_FIELDS = [
    "review_group", "normalized_title", "year", "canonical_ids", "titles",
    "authors", "databases", "reason",
]


def _first_author_surname(authors):
    first = (authors or "").split(";")[0].strip()
    if not first:
        return ""
    # Most connectors emit either 'Surname, Given' or a display name.
    if "," in first:
        return first.split(",", 1)[0].strip().lower()
    parts = first.split()
    return parts[-1].strip().lower() if parts else ""


def _read_result_files(results_dir):
    logs = [r for r in latest_logs(results_dir) if r.get("status") == "OK"]
    occurrences = []
    for log in logs:
        path = log.get("export_filename", "")
        if path and not os.path.exists(path):
            path = os.path.join(results_dir, os.path.basename(path))
        if not path or not os.path.exists(path):
            continue
        with open(path, encoding="utf-8-sig") as f:
            occurrences.extend(csv.DictReader(f))
    return occurrences


def _stable_id(seed):
    return "SV-" + hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]


def _best_text(values):
    vals = [v.strip() for v in values if (v or "").strip()]
    return max(vals, key=len) if vals else ""


def _join_unique(values):
    return "; ".join(sorted({v.strip() for v in values if (v or "").strip()}))


def deduplicate(results_dir):
    occurrences = _read_result_files(results_dir)
    if not occurrences:
        return [], [], []

    # Union-find lets DOI and title-author-year evidence join the same cluster
    # without order-dependent behavior.
    parent = list(range(len(occurrences)))
    basis = [set() for _ in occurrences]

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a, b, why):
        ra, rb = find(a), find(b)
        if ra == rb:
            basis[ra].add(why)
            return
        parent[rb] = ra
        basis[ra].update(basis[rb])
        basis[ra].add(why)

    by_doi, by_tay = {}, {}
    for i, r in enumerate(occurrences):
        doi = normalize_doi(r.get("doi"))
        title = normalize_title(r.get("title"))
        year = (r.get("year") or "")[:4]
        author = _first_author_surname(r.get("authors"))
        if doi:
            if doi in by_doi:
                union(i, by_doi[doi], "DOI")
            else:
                by_doi[doi] = i
        if title and year and author:
            key = (title, year, author)
            if key in by_tay:
                j = by_tay[key]
                doi_j = normalize_doi(occurrences[j].get("doi"))
                # Distinct non-empty DOIs are contradictory identity evidence.
                # Never auto-merge them on bibliographic similarity alone.
                if not (doi and doi_j and doi != doi_j):
                    union(i, j, "TITLE+YEAR+FIRST_AUTHOR")
            else:
                by_tay[key] = i

    groups = defaultdict(list)
    for i in range(len(occurrences)):
        groups[find(i)].append(i)

    canonical_rows, provenance_rows = [], []
    index_to_canonical = {}
    for root, idxs in groups.items():
        rows = [occurrences[i] for i in idxs]
        dois = [normalize_doi(r.get("doi")) for r in rows if normalize_doi(r.get("doi"))]
        title = _best_text([r.get("title", "") for r in rows])
        year = _best_text([r.get("year", "") for r in rows])
        authors = _best_text([r.get("authors", "") for r in rows])
        seed = (sorted(dois)[0] if dois else f"{normalize_title(title)}|{year}|{_first_author_surname(authors)}|{rows[0].get('database','')}|{rows[0].get('id','')}")
        cid = _stable_id(seed)
        why = set()
        for i in idxs:
            why.update(basis[find(i)])
            index_to_canonical[i] = cid
        if len(rows) == 1:
            why.add("UNIQUE")
        canonical_rows.append({
            "canonical_id": cid,
            "doi": sorted(dois)[0] if dois else "",
            "title": title,
            "authors": authors,
            "year": year,
            "source_name": _join_unique(r.get("source_name", "") for r in rows),
            "publication_type": _join_unique(r.get("publication_type", "") for r in rows),
            "language": _join_unique(r.get("language", "") for r in rows),
            "url": _best_text([r.get("url", "") for r in rows]),
            "abstract_available": "Y" if any((r.get("abstract") or "").strip() for r in rows) else "N",
            "abstract": _best_text([r.get("abstract", "") for r in rows]),
            "query_ids": _join_unique(r.get("query_id", "") for r in rows),
            "families": _join_unique(r.get("family", "") for r in rows),
            "substreams": _join_unique(r.get("substream", "") for r in rows),
            "databases": _join_unique(r.get("database", "") for r in rows),
            "source_record_ids": _join_unique(f"{r.get('database','')}:{r.get('id','')}" for r in rows),
            "occurrence_count": len(rows),
            "dedup_basis": "; ".join(sorted(why)),
        })
        for r in rows:
            pr = {k: "" for k in PROVENANCE_FIELDS}
            pr["canonical_id"] = cid
            for k in ROW_FIELDS:
                pr[k] = r.get(k, "")
            provenance_rows.append(pr)

    # Surface title+year collisions that were intentionally not auto-merged.
    by_ty = defaultdict(set)
    meta = {}
    for i, r in enumerate(occurrences):
        t = normalize_title(r.get("title")); y = (r.get("year") or "")[:4]
        if t and y:
            cid = index_to_canonical[i]
            by_ty[(t, y)].add(cid)
            meta.setdefault(cid, []).append(r)
    review_rows = []
    n = 0
    for (t, y), cids in sorted(by_ty.items()):
        if len(cids) < 2:
            continue
        n += 1
        rs = [r for cid in cids for r in meta[cid]]
        review_rows.append({
            "review_group": f"R{n:04d}", "normalized_title": t, "year": y,
            "canonical_ids": "; ".join(sorted(cids)),
            "titles": _join_unique(r.get("title", "") for r in rs),
            "authors": _join_unique(r.get("authors", "") for r in rs),
            "databases": _join_unique(r.get("database", "") for r in rs),
            "reason": "Same normalized title+year but insufficient author/DOI evidence for safe auto-merge",
        })

    canonical_rows.sort(key=lambda r: (r["year"], r["title"], r["canonical_id"]))
    return canonical_rows, provenance_rows, review_rows


def write_deduplicated_outputs(results_dir):
    canonical, provenance, review = deduplicate(results_dir)
    outputs = [
        ("deduplicated_records.csv", DEDUP_FIELDS, canonical),
        ("dedup_provenance.csv", PROVENANCE_FIELDS, provenance),
        ("dedup_review_candidates.csv", REVIEW_FIELDS, review),
    ]
    for filename, fields, rows in outputs:
        path = os.path.join(results_dir, filename)
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader(); w.writerows(rows)
    print(f"Deduplicated {len(provenance)} retrieved occurrences into {len(canonical)} canonical records.")
    print(f"Flagged {len(review)} title+year collision group(s) for human review; none were auto-merged.")
    return canonical, provenance, review
