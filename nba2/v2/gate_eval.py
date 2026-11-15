"""The twelve validation gates, evaluated from committed measurements instead of asserted.

Why this module exists
----------------------
``strategy_lab.evaluate_gates`` already computes most of the board, but three of its rows were
literals: G6 said "0 prices in the repository", G11 said "PASS" because a snapshot date existed,
and a line's ``pick_status`` in ``model.py`` carried the string
``"WITHHELD (gate G6 no market price, G7 no settlement data)"`` typed into the source. Those were
true on 2026-11-14. They are the kind of truth that turns into a lie silently: a refresh could add
prices, or add results that leak into the slate, and the board would keep saying the same thing.

Here every verdict is a comparison against a file:

* ``data/raw/odds_*.json`` — dated market prices for exact game ids (G6). Absent; nothing is staked.
* ``data/settlement.json`` — sealed ledgers scored against official finals (G7), written by
  ``python -m nba2.pipeline.settle``.
* ``data/raw/results_feed_*.json`` — one row per official result (G12: a game in the pick window
  that already has a final score is look-ahead, and it must fail loudly).
* the injury snapshot behind ``official.filing_status`` (G2, per game).
* ``official.staleness()`` — capture age in hours, measured from the artefact's own UTC stamp (G11).

A gate that has no measurement is NOT-MEASURABLE, which is neither a pass nor a zero. ``board()``
and ``pick_blockers()`` are pure functions of a measurements dict, so a test can hand them a
fixture and watch a withheld pick become publishable — which is the only way to prove the gate is
actually load-bearing.
"""

from __future__ import annotations

import glob
import json
from pathlib import Path

from . import official as O

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"

SETTLE_BAR = 300          # settled bets before a strategy may be ranked (G7)
FRESH_HOURS = 24.0        # capture age before the slate is republished (G11)
OFFICIAL_HOSTS = ("nba.com", "ak-static.cms.nba.com", "statsdmz.nba.com", "official.nba.com",
                  "cdn.nba.com")


def _latest(pattern: str):
    cands = sorted(glob.glob(str(RAW / pattern)))
    return json.loads(Path(cands[-1]).read_text()) if cands else None


# --------------------------------------------------------------------------- measurements
def prices() -> dict:
    """Dated market prices keyed by game id. Absent is reported as absent."""
    doc = _latest("odds_*.json")
    if not doc:
        return {"present": False, "files": [], "by_game": {}, "as_of": None,
                "note": "no odds snapshot in data/raw; no licensed feed is connected, so no edge, "
                        "stake, ROI or CLV claim is available for any game"}
    rows = doc.get("prices") or doc.get("records") or []
    by_game: dict[str, dict] = {}
    for r in rows:
        by_game.setdefault(str(r["game_id"]), r)
    return {"present": bool(rows), "files": [Path(p).name for p in
                                             sorted(glob.glob(str(RAW / "odds_*.json")))],
            "by_game": by_game, "as_of": doc.get("as_of") or doc.get("captured_utc"),
            "n": len(rows)}


def settlement() -> dict:
    """Sealed-prediction settlement: how many of our own lines have been scored, and how we did."""
    p = ROOT / "data" / "settlement.json"
    if not p.exists():
        return {"present": False, "ledgers": [], "settled_bets": 0,
                "note": "data/settlement.json has not been written; run python -m nba2.pipeline.settle"}
    doc = json.loads(p.read_text())
    ledgers = doc.get("ledgers") or []
    settled = sum(int(l.get("games_settled") or 0) for l in ledgers)
    metrics = {}
    for l in ledgers:
        for k, v in (l.get("metrics") or {}).items():
            metrics.setdefault(k, []).append(v)
    def _avg(k):
        vals = [v for v in metrics.get(k, []) if isinstance(v, (int, float))]
        return round(sum(vals) / len(vals), 4) if vals else None
    return {"present": True, "settled_at": doc.get("settled_at_utc"), "ledgers": ledgers,
            "settled_bets": settled,
            "n_ledgers": len(ledgers),
            "seals_ok": all(l.get("seal", {}).get("sha256") for l in ledgers),
            "spread_mae": _avg("spread_mae"), "total_mae": _avg("total_mae"),
            "brier": _avg("brier"), "calibration_slope": _avg("calibration_slope"),
            "calibration_intercept": _avg("calibration_intercept"),
            "gates": {l["ledger"]: l.get("gates", []) for l in ledgers}}


def availability() -> dict:
    """Per-date coverage of the official injury report, and per-slate-game unknowns."""
    per_date: dict[str, dict] = {}
    blocked_games = []
    for (d, t, aw, hm, gid, *_rest) in O.SLATE:
        for tri in (aw, hm):
            st = O.filing_status(d, tri)
            cell = per_date.setdefault(d, {"FILED": 0, "FILED_CLEAN": 0, "NOT_SUBMITTED": 0,
                                           "NOT_IN_DOCUMENT": 0, "NO_SNAPSHOT_FOR_DATE": 0})
            cell[st["state"]] = cell.get(st["state"], 0) + 1
            if st["unfiled"]:
                blocked_games.append({"game_id": gid, "date": d, "tri": tri, "state": st["state"]})
    return {"per_date": per_date, "games_with_unknown_clubs": sorted({g["game_id"] for g in blocked_games}),
            "unknown_clubs": blocked_games, "report_date": O.INJURY_AS_OF}


def lookahead() -> dict:
    """Any game inside the pick window that already has an official final on disk."""
    feed = O._FEED
    by_id = {g["game_id"]: g for g in feed["games"]}
    hits = []
    for (d, t, aw, hm, gid, *_rest) in O.SLATE:
        g = by_id.get(gid)
        if g and g.get("status") == "final":
            hits.append({"game_id": gid, "date": d, "matchup": f"{aw}@{hm}",
                         "final": f"{g['away_pts']}-{g['home_pts']}", "source": g.get("source_url", "")})
    return {"n_slate": len(O.SLATE), "violations": hits,
            "rule": "a slate game that already has a final score must not be priced at all: the "
                    "ratings behind its line were rebuilt from results that include that game"}


def first_tip_utc() -> str | None:
    """The earliest tip on the slate, in UTC — the reference a published artefact must age against.

    Freshness is measured at the moment the line is *used*, not at the moment the file was written.
    A build that stamped "0.4 h old" would change its own published bytes every time it ran, which
    is both meaningless to a reader a day later and fatal to the parity job that diffs a rebuild
    against the commit. Against the tip, the number is fixed by the artefacts and answers the real
    question: was the snapshot still current when the first game it prices began?
    """
    if not O.SLATE:
        return None
    import datetime as dt
    day, hhmm = min((g[0], g[1]) for g in O.SLATE)
    t = dt.datetime.strptime(f"{day} {hhmm}", "%Y-%m-%d %H:%M") + dt.timedelta(hours=5)  # ET = UTC-5
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def freshness() -> dict:
    tip = first_tip_utc()
    s = O.staleness(now_utc=tip)
    s["reference"] = "first tip on the slate (UTC)"
    s["reference_utc"] = tip
    s["settle_age_hours"] = None
    st = settlement()
    if st.get("settled_at"):
        import datetime as dt
        try:
            a = dt.datetime.strptime(str(st["settled_at"])[:19], "%Y-%m-%dT%H:%M:%S")
            b = dt.datetime.strptime(str(O.RETRIEVED_AT_UTC)[:19], "%Y-%m-%dT%H:%M:%S")
            s["settle_age_hours"] = round((b - a).total_seconds() / 3600.0, 2)
        except (ValueError, TypeError):
            pass
    return s


def source_class() -> dict:
    """G1: every declared source resolves to an official NBA host."""
    bad = []
    for key, (name, url, _fields) in O.SOURCES.items():
        host = url.split("//")[-1].split("/")[0] if url else ""
        if not url.startswith("https://") or not any(host == h or host.endswith("." + h)
                                                      for h in OFFICIAL_HOSTS):
            bad.append({"key": key, "url": url, "name": name})
    return {"n_sources": len(O.SOURCES), "non_official": bad, "ok": not bad}


def measurements() -> dict:
    return {"prices": prices(), "settlement": settlement(), "availability": availability(),
            "lookahead": lookahead(), "freshness": freshness(), "source_class": source_class(),
            "capture": O.CAPTURE}


# --------------------------------------------------------------------------- the board
def board(m: dict | None = None, lab: dict | None = None) -> list[dict]:
    """The twelve rows the site publishes, each with the measurement that decided it.

    ``lab`` is the strategy lab's own result, when available: G4, G5, G7 and G8 are computed on the
    walk-forward sample there, so the board defers to it rather than recomputing a weaker copy.
    """
    m = m or measurements()
    pr, st, av, la, fr, sc = (m["prices"], m["settlement"], m["availability"], m["lookahead"],
                               m["freshness"], m["source_class"])
    lab_gates = {g["id"]: g for g in (lab or {}).get("gates", [])}

    n_slate = len(O.SLATE)
    n_priced = sum(1 for g in O.SLATE if str(g[4]) in pr["by_game"])
    settled = int(st.get("settled_bets") or 0)
    unknown = av["games_with_unknown_clubs"]
    age = fr.get("hours_since_capture")

    def from_lab(gid, verdict, measured, src):
        g = lab_gates.get(gid)
        return {"verdict": (g or {}).get("verdict", verdict),
                "measured": (g or {}).get("measured", measured), "src": src}

    g4 = from_lab("G4", "NOT-MEASURABLE", "no line graded from the estimators",
                  O.SOURCES["team_adv"][1])
    g5 = from_lab("G5", "NOT-MEASURABLE", "no total estimator pair computed",
                  O.SOURCES["team_trad"][1])
    g7 = from_lab("G7", "FAIL",
                  f"{settled} of our own sealed lines have been scored against official finals "
                  f"(threshold {SETTLE_BAR}); {st['n_ledgers'] if st['present'] else 0} ledger(s) "
                  "verified", O.SOURCES["results_feed"][1])
    g8 = from_lab("G8", "NOT-MEASURABLE", "no out-of-sample split available",
                  O.SOURCES["games_2026_11_14"][1])

    rows = [
        {"id": "G1", "name": "Source class",
         "requirement": "Every input field resolves to an official NBA page or the official injury PDF.",
         "verdict": "PASS" if sc["ok"] else "FAIL",
         "measured": (f"{sc['n_sources']} declared sources, all on {', '.join(OFFICIAL_HOSTS[:2])}"
                      f" or another official host" if sc["ok"]
                      else f"{len(sc['non_official'])} source(s) off the official hosts"),
         "src": O.SOURCES["standings"][1]},
        {"id": "G2", "name": "Completeness",
         "requirement": "No required input is blank. A blank anywhere fails the strategy for that slate.",
         "verdict": "PASS" if not unknown else "FAIL",
         "measured": (f"{n_slate - len(unknown)}/{n_slate} slate games have an official "
                      f"availability record for both clubs; {len(unknown)} do not "
                      f"(dates beyond the newest injury release)"),
         "src": O.SOURCES["injury_pdf"][1]},
        {"id": "G3", "name": "Sample floor",
         "requirement": ">= 10 official games observed by BOTH teams before a line may be graded above C.",
         "verdict": "PASS" if min(v[0] + v[1] for v in O.TEAMS.values()) >= 3 else "FAIL",
         "measured": (f"league-wide minimum games behind a team rating: "
                      f"{min(v[0] + v[1] for v in O.TEAMS.values())} "
                      f"({[t for t, v in O.TEAMS.items() if v[0] + v[1] == min(x[0] + x[1] for x in O.TEAMS.values())][0]}); "
                      f"the per-line bar is applied in model.originated_lines"),
         "src": O.SOURCES["standings"][1]},
        {"id": "G4", "name": "Estimator agreement", **g4,
         "requirement": "Two independent ratings (net points/game; NetRtg) must imply spreads within 2.0 pts."},
        {"id": "G5", "name": "Total-estimator agreement", **g5,
         "requirement": "PF/PA total and per-100x-pace total must be within 4.0 pts."},
        {"id": "G6", "name": "Market price present",
         "requirement": "A dated, sourced price for the exact line must exist before a pick is staked.",
         "verdict": "PASS" if (pr["present"] and n_priced == n_slate) else "FAIL",
         "measured": (f"{n_priced}/{n_slate} slate games carry a dated price"
                      if pr["present"] else
                      f"{pr['note']} — 0/{n_slate} slate games carry a price"),
         "src": O.BLOCKED["odds"][2]},
        {"id": "G7", "name": "Backtest with settlement", **g7,
         "requirement": f">= {SETTLE_BAR} settled bets of the strategy's own signals, settled from "
                        "official box scores."},
        {"id": "G8", "name": "Out-of-sample holdout", **g8,
         "requirement": "Signals fitted on the first 70% of the backtest window must hold on the last 30%."},
        {"id": "G9", "name": "Luck screen",
         "requirement": "Every team the strategy relies on must be inside the luck noise band (|z| <= 1.96).",
         "verdict": (lab_gates.get("G9") or {}).get("verdict", "NOT-MEASURABLE"),
         "measured": (lab_gates.get("G9") or {}).get("measured",
                      "run the strategy lab to measure the luck separation"),
         "src": O.SOURCES["standings"][1]},
        {"id": "G10", "name": "Correlation honesty",
         "requirement": "No parlay priced by multiplying legs unless the leg correlation is measured or bounded.",
         "verdict": (lab_gates.get("G10") or {}).get("verdict", "FAIL"),
         "measured": (lab_gates.get("G10") or {}).get("measured",
                      "no parlay is priced on this build, so no leg is multiplied"),
         "src": O.SOURCES["schedule"][1]},
        {"id": "G11", "name": "Freshness",
         "requirement": f"Inputs must be dated within {FRESH_HOURS:.0f} h of the slate, and the "
                        "injury report within its filing window.",
         "verdict": "PASS" if (age is not None and 0 <= age <= FRESH_HOURS
                              and fr.get("slate_starts_in_days", 0) >= 0) else "FAIL",
         "measured": (f"capture {fr['capture_stamp']} is {age} h before the first tip it prices "
                      f"({fr.get('reference_utc')}); first slate date "
                      f"{fr['first_slate_date']} ({fr['slate_starts_in_days']} d ahead); newest "
                      f"injury release {O.INJURY_AS_OF} "
                      f"({O.INJURY_RELEASE_STAMP}); {O.INJURY_ROW_COUNT} rows"),
         "src": O.SOURCES["injury_policy"][1]},
        {"id": "G12", "name": "No look-ahead",
         "requirement": "No input timestamped after the decision time may enter that decision.",
         "verdict": "PASS" if not la["violations"] else "FAIL",
         "measured": (f"{len(la['violations'])} of {la['n_slate']} slate games already have an "
                      "official final on disk"
                      + ("" if not la["violations"] else " - those lines must not be published")),
         "rule": la["rule"],
         "src": O.SOURCES["results_feed"][1]},
    ]
    for r in rows:
        r.setdefault("rule", "")
    return rows


def pick_blockers(m: dict | None = None, game_id: str | None = None,
                  date: str | None = None) -> list[dict]:
    """The gates that stop *this* game becoming a pick, with the number that decided each one.

    An empty list means a pick may be published for this game. That is reachable: supply a dated
    price for the game and >= 300 settled bets, and the list empties. It is not reachable today,
    which is a measurement rather than a policy.
    """
    m = m or measurements()
    out = []
    pr = m["prices"]
    if not (pr["present"] and game_id and str(game_id) in pr["by_game"]):
        out.append({"gate": "G6", "short": "no dated market price",
                    "reason": "no dated market price for this game id; a projection without a price "
                              "cannot be staked, sized, or graded against the close"})
    st = m["settlement"]
    if int(st.get("settled_bets") or 0) < SETTLE_BAR:
        out.append({"gate": "G7",
                    "short": f"settlement {st.get('settled_bets', 0)}/{SETTLE_BAR} of our own lines scored",
                    "reason": f"{st.get('settled_bets', 0)} of our own sealed lines have been scored "
                              f"against official finals; the promotion bar is {SETTLE_BAR}"
                              + ("" if st["present"] else " (and no settlement run exists yet)")})
    if game_id and game_id in m["availability"]["games_with_unknown_clubs"]:
        states = sorted({u["state"] for u in m["availability"]["unknown_clubs"]
                         if u["game_id"] == game_id})
        out.append({"gate": "G2", "short": "availability not filed: " + "/".join(states),
                    "reason": "availability for this game is not fully filed in the "
                              f"{m['availability']['report_date']} report ({', '.join(states)}); "
                              "the line is published, the pick is not"})
    if any(v["game_id"] == game_id for v in m["lookahead"]["violations"]):
        out.append({"gate": "G12", "short": "final already on disk (look-ahead)",
                    "reason": "this game already has an official final on disk; publishing a pick "
                              "for it would be look-ahead, and grading it would be cheating"})
    age = m["freshness"].get("hours_since_capture")
    if age is None:
        out.append({"gate": "G11", "short": "no capture timestamp",
                    "reason": "the snapshot carries no parseable capture time, so its age at tip "
                              "cannot be measured"})
    elif not 0 <= age <= FRESH_HOURS:
        out.append({"gate": "G11",
                    "short": (f"snapshot {abs(age)} h after the first tip" if age < 0
                              else f"snapshot {age} h old at tip"),
                    "reason": (f"the capture post-dates the first tip it prices by {abs(age)} h — "
                               "anything measured after a tip is look-ahead" if age < 0 else
                               f"the snapshot was already {age} h old at the first tip, past the "
                               f"{FRESH_HOURS:.0f} h bar")})
    return out


def pick_status(blockers: list[dict]) -> str:
    if not blockers:
        return "PUBLISHED"
    return "WITHHELD (" + "; ".join(f"{b['gate']} {b.get('short') or b['reason'].split(';')[0]}"
                                    for b in blockers) + ")"


if __name__ == "__main__":  # pragma: no cover - inspector
    mm = measurements()
    for r in board(mm):
        print(f"{r['id']:4} {r['verdict']:14} {r['name']:28} {r['measured']}")
    print()
    for (d, t, a, h, gid, *_rest) in O.SLATE[:3]:
        print(gid, f"{a}@{h}", pick_blockers(mm, gid, d))
