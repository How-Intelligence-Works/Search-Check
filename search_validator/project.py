"""
Turns a project folder into what the engine needs: a `queries` dict and a
Config. This is the only file that knows about file formats (CSV/YAML) —
the engine itself only ever sees plain Python data structures, so a future
project could load queries from a database or a spreadsheet without the
engine changing at all.

Expected project folder layout:
    project.yml            — contact_email, download_cap, etc. (optional; defaults apply)
    queries.csv             — one row per registered query (see column spec below)
    benchmark_corpus.csv    — the hand-curated benchmark, only needed for
                               anchor checking / precision summaries

queries.csv columns:
    query_id, family, substream, text, anchors, anchor_ids, routes
    - anchors: semicolon-separated author surnames, or blank
    - routes:  semicolon-separated connector names, matching
               search_validator.engine.connectors.REGISTRY keys
               (openalex; pubmed; europe_pmc; eric; openaire)
"""

import csv
import os

import yaml

from .engine.schema import Config
from .engine.connectors import REGISTRY as CONNECTOR_REGISTRY


def load_queries(queries_csv):
    queries = {}
    with open(queries_csv, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            qid = row["query_id"].strip()
            routes = [r.strip() for r in row["routes"].split(";") if r.strip()]
            unknown = [r for r in routes if r not in CONNECTOR_REGISTRY]
            if unknown:
                raise ValueError(
                    f"{queries_csv}, query {qid}: unknown route(s) {unknown}. "
                    f"Known routes: {sorted(CONNECTOR_REGISTRY)}"
                )
            queries[qid] = {
                "family": row.get("family", "").strip(),
                "substream": row.get("substream", "").strip(),
                "text": row["text"].strip(),
                "anchors": [a.strip() for a in row.get("anchors", "").split(";") if a.strip()],
                "anchor_ids": [a.strip() for a in row.get("anchor_ids", "").split(";") if a.strip()],
                "routes": routes,
            }
    return queries


def load_config(project_dir, project_yml, out_dir_override=None):
    settings = {}
    if project_yml and os.path.exists(project_yml):
        with open(project_yml, encoding="utf-8") as f:
            settings = yaml.safe_load(f) or {}

    kwargs = {}
    for key in ("contact_email", "download_cap", "max_pages", "sleep_seconds", "out_dir",
                "core_api_key", "semantic_scholar_api_key",
                "scopus_api_key", "scopus_insttoken", "wos_api_key",
                "base_api_key", "lens_api_key", "embase_api_key", "embase_insttoken"):
        if key in settings:
            kwargs[key] = settings[key]
    if "verified_indexing_databases" in settings:
        kwargs["verified_indexing_databases"] = set(settings["verified_indexing_databases"])
    if out_dir_override:
        kwargs["out_dir"] = out_dir_override

    config = Config(**kwargs)
    # out_dir is always resolved relative to the PROJECT folder, never to
    # wherever the command happens to be run from — a relative out_dir that
    # silently pointed at the current working directory was a real bug
    # caught by testing this against synthetic results (see engine tests).
    if not os.path.isabs(config.out_dir):
        config.out_dir = os.path.join(project_dir, config.out_dir)

    if config.contact_email == "your-email@example.com":
        print("WARNING: contact_email is still the default placeholder — set it in "
              "project.yml. OpenAlex/PubMed/Europe PMC ask for a real contact email "
              "as a condition of their free, keyless access (the 'polite pool').")
    return config


def load_project(project_dir, out_dir_override=None):
    """Convenience loader: given a project folder, return (queries, config, benchmark_csv_path)."""
    queries_csv = os.path.join(project_dir, "queries.csv")
    project_yml = os.path.join(project_dir, "project.yml")
    benchmark_csv = os.path.join(project_dir, "benchmark_corpus.csv")

    if not os.path.exists(queries_csv):
        raise FileNotFoundError(f"No queries.csv found in {project_dir}")

    queries = load_queries(queries_csv)
    config = load_config(project_dir, project_yml, out_dir_override)
    benchmark_csv = benchmark_csv if os.path.exists(benchmark_csv) else None
    return queries, config, benchmark_csv


def verify_queries_against_export(queries, expected_ids):
    """Consistency check: does the loaded project have every query ID you expect?
    A project can call this with its own expected-ID set (e.g. from an earlier
    registry export) to catch silent drift the way the original v4 script did."""
    missing = set(expected_ids) - set(queries.keys())
    extra = set(queries.keys()) - set(expected_ids)
    if missing:
        print(f"WARNING: expected query IDs missing from queries.csv: {sorted(missing)}")
    if extra:
        print(f"WARNING: queries.csv has IDs not in the expected set: {sorted(extra)}")
    if not missing and not extra:
        print(f"OK: all {len(expected_ids)} expected query IDs present.")
