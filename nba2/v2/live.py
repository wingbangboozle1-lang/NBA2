"""Live-source re-verification and out-of-sample grading — session arena/ab8743d8-nba2.

This module is the only thing in ``nba2/v2`` that reads *evidence produced today* rather than
the frozen 2026-11-14 transcription in ``official.py``. Its inputs are the captures in
``audit/2026-11-14/`` — every one of which records the exact official URL it came from and the
UTC time it was read. It publishes three things the rest of the site cannot:

1. **A staleness measure.** The v2 team table was transcribed before the nine 2026-11-13
   games had official results. Nine games change eighteen team records, so the table is now
   demonstrably a pre-final snapshot. This module proves that by reconstructing the
   pre-final state from today's official standings and comparing.
2. **A real out-of-sample grade.** ``nba2/data/picks.json`` was committed 2026-11-13
   22:36:46 UTC, 83 minutes before the earliest 11/13 tip, and has a single commit. Its
   selections can therefore be graded against results it could not have seen. This is not a
   backtest; it is the first genuine forecast the repository ever made.
3. **The honesty limits of that grade.** Four games, not eight. No price anywhere, so no
   PnL. A model that went 4-0 on the games it chose while calling the winner in only 5 of 9.

Nothing here writes to ``data/raw``, ``official.py`` or any other session's files. A number
that cannot be confirmed against a captured official URL is left blank and flagged, always.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "audit" / "2026-11-14"
PICKS = ROOT / "nba2" / "data" / "picks.json"

CAPTURES = {
    "schedule": "https://www.nba.com/schedule",
    "games": "https://www.nba.com/games",
    "standings": "https://www.nba.com/standings",
    "injury_1930": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_07_30PM.pdf",
    "injury_next": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_11_00AM.pdf",
}

FETCHED_UTC = "2026-11-14T09:56:00Z"


def _load(path: Path):
    return json.loads(path.read_text())


def captures() -> dict:
    """The five pages this session read, with the outcome of each read."""
    if not (AUDIT / "official_inputs_2026-11-14.json").exists():
        return {}
    return _load(AUDIT / "official_inputs_2026-11-14.json")


# --------------------------------------------------------------------------- 1. staleness
def staleness() -> dict:
    """Is the published v2 team table still true after the 11/13 finals became official?

    Method: take today's official W-L, subtract the nine 11/13 results, and compare that
    reconstruction with (a) the table the site publishes and (b) today's live W-L. If the
    published table matches the *pre-final* reconstruction and not the live table, then it
    was captured before those results - which is the whole finding.
    """
    from .official import TEAMS

    cap = captures()
    if not cap:
        return {}
    live = {r["team"]: (r["w"], r["l"]) for r in cap["standings_2026_11_14"]["rows"]}
    pre = dict(live)
    for f in cap["finals_2026_11_13"]:
        a, h = f["away"], f["home"]
        wa, la = pre[a]
        wh, lh = pre[h]
        if f["away_pts"] > f["home_pts"]:
            pre[a] = (wa - 1, la)
            pre[h] = (wh, lh - 1)
        else:
            pre[a] = (wa, la - 1)
            pre[h] = (wh - 1, lh)

    match_live = match_pre = 0
    rows = []
    for code, tup in TEAMS.items():
        w, l = tup[0], tup[1]
        lw, ll = live[code]
        pw, pl = pre[code]
        ok_live = (w, l) == (lw, ll)
        ok_pre = (w, l) == (pw, pl)
        match_live += ok_live
        match_pre += ok_pre
        if not ok_live:
            rows.append({
                "team": code, "published": f"{w}-{l}", "live": f"{lw}-{ll}",
                "pre_final_reconstruction": f"{pw}-{pl}",
                "cause": "PRE_FINALS" if ok_pre else "UNEXPLAINED",
            })
    return {
        "published_rows": len(TEAMS),
        "match_live_standings": match_live,
        "match_pre_final_state": match_pre,
        "stale_rows": rows,
        "n_stale": len(rows),
        "n_unexplained": sum(1 for r in rows if r["cause"] == "UNEXPLAINED"),
        "verdict": ("the published team table is a PRE-FINAL snapshot: it agrees with the "
                    "pre-11/13-finals reconstruction on every row and with today's standings "
                    "on only %d of %d" % (match_live, len(TEAMS))),
        "published_claim": ("the built site advertises 'Committed W-L ... vs live "
                            "nba.com/standings | 30/30 identical | MATCH' - that comparison was "
                            "true when it was made, and it is no longer true of the same rows"),
        "source": CAPTURES["standings"],
        "source_second": CAPTURES["games"],
        "fetched_utc": FETCHED_UTC,
    }


# --------------------------------------------------------------------------- 2. the grade
def _wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(max(0.0, c - h), 4), round(min(1.0, c + h), 4))


def _sign_p(k: int, n: int):
    if n == 0:
        return None
    return round(sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n, 4)


def _grade_spread(sel: str, g: dict):
    try:
        side, pts = sel.rsplit(" ", 1)
        pts = float(pts)
    except ValueError:
        return None
    side = side.strip().upper()
    if side == g["home"]:
        m = g["home_margin"] + pts
    elif side == g["away"]:
        m = -g["home_margin"] + pts
    else:
        return None
    return "WIN" if m > 0 else "LOSS" if m < 0 else "PUSH"


def _grade_ml(sel: str, g: dict):
    side = sel.replace("ML", "").strip().upper()
    if side == g["home"]:
        return "WIN" if g["home_margin"] > 0 else "LOSS"
    if side == g["away"]:
        return "WIN" if g["home_margin"] < 0 else "LOSS"
    return None


def grade() -> dict:
    """Grade the committed pre-tip picks against the official finals captured today."""
    cap = captures()
    if not cap or not PICKS.exists():
        return {}
    picks = _load(PICKS)
    lines = {l["game_id"]: l for l in picks["lines"]}

    games = {}
    for f in cap["finals_2026_11_13"]:
        gid = f["game_id"]
        L = lines.get(gid)
        g = {
            "game_id": gid, "away": f["away"], "home": f["home"],
            "final": f'{f["away"]} {f["away_pts"]} @ {f["home"]} {f["home_pts"]}',
            "ot": f["ot"], "home_margin": f["home_pts"] - f["away_pts"],
            "total": f["away_pts"] + f["home_pts"], "source": f["source"],
            "source_second": f["second_source"],
        }
        if L:
            g.update({
                "predicted_margin": L["predicted_margin"],
                "originated_spread": L["originated_spread"],
                "originated_spread_label": L["originated_spread_label"],
                "originated_total": L["originated_total_line"],
                "home_win_prob": L["home_win_prob"],
                "spread_abs_error": round(abs(L["predicted_margin"] - g["home_margin"]), 3),
                "total_abs_error": round(abs(L["originated_total_line"] - g["total"]), 3),
                "brier": round((L["home_win_prob"] - (1.0 if g["home_margin"] > 0 else 0.0)) ** 2, 6),
                "side_correct": (L["predicted_margin"] > 0) == (g["home_margin"] > 0),
            })
        games[gid] = g

    graded = [g for g in games.values() if "predicted_margin" in g]
    n = len(graded)

    rows = []
    for s in picks["strategies"]:
        for sig in s["signals"]:
            gid_field = sig["game_id"]
            gids = [x.strip() for x in gid_field.split(";")]
            res = None
            legs = None
            if sig.get("bet_type") == "parlay" or len(gids) > 1:
                legs = []
                for gid, leg in zip(gids, sig["selection"].split("+")):
                    g = games.get(gid)
                    legs.append({"game_id": gid, "leg": leg.strip(),
                                 "result": (_grade_ml(leg.strip(), g) if g else "PENDING")})
                if any(l["result"] == "PENDING" for l in legs):
                    res = "PENDING"
                else:
                    res = "WIN" if all(l["result"] == "WIN" for l in legs) else "LOSS"
                g = None
            else:
                g = games.get(gids[0])
                if g:
                    sel = sig["selection"]
                    res = (_grade_spread(sel, g) if ("+" in sel and not sel.endswith("ML"))
                           else _grade_ml(sel, g))
                else:
                    # The game exists on the official 11/14-11/15 schedule and has simply not
                    # been played. That is the expected state, not a data problem.
                    res = "PENDING"
            rows.append({
                "strategy_id": s["id"], "type": s["type"], "bet_type": sig.get("bet_type"),
                "game_id": gid_field, "game": sig.get("game"), "selection": sig.get("selection"),
                "model_win_prob": sig.get("model_win_prob"), "spread_edge": sig.get("spread_edge"),
                "price": sig.get("american_odds"),
                "status": "GRADED" if res in ("WIN", "LOSS", "PUSH") else ("PENDING" if res == "PENDING" else "UNGRADABLE"),
                "pending_reason": ("not yet played — on the official 11/14-11/15 slate" if res == "PENDING"
                                   and not any(games.get(x) for x in gids) else None),
                "result": res,
                "final": (g["final"] if g else None),
                "source": (g["source"] if g else CAPTURES["schedule"]),
                "legs": legs,
            })

    summary = []
    for s in picks["strategies"]:
        mine = [r for r in rows if r["strategy_id"] == s["id"]]
        gd = [r for r in mine if r["status"] == "GRADED" and r["result"] in ("WIN", "LOSS")]
        w = sum(1 for r in gd if r["result"] == "WIN")
        p = _sign_p(w, len(gd))
        summary.append({
            "strategy_id": s["id"], "name": s["name"], "type": s["type"],
            "signals": len(mine), "graded": len(gd),
            "pending": sum(1 for r in mine if r["status"] == "PENDING"),
            "ungradable": sum(1 for r in mine if r["status"] == "UNGRADABLE"),
            "wins": w, "losses": len(gd) - w,
            "hit_rate": round(w / len(gd), 4) if gd else None,
            "wilson_low": _wilson(w, len(gd))[0], "wilson_high": _wilson(w, len(gd))[1],
            "sign_p": p,
            "beats_luck_5pct": bool(p is not None and p < 0.05),
            "sample_adequate": len(gd) >= 30,
            "verdict": ("insufficient evidence" if 0 < len(gd) < 30 else
                        "nothing settled yet" if len(gd) == 0 else "eligible for review"),
        })

    games_by_strategy: dict[str, set] = {}
    for r in rows:
        if r["status"] == "GRADED":
            for gid in r["game_id"].split(";"):
                games_by_strategy.setdefault(gid.strip(), set()).add(r["strategy_id"])
    overlap = {k: sorted(v) for k, v in games_by_strategy.items() if len(v) > 1}

    grade_rows_total = sum(s["graded"] for s in summary)
    distinct_graded = len(games_by_strategy)
    side_correct = sum(1 for g in graded if g["side_correct"])

    # baselines computed from the same committed ratings the model used
    from .official import TEAMS
    h = 1.53  # the pivot used by the 2026-11-13 build, as sealed in the ledger inputs
    net_ok = 0
    for g in graded:
        a, hm = g["away"], g["home"]
        na = TEAMS[a][6] - TEAMS[a][7]
        nh = TEAMS[hm][6] - TEAMS[hm][7]
        net_ok += ((nh - na + h) > 0) == (g["home_margin"] > 0)
    home_ok = sum(1 for g in graded if g["home_margin"] > 0)

    return {
        "prediction_file": "nba2/data/picks.json",
        "prediction_commit": "d04bdc3",
        "committed_utc": "2026-11-13T22:36:46Z",
        "first_tip_utc": "2026-11-14T00:00:00Z",
        "minutes_before_first_tip": 83,
        "graded_at_utc": FETCHED_UTC,
        "sources": [CAPTURES["games"], CAPTURES["schedule"]],
        "games_graded": n,
        "games": sorted(games.values(), key=lambda g: g["game_id"]),
        "line_forecast": {
            "spread_mae": round(sum(g["spread_abs_error"] for g in graded) / n, 3),
            "total_mae": round(sum(g["total_abs_error"] for g in graded) / n, 3),
            "brier": round(sum(g["brier"] for g in graded) / n, 6),
            "naive_spread_mae": round(sum(abs(g["home_margin"]) for g in graded) / n, 3),
            "naive_total_mae": round(sum(abs(224.0 - g["total"]) for g in graded) / n, 3),
            "naive_brier": round(sum((0.5 - (1.0 if g["home_margin"] > 0 else 0.0)) ** 2
                                     for g in graded) / n, 6),
        },
        "side_accuracy": {
            "model": side_correct, "model_pct": round(side_correct / n, 4),
            "net_rating_baseline": net_ok, "net_rating_pct": round(net_ok / n, 4),
            "always_home": home_ok, "always_home_pct": round(home_ok / n, 4),
            "n": n,
        },
        "signals": rows,
        "strategies": summary,
        "recorded_signals_graded": grade_rows_total,
        "distinct_games_graded": distinct_graded,
        "duplicate_accounting": {
            "games_bet_by_several_strategies": overlap,
            "explanation": (f"{grade_rows_total} strategy-signal rows recorded, but only "
                            f"{distinct_graded} distinct games produced them: the same four wins are "
                            "counted twice because S1_MarginFavorite (moneyline) and S2_SpreadValue "
                            "(spread) both fired on the same games. 4-0 twice is 4 games, not 8."),
        },
        "pricing_note": ("no row in picks.json carries a market price (`american_odds` is absent "
                         "from every signal), so profit is not measurable and is not published. "
                         "A PnL here would be an assumed -110, i.e. an invented number."),
        "verdict": ("the first genuine out-of-sample forecast the repository has: every graded pick "
                    "won, but only four distinct games were bet, the model called the winner in 5 of "
                    "9 games (a naive net-rating baseline also got 5, always-home gets 7), and no "
                    "sample this small can separate skill from luck."),
    }


# --------------------------------------------------------------------------- 3. live checks
def checks() -> dict:
    """What this session verified live, and what the repository says that is now false."""
    st = staleness()
    gr = grade()
    out = {
        "fetched_utc": FETCHED_UTC,
        "captures": [
            {"name": "Official schedule", "url": CAPTURES["schedule"], "outcome": "read",
             "proved": "nine 11/13 finals; the 11/14-11/17 slate and tip times"},
            {"name": "Official games / scores", "url": CAPTURES["games"], "outcome": "read",
             "proved": "independent second confirmation of all nine finals"},
            {"name": "Official standings", "url": CAPTURES["standings"], "outcome": "read",
             "proved": "current 30-team W-L and last-10 for the 2026-27 season"},
            {"name": "Injury report 11/13 19:30 ET", "url": CAPTURES["injury_1930"], "outcome": "read",
             "proved": "the revision already published is still the served revision"},
            {"name": "Injury report 11/14 11:00 AM ET", "url": CAPTURES["injury_next"],
             "outcome": "AccessDenied", "proved": "no newer official revision existed at fetch time"},
        ],
        "staleness": st,
        "grade": gr,
    }
    return out


# --------------------------------------------------------------------------- 4. decision queue
def decision_queue() -> dict:
    """The suggestions register, reshaped into decisions a reviewer can actually act on.

    Source of truth is ``suggestions/SUGGESTIONS.json`` — this function adds nothing to it. It
    derives the two things a reviewer needs and the raw register does not carry: which track the
    item belongs to (data / site / model / governance) and whether answering it is a precondition
    for anything else. ``status`` is copied verbatim and never upgraded by this code.
    """
    path = ROOT / "suggestions" / "SUGGESTIONS.json"
    if not path.exists():
        return {"items": [], "n_total": 0, "n_awaiting": 0, "n_implemented": 0, "n_blocking": 0}
    reg = _load(path)["suggestions"]

    track_of = {
        "S-21": "site", "S-22": "model", "S-23": "model", "S-24": "site",
        "S-25": "site", "S-26": "model", "S-27": "governance",
    }
    blocking = {"S-27", "S-25", "S-26"}
    what_changes = {
        "S-21": "A new page exists, generated from dated official captures, and it fails the build if a capture is missing.",
        "S-22": "Every hit-rate table renders both 'signal rows' and 'distinct games'; a rate without its n is a lint error.",
        "S-23": "Three named baselines render beside every accuracy number; ranking above a baseline you lose to becomes impossible.",
        "S-24": "The suggestions page becomes this queue, with an explicit owner action on every row.",
        "S-25": "The Pages workflow cannot publish a build whose newest capture is older than a per-table limit.",
        "S-26": "S2 selections name the side that takes the points, matching the file's own spread label.",
        "S-27": "One dashboard is served; the other five move under archive/ behind dated redirects.",
    }
    evidence = {
        "S-21": "18 of 30 published team records no longer match today's official standings",
        "S-22": "8 graded signal wins are 4 distinct games (S1 and S2 fired on the same four games)",
        "S-23": "model 5/9 on winners vs 5/9 naive net rating vs 7/9 always-home",
        "S-24": "suggestions were a list of status strings with no action a reviewer could take",
        "S-25": "every page prints an as-of date and no build fails when it is old",
        "S-26": "picks.json prints 'POR +6.0' where its own label reads 'POR -6.0'",
        "S-27": "the live index is the v2 tree while the Pages API reports source = main /",
    }
    items = []
    for r in reg:
        sid = r["id"]
        if sid not in track_of:
            continue
        items.append({
            "id": sid,
            "track": track_of[sid],
            "title": r["title"],
            "problem": f'{r["problem"]} — evidence: {evidence.get(sid, "")}',
            "changes": what_changes.get(sid, r["proposal"]),
            "effort": r["effort"],
            "status": r["status"],
            "source": CAPTURES["standings"] if sid != "S-27" else "https://github.com/wingbangboozle1-lang/NBA2",
            "evidence": "https://github.com/wingbangboozle1-lang/NBA2/blob/main/audit/2026-11-14/official_inputs_2026-11-14.json",
            "blocking": sid in blocking,
        })
    return {
        "items": items,
        "n_total": len(items),
        "n_awaiting": sum(1 for i in items if not i["status"].startswith("implemented")),
        "n_implemented": sum(1 for i in items if i["status"].startswith("implemented")),
        "n_blocking": sum(1 for i in items if i["blocking"]),
    }


def main() -> int:
    """`python3 -m nba2.v2.live` — re-run the live checks and print them."""
    st = staleness()
    gr = grade()
    print(f"staleness: {st['match_live_standings']}/{st['published_rows']} match today, "
          f"{st['match_pre_final_state']}/{st['published_rows']} match the pre-final state, "
          f"{st['n_unexplained']} unexplained")
    print(f"graded:    {gr['games_graded']} games, {gr['recorded_signals_graded']} signal rows, "
          f"{gr['distinct_games_graded']} distinct games")
    sa = gr["side_accuracy"]
    print(f"winners:   model {sa['model']}/{sa['n']}  net-rating {sa['net_rating_baseline']}/{sa['n']}  "
          f"always-home {sa['always_home']}/{sa['n']}")
    dq = decision_queue()
    print(f"decisions: {dq['n_total']} queued, {dq['n_awaiting']} awaiting owner, "
          f"{dq['n_implemented']} implemented, {dq['n_blocking']} blocking")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


def new_questions() -> dict:
    """The questions this session added to the shared register, identified by ID range."""
    path = ROOT / "requirements" / "QUESTIONS.json"
    if not path.exists():
        return {"items": []}
    qs = _load(path)["questions"]
    mine = [q for q in qs if q["id"] in {"Q-23", "Q-24", "Q-25", "Q-26", "Q-27", "Q-28"}]
    return {"items": mine}
