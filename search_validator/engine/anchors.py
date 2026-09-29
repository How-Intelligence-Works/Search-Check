"""Database-specific benchmark/anchor recovery.

Matching hierarchy:
    DOI match                                  -> RECOVERED
    normalized title + first-author + year     -> RECOVERED
    normalized title + year only               -> CANDIDATE_REQUIRES_REVIEW
    verified indexed in this database, no match-> MISSING
    verified not indexed                       -> NOT_INDEXED
    no database-specific indexing ground truth -> indexing status unknown

A query may identify benchmark rows with `anchor_ids` (preferred) or legacy
first-author surname strings in `anchors`.
"""
import csv
import os
import re

from .schema import normalize_title, normalize_doi
from .connectors import REGISTRY
from .results import latest_export_for


def load_benchmark(benchmark_csv):
    with open(benchmark_csv, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "_", (s or "").lower()).strip("_")


def _indexing_flag(rec, db_name, route):
    """Return True/False/None from a database-specific benchmark column.

    Accepted headings include e.g. indexed_in_openalex, indexed_in_openalex?,
    indexed_in_pubmed, indexed_in_europe_pmc. Legacy Paper-2 heading
    `indexed_in_openalex? (Y/N)` is also accepted.
    """
    wanted = {_slug(f"indexed_in_{route}"), _slug(f"indexed_in_{db_name}")}
    for key, value in rec.items():
        ks = _slug(key)
        if any(ks == w or ks.startswith(w + "_") for w in wanted):
            v = (value or "").strip().upper()
            if v in {"Y", "YES", "TRUE", "1"}: return True
            if v in {"N", "NO", "FALSE", "0"}: return False
    return None


def _first_author_surname(authors):
    first = (authors or "").split(";")[0].strip()
    if not first: return ""
    if "," in first: return first.split(",", 1)[0].strip().lower()
    parts = first.split()
    return parts[-1].strip().lower() if parts else ""


def check_anchors(queries, benchmark_csv, results_dir, config, verbose=True):
    benchmark = load_benchmark(benchmark_csv)
    all_rows = []
    for qid, spec in queries.items():
        anchor_ids = set(spec.get("anchor_ids") or [])
        anchor_names = spec.get("anchors") or []
        if not anchor_ids and not anchor_names:
            continue
        if anchor_ids:
            candidate_records = [b for b in benchmark if (b.get("record_id") or "").strip() in anchor_ids]
        else:
            candidate_records = [b for b in benchmark if any(a.lower() in (b.get("first_author") or "").lower() for a in anchor_names)]
        if not candidate_records:
            if verbose: print(f"{qid}: no benchmark rows matched its configured anchors/anchor_ids")
            continue

        for route in spec["routes"]:
            db_name = REGISTRY[route].NAME
            path = latest_export_for(results_dir, qid, db_name)
            if not path:
                continue
            with open(path, encoding="utf-8-sig") as f:
                retrieved = list(csv.DictReader(f))
            retrieved_dois = {normalize_doi(r.get("doi")) for r in retrieved if r.get("doi")}
            by_tay, by_ty = {}, {}
            for r in retrieved:
                t = normalize_title(r.get("title")); y = (r.get("year") or "")[:4]
                first = _first_author_surname(r.get("authors"))
                if t and y: by_ty[(t, y)] = r
                if t and y and first: by_tay[(t, first, y)] = r

            db_verified = db_name in config.verified_indexing_databases
            for rec in candidate_records:
                doi = normalize_doi(rec.get("doi_or_url") or rec.get("doi"))
                title = normalize_title(rec.get("title")); year = (rec.get("year") or "")[:4]
                first = _first_author_surname(rec.get("first_author"))
                idx = _indexing_flag(rec, db_name, route) if db_verified else None
                if doi and doi in retrieved_dois:
                    classification = "RECOVERED (DOI match)"
                elif title and first and year and (title, first, year) in by_tay:
                    classification = "RECOVERED (title+author+year match)"
                elif title and year and (title, year) in by_ty:
                    classification = "CANDIDATE_REQUIRES_REVIEW (title+year, author unconfirmed)"
                elif idx is True:
                    classification = "MISSING (verified indexed, not retrieved)"
                elif idx is False:
                    classification = "NOT_INDEXED (verified not indexed here)"
                else:
                    classification = "indexing status unknown for this database"
                all_rows.append({"query_id": qid, "database": db_name, "anchor_record_id": rec.get("record_id", ""),
                                 "anchor_first_author": rec.get("first_author", ""), "anchor_year": year,
                                 "classification": classification})
    if verbose:
        by_qd = {}
        for r in all_rows: by_qd.setdefault((r["query_id"], r["database"]), []).append(r)
        for (qid, db), rows in sorted(by_qd.items()):
            print(f"{qid} / {db}:")
            for r in rows: print(f"    {r['anchor_record_id']} ({r['anchor_first_author']}, {r['anchor_year']}) — {r['classification']}")
    return all_rows


def write_anchor_matrix(queries, benchmark_csv, results_dir, config):
    rows = check_anchors(queries, benchmark_csv, results_dir, config, verbose=False)
    path = os.path.join(results_dir, "anchor_matrix.csv")
    fields = ["query_id", "database", "anchor_record_id", "anchor_first_author", "anchor_year", "classification"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
    print(f"Wrote {path} ({len(rows)} query x database x anchor rows).")
    return rows
