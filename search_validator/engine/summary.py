import csv
import os
from collections import Counter

from .schema import CODING_FIELDS
from .anchors import check_anchors
from .sampling import read_coding_sample
from .results import latest_logs

RELEVANCE_FIELD = CODING_FIELDS[6]
MECHANISM_FIELD = CODING_FIELDS[7]


def summarize(queries, benchmark_csv, results_dir, config):
    log_path = os.path.join(results_dir, "search_log.csv")
    out_path = os.path.join(results_dir, "pilot_summary.csv")
    if not os.path.exists(log_path):
        print(f"No search_log.csv found at {log_path} — run some queries first.")
        return
    log_rows = latest_logs(results_dir)

    anchor_rows = []
    if benchmark_csv and os.path.exists(benchmark_csv):
        anchor_rows = check_anchors(queries, benchmark_csv, results_dir, config, verbose=False)
    anchor_by_qd = {}
    for r in anchor_rows:
        anchor_by_qd.setdefault((r["query_id"], r["database"]), []).append(r)

    coding_by_qd = read_coding_sample(results_dir)
    summary_fields = [
        "query_id", "database", "family", "status", "total_hits_reported",
        "records_retrieved", "retrieval_truncated", "anchor_rows_assessed",
        "verified_indexed_anchor_denominator", "anchors_recovered",
        "anchor_sensitivity", "anchor_indexing_unknown", "anchor_not_indexed",
        "anchor_candidates_requiring_review", "sample_size", "n_relevant",
        "n_partial", "n_irrelevant", "n_pending_coding", "strict_precision",
        "broad_precision", "weighted_relevance_yield", "dominant_false_positive_mechanism",
        "decision (KEEP/REVISE/SPLIT/MERGE — FILL IN)",
    ]
    out_rows = []
    for log_row in log_rows:
        qid, db = log_row["query_id"], log_row["database"]
        a_rows = anchor_by_qd.get((qid, db), [])
        recovered_rows = [r for r in a_rows if r["classification"].startswith("RECOVERED")]
        missing_verified = [r for r in a_rows if r["classification"].startswith("MISSING")]
        verified_denom = len(recovered_rows) + len(missing_verified)
        sensitivity = f"{len(recovered_rows)/verified_denom:.0%}" if verified_denom else "n/a"
        unknown = sum(1 for r in a_rows if r["classification"].startswith("indexing status unknown"))
        not_indexed = sum(1 for r in a_rows if r["classification"].startswith("NOT_INDEXED"))
        candidates = sum(1 for r in a_rows if r["classification"].startswith("CANDIDATE_REQUIRES_REVIEW"))

        c_rows = coding_by_qd.get((qid, db), [])
        coded = [r for r in c_rows if r.get(RELEVANCE_FIELD, "").strip()]
        pending = len(c_rows) - len(coded)
        labels = [r[RELEVANCE_FIELD].strip().lower() for r in coded]
        n_rel, n_partial, n_irrel = labels.count("relevant"), labels.count("partial"), labels.count("irrelevant")
        valid_n = n_rel + n_partial + n_irrel
        strict = f"{n_rel/valid_n:.0%}" if valid_n else "PENDING MANUAL CODING"
        broad = f"{(n_rel+n_partial)/valid_n:.0%}" if valid_n else "PENDING MANUAL CODING"
        weighted = f"{(n_rel+0.5*n_partial)/valid_n:.0%}" if valid_n else "PENDING MANUAL CODING"
        mechanisms = [r.get(MECHANISM_FIELD, "").strip() for r in coded if r.get(MECHANISM_FIELD, "").strip()]
        dominant = Counter(mechanisms).most_common(1)[0][0] if mechanisms else ""

        out_rows.append({
            "query_id": qid, "database": db, "family": queries.get(qid, {}).get("family", ""),
            "status": log_row.get("status", ""), "total_hits_reported": log_row.get("total_hits_reported", ""),
            "records_retrieved": log_row.get("records_retrieved", ""), "retrieval_truncated": log_row.get("retrieval_truncated", ""),
            "anchor_rows_assessed": len(a_rows), "verified_indexed_anchor_denominator": verified_denom,
            "anchors_recovered": len(recovered_rows), "anchor_sensitivity": sensitivity,
            "anchor_indexing_unknown": unknown, "anchor_not_indexed": not_indexed,
            "anchor_candidates_requiring_review": candidates, "sample_size": len(c_rows),
            "n_relevant": n_rel, "n_partial": n_partial, "n_irrelevant": n_irrel,
            "n_pending_coding": pending, "strict_precision": strict, "broad_precision": broad,
            "weighted_relevance_yield": weighted, "dominant_false_positive_mechanism": dominant,
            "decision (KEEP/REVISE/SPLIT/MERGE — FILL IN)": "",
        })

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=summary_fields); w.writeheader(); w.writerows(out_rows)
    n_ok = sum(1 for r in log_rows if r.get("status") == "OK")
    n_err = sum(1 for r in log_rows if r.get("status") == "ERROR")
    print(f"Wrote {out_path}: {len(out_rows)} query x database runs ({n_ok} OK, {n_err} errors).")
