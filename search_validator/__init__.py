"""search_validator — benchmark-driven search-strategy validation engine.

Engine code (this package) is generic: it knows how to talk to OpenAlex,
PubMed, Europe PMC, ERIC and OpenAIRE, how to match results against a
benchmark corpus, and how to build a coding sample and a pilot summary.

It knows nothing about any specific study's queries, families, or anchors —
that lives entirely in a project folder (see project_template/) supplied at
run time. Paper 2 is the first project that uses this engine, not part of
the engine itself.
"""

__version__ = "0.1.0-dev"
