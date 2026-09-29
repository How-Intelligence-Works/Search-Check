"""Generate a dependency-free HTML validation report from result CSVs."""
import csv, html, os
from datetime import datetime, timezone


def _read(path):
    if not os.path.exists(path): return []
    with open(path, encoding="utf-8-sig") as f: return list(csv.DictReader(f))


def generate_html_report(results_dir, project_name="Search validation project"):
    summary = _read(os.path.join(results_dir, "pilot_summary.csv"))
    dedup = _read(os.path.join(results_dir, "deduplicated_records.csv"))
    prov = _read(os.path.join(results_dir, "dedup_provenance.csv"))
    review = _read(os.path.join(results_dir, "dedup_review_candidates.csv"))
    logs = _read(os.path.join(results_dir, "search_log.csv"))
    ok = sum(r.get("status") == "OK" for r in logs); err = sum(r.get("status") == "ERROR" for r in logs)
    def esc(x): return html.escape(str(x or ""))
    rows = "".join(
        "<tr>" + "".join(f"<td>{esc(r.get(k,''))}</td>" for k in
        ["query_id","database","records_retrieved","anchor_sensitivity","strict_precision","broad_precision","weighted_relevance_yield"]) + "</tr>"
        for r in summary
    ) or '<tr><td colspan="7">No pilot summary yet. Generate/copy a coding sample, code it, then summarize.</td></tr>'
    body = f'''<!doctype html><html><head><meta charset="utf-8"><title>{esc(project_name)} — Search Validation Report</title>
<style>body{{font-family:system-ui,sans-serif;max-width:1100px;margin:40px auto;padding:0 20px;line-height:1.45}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ddd;padding:7px;text-align:left;vertical-align:top}}th{{background:#f4f4f4}}.cards{{display:flex;gap:12px;flex-wrap:wrap}}.card{{border:1px solid #ddd;padding:12px 16px;border-radius:8px;min-width:150px}}code{{background:#f4f4f4;padding:2px 4px}}</style></head><body>
<h1>{esc(project_name)}</h1><p>Generated {esc(datetime.now(timezone.utc).isoformat())}. This report distinguishes verified benchmark sensitivity from unknown indexing status and keeps relevance judgments human-coded.</p>
<div class="cards"><div class="card"><b>Successful logged runs</b><br>{ok}</div><div class="card"><b>Errors logged</b><br>{err}</div><div class="card"><b>Deduplicated records</b><br>{len(dedup) if dedup else 'not generated'}</div><div class="card"><b>Raw occurrences in provenance</b><br>{len(prov) if prov else 'not generated'}</div><div class="card"><b>Dedup review groups</b><br>{len(review) if review else 'not generated'}</div></div>
<h2>Query × database diagnostics</h2><table><thead><tr><th>Query</th><th>Database</th><th>Retrieved</th><th>Verified anchor sensitivity</th><th>Strict precision</th><th>Broad precision</th><th>Weighted relevance yield</th></tr></thead><tbody>{rows}</tbody></table>
<h2>Interpretation safeguards</h2><ul><li><b>Anchor sensitivity</b> is calculated only where benchmark indexing is verified for that database.</li><li><b>Strict precision</b> = relevant / valid coded sample; <b>broad precision</b> = (relevant + partial) / valid coded sample.</li><li><b>Weighted relevance yield</b> uses relevant=1, partial=0.5, irrelevant=0 and is not labelled precision.</li><li>Deduplication auto-merges DOI matches or title+year+first-author matches. Title+year-only collisions are flagged for review, not merged.</li></ul>
</body></html>'''
    path = os.path.join(results_dir, "validation_report.html")
    with open(path, "w", encoding="utf-8") as f: f.write(body)
    print(f"Wrote {path}")
    return path
