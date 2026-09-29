"""
Reproducible sampling for manual relevance coding. This module never
classifies relevance itself — see the CODING_FIELDS comment in schema.py.
"""

import csv
import os
import random

from .schema import CODING_FIELDS
from .results import latest_logs


def generate_coding_sample(results_dir, n_first=10, n_random=10, seed=42):
    log_path = os.path.join(results_dir, "search_log.csv")
    if not os.path.exists(log_path):
        print("No search_log.csv found — run some queries first.")
        return
    log_rows = [r for r in latest_logs(results_dir) if r.get("status") == "OK"]

    sample_rows = []
    for log_row in log_rows:
        path = log_row["export_filename"]
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            records = list(csv.DictReader(f))
        if not records:
            continue

        first_n = records[:n_first]
        rng = random.Random(seed)
        remaining = records[n_first:]
        random_n = rng.sample(remaining, min(n_random, len(remaining))) if remaining else []

        for rec, sample_type in [(r, "first_N") for r in first_n] + \
                                  [(r, "random_seed" + str(seed)) for r in random_n]:
            sample_rows.append({
                "query_id": rec["query_id"], "database": rec["database"],
                "record_id": rec["id"], "title": rec["title"], "year": rec["year"],
                "sample_type": sample_type,
            })

    out_path = os.path.join(results_dir, "coding_sample.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CODING_FIELDS)
        writer.writeheader()
        for row in sample_rows:
            full_row = {k: "" for k in CODING_FIELDS}
            full_row.update(row)
            writer.writerow(full_row)
    print(f"Wrote {out_path}: {len(sample_rows)} records to code by hand "
          f"(up to {n_first} first + {n_random} random per query x database).")
    print("This does not classify relevance for you — fill in the "
          "relevance/mechanism/notes columns, then run summarize again.")


def read_coding_sample(results_dir):
    path = os.path.join(results_dir, "coding_sample.csv")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    by_qd = {}
    for r in rows:
        by_qd.setdefault((r["query_id"], r["database"]), []).append(r)
    return by_qd
