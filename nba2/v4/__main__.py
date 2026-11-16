"""Entry point: build the v4 pages, run the gates, and publish nothing unless they pass.

Order matters and mirrors the brief:

1. **capture**    — rewrite the frozen official snapshot from the committed reading. Fails
                    closed if the capture's own selftest fails.
2. **injury**     — store the releases and diff consecutive ones.
3. **gates**      — freshness + provenance. If any gate fails we stop *before* rendering, so
                    a stale or unsourced snapshot can never reach the published tree.
4. **render**     — write the v4 pages into ``site/``.
5. **settlement** — grade the sealed ledger against verified finals and keep the stamp.
6. **check**      — structural, surface-wall and numeric verification on the emitted HTML.
"""

from __future__ import annotations

import json

from . import check as CH
from . import injury_diff as ID
from . import model as M
from . import publish as P
from . import settlement as S
from . import write_capture as WC


def build() -> tuple[list[str], dict]:
    written = WC.write()
    inj = ID.write()

    gates = CH.gates(CH.build_docs())
    failed = [g for g in gates if not g["ok"]]
    if failed:
        for g in failed:
            print(f"GATE FAILED {g['id']}: {g['measured']} - {g['detail']}")
        raise SystemExit("v4 build aborted: a freshness/provenance gate failed, "
                         "nothing rendered and the site was not rebuilt")

    res = M.build()
    settle_doc = S.settle()
    verify = S.verify_settlement()
    settle_doc["_verify"] = verify

    checks = {"gates": gates, "settlement_verify": verify,
              "capture_files": written + inj}
    pages = P.build(res, settle_doc, checks)
    # Post-build measurement, then one page re-render so the verification page shows the
    # gates that can only be measured on emitted HTML (the projection/bet wall).
    result = CH.run()
    checks["gates"] = result["gates"]
    checks["surface_wall"] = result["surface_wall"]
    P.inject_nav()
    P.rerender_verify(res, settle_doc, checks)
    data = P.write_data(res, {k: v for k, v in settle_doc.items()}, checks)
    return pages, {"capture": written, "injury": inj, "data": data,
                   "checks": {"n_gates_pass": result["n_gates_pass"],
                              "n_gates_fail": result["n_gates_fail"],
                              "publishable": result["publishable"],
                              "ok": result["ok"],
                              "structural": len(result["structural"]),
                              "surface_wall": len(result["surface_wall"]),
                              "numeric": len(result["numeric"])}}


if __name__ == "__main__":
    pages, summary = build()
    print(f"built {len(pages)} v4 pages: {', '.join(pages)}")
    print(json.dumps(summary["checks"], indent=1))
