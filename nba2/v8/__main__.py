"""Build the v8 pages. Runs LAST in the chain: it appends its nav block to pages v2..v6 wrote."""
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
