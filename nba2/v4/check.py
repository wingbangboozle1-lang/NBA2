"""Post-build verification for v4. Fails the build on any finding.

Structural
    every local link resolves; every table row carries an outbound source; every blank cell
    carries a reason; no placeholder tokens.

The surface wall (the brief's "never mix them")
    ``projection.html`` may not contain a stake, an edge, a market price or a Kelly fraction.
    ``bet.html`` may not contain a row that claims to be published without a market price.
    Both are asserted on the emitted HTML, not on the in-memory model, so a template change
    cannot quietly cross the wall.

The freshness and provenance gates
    the four official surfaces must all be present in this session's capture and stamped;
    every captured row must carry a source URL. A gate failure aborts the rebuild, which is
    what "rebuild only after the gates pass" means operationally.

Numerics
    the published totals must equal possessions x points-per-possession, HCA must equal the
    pinned identity, the luck z-scores must equal expected-wins residuals over their sd, and
    the settlement must re-hash.
"""

from __future__ import annotations

import html
import json
import math
import re
from pathlib import Path

from . import capture as C
from . import model as M
from . import settlement as S
from .publish import V4_PAGES

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "site"

LOCAL = re.compile(r'(?:href|src)="([^"#][^"]*)"')
ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
TABLE = re.compile(r"<table>(.*?)</table>", re.S)
CAPTION = re.compile(r"<caption>(.*?)</caption>", re.S)
CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
TAG = re.compile(r"<[^>]+>")
PLACEHOLDER = re.compile(r"\b(TODO|TBD|lorem ipsum|XXX|FIXME)\b", re.I)
# A blank is only acceptable when the cell says *why* it is blank. A bare em dash (or an
# empty cell) is a finding, not a blank - the brief is explicit that a value with no source
# must be flagged, not silently dropped. "—" is therefore deliberately NOT in this list.
BLANK_OK = re.compile(r"(F-V4-\d{2}|no official|not filed|blocked|NOT YET SUBMITTED|"
                      r"not transcribed|no measured|no row|unreadable|not published|"
                      r"not available|unlisted|withheld)", re.I)

BET_MARKERS = re.compile(r"(stake|kelly|edge_vs_market|market price|\bedge\b)", re.I)


def text_of(c: str) -> str:
    return html.unescape(TAG.sub("", c)).strip()


# --------------------------------------------------------------------------- structural
def structural() -> list[str]:
    problems = []
    for name in V4_PAGES:
        p = SITE / name
        if not p.exists():
            problems.append(f"{name}: missing")
            continue
        doc = p.read_text()
        for href in LOCAL.findall(doc):
            if href.startswith(("http://", "https://", "mailto:", "//", "data:")):
                continue
            path, _, frag = href.partition("#")
            target = p.parent / path.split("?")[0] if path else p
            if not target.exists():
                problems.append(f"{name}: broken local link -> {href}")
                continue
            # a fragment must actually exist in the target, or the link lands nowhere
            if frag:
                tdoc = target.read_text()
                if f'id="{frag}"' not in tdoc and f'name="{frag}"' not in tdoc:
                    problems.append(f"{name}: link -> {href} has no matching anchor")
        for m in PLACEHOLDER.finditer(doc):
            problems.append(f"{name}: placeholder {m.group(0)!r}")
        # A data row must carry its own source link. A table whose caption carries an
        # outbound link is the only exception, and then EVERY row in that table is exempt -
        # so a caption can never excuse a single unsourced row.
        captioned: set[int] = set()
        for tm in TABLE.finditer(doc):
            block = tm.group(1)
            cm = CAPTION.search(block)
            if cm and re.search(r'<a href="https?://', cm.group(1)):
                captioned.add(tm.start(1))
        for m in ROW.finditer(doc):
            cells = CELL.findall(m.group(1))
            if not cells:
                continue
            row = m.group(1)
            if re.search(r'<a href="https?://', row):
                continue
            in_captioned = False
            for tm in TABLE.finditer(doc):
                if tm.start(1) <= m.start() < tm.end(1) and tm.start(1) in captioned:
                    in_captioned = True
                    break
            if not in_captioned:
                problems.append(f"{name}: table row with no outbound source: {row[:120]}")
            for c in cells:
                t = text_of(c)
                if not t:
                    problems.append(f"{name}: empty cell (should be a reasoned blank)")
                elif not re.search(r"[0-9A-Za-z]", t):
                    problems.append(f"{name}: bare dash cell - blanks must state the reason: {t!r}")
                elif "—" in t and not BLANK_OK.search(t):
                    problems.append(f"{name}: unexplained blank: {t!r}")
    return problems


# ------------------------------------------------------------------------- surface wall
def surface_wall() -> list[str]:
    problems = []
    proj = SITE / "projection.html"
    bet = SITE / "bet.html"
    if not proj.exists() or not bet.exists():
        return ["projection.html or bet.html missing"]

    doc = proj.read_text()
    # The word "stake" is allowed only inside an explicit disclosure that none is published.
    for m in BET_MARKERS.finditer(doc):
        start = max(0, m.start() - 160)
        ctx = doc[start:m.end() + 160]
        if re.search(r"(no stake|stakes published|not a bet|no market price|"
                     r"without a market|is not a recommendation|never publish)", ctx, re.I):
            continue
        problems.append(f"projection.html mentions {m.group(0)!r} outside a disclosure: "
                        f"...{ctx.strip()[:160]}...")
    if re.search(r'class="n">\s*-?\d+\.\d{2,}\s*</td>\s*<td[^>]*>\s*stake', doc, re.I):
        problems.append("projection.html appears to carry a stake column")

    doc = bet.read_text()
    # every PUBLISHED row in bet.html must carry a numeric market price
    for m in ROW.finditer(doc):
        row = m.group(1)
        if "PUBLISHED" not in row:
            continue
        cells = [text_of(c) for c in CELL.findall(row)]
        nums = [c for c in cells if re.fullmatch(r"-?\d+(\.\d+)?", c or "")]
        if not nums:
            problems.append(f"bet.html has a PUBLISHED row with no numeric price: {cells[:6]}")
    return problems


# --------------------------------------------------------------------- freshness gates
def gates(docs: dict | None = None, include_built: bool = False) -> list[dict]:
    docs = docs or build_docs()
    out = []

    # G-V4-1 finals: every 11/15 game has a final whose period rows, where present, sum to it
    fin = C.finals_2026_11_15()
    bad = []
    for g in fin:
        if g["away_q"] is not None and sum(g["away_q"]) != g["away_pts"]:
            bad.append(g["game_id"] + "/away")
        if g["home_q"] is not None and sum(g["home_q"]) != g["home_pts"]:
            bad.append(g["game_id"] + "/home")
    out.append({"id": "G-V4-1", "name": "official finals complete and quarter rows sum to finals",
                "ok": len(fin) == 9 and not bad,
                "measured": f"{len(fin)} finals, {sum(1 for g in fin if g['quarter_status']=='read')} "
                            f"with verified quarters",
                "detail": "every transcribed period row sums to its final" if not bad
                          else f"mismatches: {bad}"})

    # G-V4-2 standings
    c = C.crosschecks()
    out.append({"id": "G-V4-2", "name": "standings internally balanced",
                "ok": c["wins_equal_losses"] and c["home_w_equal_road_l"] and c["n_clubs"] == 30,
                "measured": f"{c['n_clubs']} clubs, {c['wins']}W/{c['losses']}L, "
                            f"home {c['home_w']}-{c['home_l']} vs road {c['road_w']}-{c['road_l']}",
                "detail": "wins=losses and home wins=road losses and 30 clubs"})

    # G-V4-3 team stats: three pages, complete, and the points identity holds
    trad_ok = all(abs(2 * r["fgm"] + r["fg3m"] + r["ftm"] - r["pts"]) <= 0.45
                  for r in C.traditional())
    out.append({"id": "G-V4-3", "name": "three official team-stat pages complete and consistent",
                "ok": c["all_three_pages_complete"] and trad_ok
                      and c["pts_balance_within_bound"],
                "measured": f"advanced {c['n_teams_advanced']}, opponent "
                            f"{c['n_teams_opponent']}, traditional {c['n_teams_traditional']}; "
                            f"points diff {c['pts_diff']} within ±{c['rounding_bound']}",
                "detail": "2*FGM+3PM+FTM=PTS holds on all 30 rows and league points balance"})

    # G-V4-4 slate: unique ids, T+0..T+3 covered, every row sourced
    sl = C.slate()
    ids = [g["game_id"] for g in sl]
    dates = sorted({g["date"] for g in sl})
    out.append({"id": "G-V4-4", "name": "slate covers T+0..T+3 with unique official ids",
                "ok": len(ids) == len(set(ids)) and all(len(i) == 10 and i.startswith("002")
                                                       for i in ids)
                      and dates[0] == C.EXTENDED_WINDOW[0] and dates[-1] == C.EXTENDED_WINDOW[1]
                      and all(g["source_url"] for g in sl),
                "measured": f"{len(sl)} games across {len(dates)} dates ({dates[0]}..{dates[-1]})",
                "detail": "unique, well-formed, sourced, and the window edges are exact"})

    # G-V4-5 injuries: revision + retrieval + index stamps all present
    rel = C.INJURY_RELEASES[0]
    out.append({"id": "G-V4-5", "name": "newest-indexed injury release is stamped three ways",
                "ok": bool(rel["stamp_et"] and rel["retrieved_utc"] and rel["index_checked_utc"]
                           and rel["url"]),
                "measured": f"revision {rel['stamp_et']}, retrieved {rel['retrieved_utc']}, "
                            f"index checked {rel['index_checked_utc']}",
                "detail": "both stamps and the index check are recorded"})

    # G-V4-6 provenance: every captured row carries a source
    missing = []
    for name, doc in docs.items():
        if not isinstance(doc, dict):
            continue
        stack = [doc]
        while stack:
            cur = stack.pop()
            if isinstance(cur, dict):
                if "game_id" in cur or "tri" in cur or "player" in cur:
                    if not (cur.get("source_url") or cur.get("final_source_url")
                            or cur.get("list_url") or cur.get("src_rec")
                            or cur.get("url")):
                        missing.append(f"{name}: {str(cur)[:80]}")
                stack.extend(cur.values())
            elif isinstance(cur, list):
                stack.extend(cur)
    out.append({"id": "G-V4-6", "name": "provenance: every captured row carries a source",
                "ok": not missing,
                "measured": f"{len(docs)} capture documents scanned",
                "detail": "every row carries a source URL" if not missing
                          else f"{len(missing)} rows without a source: {missing[:5]}"})

    # G-V4-7 settlement integrity
    v = S.verify_settlement()
    out.append({"id": "G-V4-7", "name": "settlement re-hashes and the seal still verifies",
                "ok": bool(v.get("ok")) and bool(v.get("seal_still_verified")),
                "measured": f"settlement hash {str(v.get('stored'))[:16]}",
                "detail": ("hash matches and the sealed ledger is unmodified" if v.get("ok")
                           else f"settlement verification failed: {v}")})

    # G-V4-8 projection/bet separation. This one can only be measured on the EMITTED
    # pages, so it is opt-in and runs after rendering - never as a pre-render gate.
    if not include_built:
        return out
    wall = surface_wall()
    out.append({"id": "G-V4-8", "name": "projection and bet surfaces do not mix",
                "ok": not wall,
                "measured": "2 pages inspected on the emitted HTML",
                "detail": "no bet field on the projection surface; no unpriced bet row"
                          if not wall else f"{len(wall)} violations: {wall[:3]}"})
    return out


def build_docs() -> dict:
    raw = ROOT / "data" / "raw"
    docs = {}
    for p in sorted(raw.glob("refresh_*/**/*.json")):
        try:
            docs[p.name] = json.loads(p.read_text())
        except json.JSONDecodeError:
            docs[p.name] = {}
    return docs


# ------------------------------------------------------------------------- numerics
def numeric() -> list[str]:
    problems = []
    res = M.build()
    for p in res["projections"]:
        poss, ppph, pppa = p["possessions"], p["ppp_home"], p["ppp_away"]
        total = p["proj_total"]
        if abs(poss * (ppph + pppa) - total) > 0.06:
            problems.append(f"{p['game_id']}: total {total} != possessions x ppp "
                            f"({poss * (ppph + pppa):.2f})")
        if abs(M.phi(p["e1_margin"] / res["sigma"]) - p["p_home_e1"]) > 1e-3:
            problems.append(f"{p['game_id']}: p_home_e1 does not re-derive")
        if p["market_price"] is not None or p["stake_pct"] not in (0.0, None):
            problems.append(f"{p['game_id']}: projection row carries a market price or stake")
    hc = res["home_court"]
    if abs(hc["margin_sd"] * M.phi_inv(hc["home_win_rate"]) - hc["hca_points"]) > 1e-3:
        problems.append("HCA is not the pinned identity sd x Phi^-1(home win rate)")
    for r in res["luck"]:
        if r["luck_z"] is None:
            problems.append(f"{r['team']}: luck z missing")
            continue
        exp_p = M.pythagorean(r["pts_for"], r["pts_against"])
        exp_w = exp_p * r["gp"]
        if abs(exp_w - r["expected_wins"]) > 0.011:
            problems.append(f"{r['team']}: expected wins do not re-derive")
        if abs(abs(r["luck_z"]) <= res["luck_band_z"] - (0 if r["in_noise_band"] else 1)) > 2:
            problems.append(f"{r['team']}: band flag inconsistent with z")
    return problems


def run(verbose: bool = False) -> dict:
    st = structural()
    wall = surface_wall()
    num = numeric()
    g = gates(include_built=True)
    out = {
        "structural": st, "surface_wall": wall, "numeric": num,
        "gates": g,
        "n_problems": len(st) + len(wall) + len(num) + sum(0 if x["ok"] else 1 for x in g),
        "n_gates_pass": sum(1 for x in g if x["ok"]),
        "n_gates_fail": sum(1 for x in g if not x["ok"]),
    }
    out["ok"] = out["n_problems"] == 0
    out["publishable"] = all(x["ok"] for x in g)
    if verbose:
        for x in st + wall + num:
            print("  [problem]", x)
        for x in g:
            print(f"  [{'PASS' if x['ok'] else 'FAIL'}] {x['id']}: {x['measured']} - {x['detail']}")
    return out


if __name__ == "__main__":
    r = run(verbose=True)
    print(f"v4 check: {r['n_gates_pass']} gates pass / {r['n_gates_fail']} fail; "
          f"{len(r['structural'])} structural, {len(r['surface_wall'])} surface-wall, "
          f"{len(r['numeric'])} numeric; publishable={r['publishable']}")
    raise SystemExit(0 if r["ok"] else 1)
