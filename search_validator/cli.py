"""
Usage (run from the directory containing your project folder, or pass --project):

    python -m search_validator.cli --project examples/paper2_example --run all
    python -m search_validator.cli --project examples/paper2_example --run Q07.5
    python -m search_validator.cli --project examples/paper2_example --check-anchors
    python -m search_validator.cli --project examples/paper2_example --anchor-matrix
    python -m search_validator.cli --project examples/paper2_example --deduplicate
    python -m search_validator.cli --project examples/paper2_example --sample
    python -m search_validator.cli --project examples/paper2_example --summarize
    python -m search_validator.cli --project examples/paper2_example --verify-doi 10.1257/aer.97.2.31

Requires: pip install requests pyyaml
"""

import argparse
import sys

from .project import load_project
from .setup_prompts import ensure_settings_interactive
from .engine import (
    run_one, run_all, check_anchors, write_anchor_matrix,
    generate_coding_sample, summarize, verify_doi, write_deduplicated_outputs, generate_html_report,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project", default=".", help="Path to the project folder")
    parser.add_argument("--out", help="Override the output directory from project.yml")
    parser.add_argument("--run", help="Query ID (e.g. Q07.5) or 'all'")
    parser.add_argument("--check-anchors", action="store_true",
                         help="Print database-specific anchor recovery")
    parser.add_argument("--anchor-matrix", action="store_true",
                         help="Write the full query x database x anchor matrix to anchor_matrix.csv")
    parser.add_argument("--deduplicate", action="store_true",
                         help="Deduplicate successful raw exports across queries/databases with provenance")
    parser.add_argument("--report", action="store_true", help="Generate validation_report.html from current outputs")
    parser.add_argument("--sample", action="store_true",
                         help="Generate coding_sample.csv for manual relevance coding")
    parser.add_argument("--summarize", action="store_true",
                         help="Produce pilot_summary.csv")
    parser.add_argument("--verify-doi", help="Look up one DOI via Crossref")
    args = parser.parse_args()

    queries, config, benchmark_csv = load_project(args.project, args.out)

    # Only prompt ahead of commands that actually make live API calls —
    # --summarize/--sample/--check-anchors/--anchor-matrix work entirely
    # from already-downloaded files and don't need any of these settings.
    if args.run or args.verify_doi:
        config = ensure_settings_interactive(queries, config, args.project)

    if args.verify_doi:
        verify_doi(args.verify_doi, config)
        return
    if args.check_anchors:
        if not benchmark_csv:
            print("No benchmark_corpus.csv found in this project — anchor checking needs it.")
            return
        check_anchors(queries, benchmark_csv, config.out_dir, config)
        return
    if args.anchor_matrix:
        if not benchmark_csv:
            print("No benchmark_corpus.csv found in this project — anchor checking needs it.")
            return
        write_anchor_matrix(queries, benchmark_csv, config.out_dir, config)
        return
    if args.deduplicate:
        write_deduplicated_outputs(config.out_dir)
        return
    if args.report:
        generate_html_report(config.out_dir)
        return
    if args.sample:
        generate_coding_sample(config.out_dir)
        return
    if args.summarize:
        summarize(queries, benchmark_csv, config.out_dir, config)
        return
    if not args.run:
        parser.print_help()
        sys.exit(1)

    if args.run == "all":
        run_all(queries, config.out_dir, config)
    else:
        if args.run not in queries:
            print(f"Unknown query id: {args.run}. Known: {sorted(queries.keys())}")
            sys.exit(1)
        run_one(args.run, queries, config.out_dir, config)


if __name__ == "__main__":
    main()
