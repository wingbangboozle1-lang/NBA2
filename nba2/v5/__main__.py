"""Entry point: rebuild the v5 data files and pages, but only if the gates pass.

Order:
1. load the committed official gamebook transcripts (no network — the fetch happened
   in-session through the platform page-fetch tool);
2. run the eight gates fail-closed; a hard failure renders nothing;
3. derive the result feed, the minutes shares, the replacement shares and the injury join;
4. render four pages into ``site/`` and inject the v5 links into the shared navigation.
"""

from __future__ import annotations

import json

from . import model as M
from . import publish as P


def build() -> tuple[list[str], dict]:
    res = M.build()
    pages, summary = P.build(res)
    return pages, summary


if __name__ == "__main__":
    pages, summary = build()
    print(f"built {len(pages)} v5 pages: {', '.join(pages)}")
    print(f"gates: {summary['n_gates_pass']}/{summary['n_gates']} pass; "
          f"nav injected into {summary['injected_nav']} page(s)")
    print("data: " + ", ".join(summary["data"]))
    print(json.dumps({k: v for k, v in summary.items() if k != "data"}, indent=1))
