"""Rewrite the artefact counts in README.md from the built artefacts, not from memory.

    python3 audit/2026-11-14-3681/sync_readme_counts.py

Why this exists
---------------
README.md stated "19 pages, 39 tables, 1124 rows" while disk held 20 / 43 / 1234. That
drift has now been found three separate times by three separate checks (finding F2 and
CR-2 from arena/5b80b88a, crosscheck CC-DOC-01, repo-review RR-27). Correcting the digits
by hand fixes it until the next build and no further; generating them fixes it once.

The script rewrites only the parenthesised counts in the line that describes the
generated site, and refuses to touch the file if that pattern is not found exactly once,
so it cannot silently mangle prose.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"
SITE = ROOT / "data" / "site.json"

PATTERN = re.compile(r"\((\d+) pages?, (\d+) tables?, (\d+) rows?\)")


def measure() -> tuple[int, int, int]:
    site = json.loads(SITE.read_text())
    tables = len(site["sections"])
    rows = sum(len(t["rows"]) for t in site["sections"].values()
               if isinstance(t, dict) and "rows" in t)
    pages = 1 + len(list((ROOT / "pages").glob("*.html")))
    return pages, tables, rows


def main() -> int:
    if not SITE.exists():
        print("data/site.json missing — run: python -m nba2.pipeline.build_site_data",
              file=sys.stderr)
        return 2
    pages, tables, rows = measure()
    text = README.read_text()
    found = PATTERN.findall(text)
    if len(found) != 1:
        print(f"expected exactly one '(N pages, M tables, K rows)' block in README.md, "
              f"found {len(found)}; leaving the file alone", file=sys.stderr)
        return 3
    new = PATTERN.sub(f"({pages} pages, {tables} tables, {rows} rows)", text, count=1)
    if new == text:
        print(f"README counts already current ({pages}/{tables}/{rows}); nothing to do")
        return 0
    README.write_text(new)
    print(f"README counts -> {pages} pages, {tables} tables, {rows} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
