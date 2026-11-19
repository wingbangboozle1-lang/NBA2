"""Build the v8 pages.

Runs after v5 and **before v6**: it renders three pages and appends its own nav block to the pages
v2..v5 wrote, then v6 groups the whole sidebar into categories — and v8's three pages are listed in
``nba2/v6/nav.py`` CATEGORIES so they land in a category instead of falling into "Other pages".
"""
from __future__ import annotations

import sys

from .build import build


def main() -> int:
    res = build()
    print(f"v8: wrote {len(res['pages'])} pages ({', '.join(res['pages'])}); "
          f"nav block added to {res['nav_injected']} existing pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
