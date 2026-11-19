"""``python -m nba2.v6`` — measure, gate, render, and wire the v6 pages into the site.

Order matters and is: **measure → gate → render → group the navigation**. Rendering before
the gates would let a failing build write pages; grouping the nav before rendering would
miss this tree's own six pages.

The module reads nothing from the network and touches no page body that another tree owns.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from . import inventory as INV
from . import market_prior as MP
from . import nav as NAV
from . import player_coverage as PC
from . import publish as PUB
from . import results_coverage as RC
from .common import ROOT, SITE, V6

DATA_FILES = {
    "injury_archive.json": None,
    "results_coverage.json": None,
    "player_coverage.json": None,
    "market_prior.json": None,
    "endpoints.json": None,
    "checks.json": None,
}


def build(write: bool = True) -> tuple[list[str], dict]:
    rels = INV.injury_releases()
    cov = RC.build()
    pc = PC.build()
    mp = MP.build()
    ep = INV.endpoints()
    verdict = INV.refresh_verdict()

    # gate BEFORE rendering: a failed gate stops the write.
    from . import check as CH
    from . import flags as FL
    checks = CH.run()
    if not checks["publishable"]:
        hard = [g for g in checks["gates"] if g["hard"] and not g["ok"]]
        print("v6: HARD GATE FAILURE — nothing is rendered")
        for g in hard:
            print(f"  {g['id']}: {g['name']}")
            for f in g["failures"][:10]:
                print(f"      ! {f}")
        raise SystemExit(1)

    pages = {
        "injury-archive.html": PUB.page_injury_archive(rels),
        "results-coverage.html": PUB.page_results_coverage(cov),
        "player-coverage.html": PUB.page_player_coverage(pc),
        "market-prior.html": PUB.page_market_prior(mp),
        "endpoints.html": PUB.page_endpoints(ep, verdict),
        "v6-verify.html": PUB.page_verify(checks, {}),
    }
    written = []
    if write:
        V6.mkdir(parents=True, exist_ok=True)
        SITE.mkdir(parents=True, exist_ok=True)
        for name, body in pages.items():
            title = dict(PUB.V6_NAV)[name]
            (SITE / name).write_text(
                PUB.page(title, name, body,
                         lede=_lede(name, rels, cov, pc, mp),
                         crumbs="Dashboard › " + title))
            written.append(name)

        # data copies, so a reader can check the page against the numbers
        docs = {"injury_archive.json": {"schema": "nba2.v6.injury-archive.v1",
                                        "session": "arena/f5ac4e74-nba2",
                                        "n_releases": len(rels), "releases": rels},
                "results_coverage.json": cov,
                "player_coverage.json": pc,
                "market_prior.json": mp,
                "endpoints.json": ep,
                "checks.json": checks}
        for name, doc in docs.items():
            (V6 / name).write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")

        # the verify page is re-rendered with the page gate now that the pages exist
        checks2 = CH.run(pages=list(pages))
        (SITE / "v6-verify.html").write_text(
            PUB.page("v6 verification", "v6-verify.html",
                     PUB.page_verify(checks2, {}),
                     lede="Every gate below is a count over committed rows. Nothing is "
                          "asserted that was not measured.",
                     crumbs="Dashboard › v6 verification"))
        (V6 / "checks.json").write_text(
            json.dumps(checks2, indent=1, ensure_ascii=False) + "\n")
        checks = checks2
        if not checks["publishable"]:
            print("v6: page-level gate failed after render")
            for g in checks["gates"]:
                if not g["ok"]:
                    for f in g["failures"][:10]:
                        print(f"  {g['id']} ! {f}")
            raise SystemExit(1)

        # K-06: grouped navigation + landing cards, last, after every tree has rendered
        css_changed = NAV.ensure_css()
        injected = NAV.inject_nav()
        flagged = FL.append_to_flagged()
        FL.write_data()
        cards = NAV.landing_cards()
        nav_report = NAV.rewrite_nav()
        if not nav_report["href_set_preserved"]:
            print("v6: NAV REGROUP CHANGED THE LINK SET — reverting nothing, failing loudly")
            for pr in nav_report["problems"][:10]:
                print("  !", pr)
            raise SystemExit(1)
    else:
        nav_report = {"n_pages": 0, "n_links": 0, "href_set_preserved": True, "problems": []}
        injected = 0
        css_changed = cards = flagged = False

    return written, {"n_gates": checks["n_gates"],
                     "n_gates_pass": checks["n_gates_pass"],
                     "publishable": checks["publishable"],
                     "nav_pages": nav_report["n_pages"],
                     "nav_links": nav_report["n_links"],
                     "nav_injected": injected,
                     "href_set_preserved": nav_report["href_set_preserved"],
                     "landing_cards": bool(cards),
                     "flagged_appended": bool(flagged),
                     "css_appended": bool(css_changed),
                     "counts": checks["counts"]}


def _lede(name: str, rels, cov, pc, mp) -> str:
    n_bytes = sum(1 for r in rels if r["bytes_stored"])
    if name == "injury-archive.html":
        return ("Every official injury report this repository knows about, with its revision "
                f"stamp, its retrieval time and whether its bytes are archived: "
                f"<b>{n_bytes} of {len(rels)}</b> are. The rest are listed with the reason.")
    if name == "results-coverage.html":
        return ("How much of the official result feed is actually committed, per game date: "
                f"<b>{cov['n_games_with_final']} of {cov['n_games_known']}</b> games have an "
                f"official final and <b>{cov['n_games_graded']}</b> are settled against a "
                "sealed ledger. One row per game: date, teams, final, quarter scores.")
    if name == "player-coverage.html":
        return ("Per-player game logs for the players named on an official injury report — "
                f"measured coverage <b>{pc['n_matched']} of {pc['n_report_rows']}</b> "
                f"({pc['coverage']}). Minutes, points, rebounds, assists and opponent, "
                "exactly as the official gamebook printed them.")
    if name == "market-prior.html":
        return ("Blend the model line with the closing line, weighted by measured "
                "out-of-sample log-loss. The rule is pre-registered and published; the "
                "weight is <b>blank</b>, because no closing line has ever been captured.")
    if name == "endpoints.html":
        return ("Which official endpoints a runner can actually reach, measured and "
                "timestamped — the evidence behind every 'we could not read that' statement "
                "on this site.")
    return "v6 gates and measurements."


def main(argv: list[str] | None = None) -> int:
    check_only = "--check-only" in (argv or sys.argv[1:])
    written, report = build(write=not check_only)
    print(f"v6: built {len(written)} pages: {', '.join(written) if written else '(check only)'}")
    print("v6: " + json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
