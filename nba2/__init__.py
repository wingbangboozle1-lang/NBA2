"""NBA2 — originated NBA lines, signals, and picks platform.

Two code paths coexist here after parallel sessions merged into `main`:

* `nba2/model.py`, `picks.py`, `strategies.py`, `correlations.py`, `injuries.py`, `sources.py`,
  `generate.py` (+ `nba2/data/*.json`) — the earlier session's origination pipeline, still the
  source of the root-level `*.html` pages. Kept working; not imported by this package.
* `nba2/config.py`, `provenance.py`, `models/`, `pipeline/`, `tests/` — the gated research
  engine that renders `index.html` + `pages/**` from `data/site.json`.

Nothing is imported at package level: the two paths have different data contracts, and an import
side effect would make one session's tooling fail for reasons that have nothing to do with it.
"""

__all__ = ["config", "models", "pipeline", "provenance"]
