"""v7 slate: originate a line for every game in the next three days, with its provenance.

For each game the row carries:
    date, tip (official), clubs, game id, official game-page link
    E1 margin, E2 margin, their **disagreement** (the headline), the blend (underneath)
    P(home win) under each estimator, our spread and total (possessions x PPP)
    rest days / back-to-back / 3-in-4 for both clubs, computed from the official finals
    the availability column, which is BLANK and flagged when no report was read
    the strategy verdict: what a bet on this game would need, and why nothing is staked

Availability is the one column this build genuinely cannot fill: the 2026-11-19 official
injury report was not read this session (`official.INJURY_REPORT_READ = False`), so every
availability cell is blank with a flag id rather than a guess. The brief asks for the column
to exist on the picks page; it exists, empty and labelled, which is the honest version.
"""

from __future__ import annotations

import datetime as dt

from . import model as M
from . import official as O


def _dates_between(a: str, b: str) -> list[str]:
    d0 = dt.date.fromisoformat(a)
    d1 = dt.date.fromisoformat(b)
    out, d = [], d0
    while d <= d1:
        out.append(d.isoformat())
        d += dt.timedelta(days=1)
    return out


def rest_and_load(games: list[dict], team: str, date: str) -> dict:
    """Rest days, back-to-back and 3-in-4 for one club before a date, from official finals."""
    prior = sorted({g["date"] for g in games
                    if g["date"] < date and team in (g["away"], g["home"])})
    if not prior:
        return {"last_game_date": None, "rest_days": None, "back_to_back": None,
                "three_in_four": None, "games_last_4_days": None,
                "flag": "no prior official final for this club in the committed window"}
    last = prior[-1]
    rest = (dt.date.fromisoformat(date) - dt.date.fromisoformat(last)).days - 1
    window = [d for d in prior
              if 0 <= (dt.date.fromisoformat(date) - dt.date.fromisoformat(d)).days <= 3]
    return {"last_game_date": last, "rest_days": rest, "back_to_back": rest == 0,
            "three_in_four": len(window) + 1 >= 3, "games_last_4_days": len(window),
            "window_dates": window, "flag": None}


def build(res: dict) -> dict:
    teams = res["teams"]
    games_hist = res["games"]
    cut = res["cut"]
    luck = res["luck"]
    rows = []
    for g in O.SLATE:
        a, h = g["away"], g["home"]
        m1, m2 = cut.margins(a, h)
        p1, p2 = cut.p_home(a, h)
        tot = cut.total(a, h, teams)
        dis = abs(m1 - m2) if (m1 is not None and m2 is not None) else None
        cons = (m1 + m2) / 2 if (m1 is not None and m2 is not None) else None
        ra, rh = rest_and_load(games_hist, a, g["date"]), rest_and_load(games_hist, h, g["date"])
        out_band = [t for t in (a, h) if luck.get(t, {}).get("outside")]
        # which side the consensus favours, and by how much
        lean = None
        if cons is not None:
            lean = h if cons > 0 else a
        rows.append({
            "date": g["date"], "tip_et": g["tip"], "game_id": g["game_id"],
            "away": a, "home": h, "cup_group": O.CUP_GROUP.get(g["game_id"]),
            "e1_margin_home": m1, "e2_margin_home": m2,
            "disagreement_pts": dis, "consensus_margin_home": cons,
            "blend_note": "the blend is published under the disagreement, never instead of it",
            "spread_home": -cons if cons is not None else None,
            "p_home_e1": p1, "p_home_e2": p2,
            "p_home": (p1 + p2) / 2 if (p1 is not None and p2 is not None) else None,
            "lean": lean,
            "total": tot.get("total"), "possessions": tot.get("possessions"),
            "ppp_home": tot.get("ppp_home"), "ppp_away": tot.get("ppp_away"),
            "total_note": tot.get("identity") or tot.get("flag"),
            "rest": {"away": ra, "home": rh,
                     "rest_edge_days": (ra["rest_days"] - rh["rest_days"])
                     if (ra["rest_days"] is not None and rh["rest_days"] is not None) else None},
            "availability": {
                "status": "BLANK" if not O.INJURY_REPORT_READ else "filed",
                "out": None, "questionable": None, "probable": None,
                "flag": ("no official injury report for this date was read in this "
                         "session — the column is published empty on purpose")
                if not O.INJURY_REPORT_READ else None,
                "flag_id": "F-V7-AVAIL" if not O.INJURY_REPORT_READ else None,
            },
            "luck_gate": {"away_z": luck.get(a, {}).get("z"),
                          "home_z": luck.get(h, {}).get("z"),
                          "outside_band": out_band,
                          "blocks": bool(out_band)},
            "stake": 0.0,
            "source_url": f"https://www.nba.com/game/{a.lower()}-vs-{h.lower()}-{g['game_id']}",
            "list_url": f"https://www.nba.com/games?date={g['date']}",
        })
    dates = sorted({r["date"] for r in rows})
    return {"schema": "nba2.v7.slate.v1", "session": "arena/6023d517-nba2",
            "as_of_utc": O.RETRIEVED_AT_UTC,
            "window": {"start": dates[0], "end": dates[-1], "n_dates": len(dates),
                       "n_games": len(rows), "max_days_ahead": 3,
                       "rule": ("3 days ahead of the snapshot date, which is the brief's "
                                "maximum; the window is printed rather than implied")},
            "dates": dates,
            "rows": rows,
            "by_date": {d: [r for r in rows if r["date"] == d] for d in dates}}
