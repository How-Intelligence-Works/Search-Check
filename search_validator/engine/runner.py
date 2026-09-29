import csv
import os
from datetime import datetime, timezone

from .schema import LOG_FIELDS, ROW_FIELDS
from .connectors import REGISTRY


def append_search_log(log_path, **kwargs):
    new_file = not os.path.exists(log_path)
    with open(log_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        if new_file: writer.writeheader()
        row = {k: "" for k in LOG_FIELDS}; row.update(kwargs); writer.writerow(row)


def write_rows_csv(rows, path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ROW_FIELDS); writer.writeheader(); writer.writerows(rows)


def run_one(query_id, queries, out_dir, config):
    spec = queries[query_id]
    os.makedirs(out_dir, exist_ok=True)
    log_path = os.path.join(out_dir, "search_log.csv")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    print(f"{query_id} — {spec.get('substream', '')}")
    for route in spec["routes"]:
        if route not in REGISTRY:
            print(f"  Unknown route '{route}' for {query_id} — skipping (known routes: {sorted(REGISTRY)})"); continue
        connector = REGISTRY[route]; db_name = connector.NAME; trans = connector.TRANSLATION
        path = os.path.join(out_dir, f"{query_id}_{route}_{run_id}.csv")
        try:
            q, rows, total_hits = connector.run(query_id, spec, config)
            retrieved = len(rows)
            truncated = "Y" if (total_hits not in (None, "") and retrieved < int(total_hits)) else "N"
            write_rows_csv(rows, path)
            print(f"  [{db_name}] {retrieved}/{total_hits} hits {'(TRUNCATED)' if truncated == 'Y' else ''} -> {path}")
            append_search_log(log_path, run_id=run_id, query_id=query_id, database=db_name,
                translation_version=trans["version"], translation_status=trans["status"],
                date_run=datetime.now(timezone.utc).isoformat(), translated_query=q,
                total_hits_reported=total_hits, records_retrieved=retrieved,
                retrieval_truncated=truncated, export_filename=os.path.abspath(path), status="OK")
        except Exception as e:
            print(f"  [{db_name}] ERROR: {e}")
            append_search_log(log_path, run_id=run_id, query_id=query_id, database=db_name,
                translation_version=trans["version"], translation_status=trans["status"],
                date_run=datetime.now(timezone.utc).isoformat(), translated_query=spec["text"],
                total_hits_reported="", records_retrieved=0, retrieval_truncated="",
                export_filename=os.path.abspath(path), status="ERROR", error_message=f"{type(e).__name__}: {e}")


def run_all(queries, out_dir, config):
    os.makedirs(out_dir, exist_ok=True)
    for qid in queries: run_one(qid, queries, out_dir, config)
