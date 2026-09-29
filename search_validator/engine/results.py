"""Helpers for resolving the latest run/export per query/database."""
import csv, os


def all_logs(results_dir):
    path = os.path.join(results_dir, "search_log.csv")
    if not os.path.exists(path): return []
    with open(path, encoding="utf-8-sig") as f: return list(csv.DictReader(f))


def latest_logs(results_dir):
    latest = {}
    for i, r in enumerate(all_logs(results_dir)):
        latest[(r.get("query_id", ""), r.get("database", ""))] = (i, r)
    return [v[1] for v in sorted(latest.values(), key=lambda x: x[0])]


def latest_successful_logs(results_dir):
    latest = {}
    for i, r in enumerate(all_logs(results_dir)):
        if r.get("status") == "OK": latest[(r.get("query_id", ""), r.get("database", ""))] = (i, r)
    return [v[1] for v in sorted(latest.values(), key=lambda x: x[0])]


def latest_export_for(results_dir, query_id, database):
    # Use the latest run only. If the latest run failed, do not silently fall
    # back to an older successful export and present stale results as current.
    for r in latest_logs(results_dir):
        if r.get("query_id") == query_id and r.get("database") == database:
            if r.get("status") != "OK": return None
            p = r.get("export_filename", "")
            if p and os.path.exists(p): return p
            if p:
                alt = os.path.join(results_dir, os.path.basename(p))
                if os.path.exists(alt): return alt
    return None
