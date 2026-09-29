"""
Interactive prompting for settings a query run actually needs, but that
project.yml doesn't have yet. Only fires in an interactive terminal (checks
sys.stdin.isatty()) so it never hangs an automated/scripted run — those
still get the existing printed warnings from engine/connectors/*.py instead.

Uses targeted line replacement rather than re-serializing the whole YAML
file, so your comments and formatting in project.yml survive being edited.
"""

import os
import re
import sys


def _write_setting(project_yml_path, key, value):
    with open(project_yml_path, encoding="utf-8") as f:
        text = f.read()
    quoted_value = f'"{value}"' if isinstance(value, str) else str(value)
    new_line = f"{key}: {quoted_value}"
    pattern = re.compile(rf"^{re.escape(key)}:.*$", re.MULTILINE)
    if pattern.search(text):
        text = pattern.sub(new_line, text, count=1)
    else:
        text = text.rstrip("\n") + f"\n{new_line}\n"
    with open(project_yml_path, "w", encoding="utf-8") as f:
        f.write(text)


def ensure_settings_interactive(queries, config, project_dir):
    """Prompts for, and saves, only the settings the routes actually used in
    this project require and don't already have. Returns the (possibly
    updated) config. No-op outside an interactive terminal."""
    if not sys.stdin.isatty():
        return config

    project_yml_path = os.path.join(project_dir, "project.yml")
    if not os.path.exists(project_yml_path):
        return config  # nothing to write back to; skip rather than guess a path

    used_routes = set()
    for spec in queries.values():
        used_routes.update(spec["routes"])

    changed = False

    if config.contact_email == "your-email@example.com" and used_routes & {
        "openalex", "pubmed", "europe_pmc"
    }:
        print("\nOpenAlex/PubMed/Europe PMC ask for a contact email as a condition of "
              "free, keyless access (their 'polite pool').")
        answer = input("Enter your contact email: ").strip()
        if answer:
            config.contact_email = answer
            _write_setting(project_yml_path, "contact_email", answer)
            changed = True

    if "core" in used_routes and not config.core_api_key:
        print("\nCORE is used by this project's queries. Anonymous requests are reliably "
              "rate-limited (429) — a free key fixes that. Register at "
              "https://core.ac.uk/services/api")
        answer = input("Enter your CORE API key (or press Enter to skip and risk rate limiting): ").strip()
        if answer:
            config.core_api_key = answer
            _write_setting(project_yml_path, "core_api_key", answer)
            changed = True

    if "semantic_scholar" in used_routes and not config.semantic_scholar_api_key:
        print("\nSemantic Scholar is used by this project's queries. It works without a key "
              "(shared ~1 req/sec pool), but a free key raises your own rate limit. Register "
              "(optional) at https://www.semanticscholar.org/product/api")
        answer = input("Enter a Semantic Scholar API key, or press Enter to skip: ").strip()
        if answer:
            config.semantic_scholar_api_key = answer
            _write_setting(project_yml_path, "semantic_scholar_api_key", answer)
            changed = True

    if "scopus" in used_routes and not config.scopus_api_key:
        print("\nScopus is used by this project's queries. This requires an INSTITUTIONAL "
              "subscription — a personal key alone will likely fail with 401/403 unless "
              "you're on a recognized campus network or have an Insttoken from your "
              "institution's library. Register at https://dev.elsevier.com if you have "
              "institutional access.")
        answer = input("Enter your Scopus API key, or press Enter to skip: ").strip()
        if answer:
            config.scopus_api_key = answer
            _write_setting(project_yml_path, "scopus_api_key", answer)
            changed = True
            token_answer = input("Enter your Scopus Insttoken too, if you have one (optional, press Enter to skip): ").strip()
            if token_answer:
                config.scopus_insttoken = token_answer
                _write_setting(project_yml_path, "scopus_insttoken", token_answer)

    if "wos" in used_routes and not config.wos_api_key:
        print("\nWeb of Science is used by this project's queries. This requires an "
              "institutional subscription SPECIFICALLY to the Expanded API (WoS has several "
              "API tiers with separate entitlements — check which one your institution "
              "actually licenses). Register via https://developer.clarivate.com if you have "
              "institutional access.")
        answer = input("Enter your Web of Science API key, or press Enter to skip: ").strip()
        if answer:
            config.wos_api_key = answer
            _write_setting(project_yml_path, "wos_api_key", answer)
            changed = True

    if "base" in used_routes and not config.base_api_key:
        print("\nBASE is used by this project's queries. Its access model is inconsistently "
              "documented — usually a free registered key, but BASE may also need to "
              "whitelist your IP separately. Register at "
              "https://www.base-search.net/about/en/api.php")
        answer = input("Enter your BASE API key, or press Enter to skip: ").strip()
        if answer:
            config.base_api_key = answer
            _write_setting(project_yml_path, "base_api_key", answer)
            changed = True

    if "lens" in used_routes and not config.lens_api_key:
        print("\nLens.org is used by this project's queries. Access is free for "
              "non-commercial research use but is APPROVAL-GATED — you apply and wait "
              "for Lens to review it, it's not instant. Apply at "
              "https://www.lens.org/lens/user/subscriptions")
        answer = input("Enter your Lens.org API token, or press Enter to skip: ").strip()
        if answer:
            config.lens_api_key = answer
            _write_setting(project_yml_path, "lens_api_key", answer)
            changed = True

    if "embase" in used_routes and not config.embase_api_key:
        print("\nEmbase is used by this project's queries. Access is granted case-by-case "
              "by Elsevier, regardless of an embase.com subscription — a Scopus key will "
              "NOT work here. Contact an Elsevier Embase representative via "
              "https://dev.elsevier.com/embase_apis.html")
        answer = input("Enter your Embase API key, or press Enter to skip: ").strip()
        if answer:
            config.embase_api_key = answer
            _write_setting(project_yml_path, "embase_api_key", answer)
            changed = True
            token_answer = input("Enter your Embase Insttoken too, if you have one (optional, press Enter to skip): ").strip()
            if token_answer:
                config.embase_insttoken = token_answer
                _write_setting(project_yml_path, "embase_insttoken", token_answer)

    if changed:
        print(f"\nSaved to {project_yml_path} — you won't be asked again.\n")

    return config
