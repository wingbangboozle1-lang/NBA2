"""python -m nba2.v7 — build the v7 pages, add them to the nav, print the check summary."""

from __future__ import annotations

import json
import sys

from . import build as B
from . import flags as FL
from . import nav as NAV


def main() -> int:
    out = B.build()
    nav = NAV.run()
    fl = FL.run()
    checks = out["checks"]
    gates = out["gates"]
    print(f"v7: built {len(out['pages'])} pages: {', '.join(out['pages'])}")
    print(json.dumps({
        "n_checks": len(checks),
        "n_checks_ok": sum(1 for c in checks if c["ok"]),
        "n_gates": len(gates),
        "n_gates_pass": sum(1 for g in gates if g["status"] == "PASS"),
        "gates_blocked": [g["id"] for g in gates if g["status"] != "PASS"],
        "failing_checks": [c["id"] for c in checks if not c["ok"]],
        "nav": nav,
        "flags": fl,
    }, indent=1))
    # Re-adding the section is the normal path: v2 regenerates site/flagged.html on every
    # rebuild, which drops the appended section, so v7 must put it back every time. What must
    # never happen is the section being absent after the run.
    ok = all(c["ok"] for c in checks) and nav["href_set_preserved"] and fl["section_present"]
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
