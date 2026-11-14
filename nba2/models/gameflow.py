"""Game-flow / schedule-spot analysis.

Two kinds of output, kept strictly apart:

1. WHAT WE CAN SEE NOW (from the official schedule): rest between games inside the observed
   window, back-to-backs, 3-in-4, home stands, road-trip length, and duplicate-matchup
   anomalies. These are facts about the slate.
2. WHAT WE CANNOT SEE NOW: in-game flow (lead changes, garbage time, foul trouble, pace
   by half, closing lineups). All of that needs play-by-play and lineup data. Those fields
   are returned as `None` so the site renders them blank + flagged instead of narrating.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta


def _d(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


@dataclass
class Spot:
    tricode: str
    games_in_window: int
    dates: list[str]
    b2b_nights: list[str]
    three_in_four: list[str]
    home_games: int
    away_games: int
    longest_home_stand: int
    longest_road_trip: int
    window_start: str
    window_end: str
    caveats: list[str]

    def as_dict(self) -> dict:
        return self.__dict__.copy()


def schedule_spots(games: list[dict], window_start: str, window_end: str) -> dict[str, Spot]:
    """Build per-team schedule load from the slate we hold.

    IMPORTANT: `window` is 2026-11-13..2026-11-17 in the current snapshot (11/13 exists as
    day-before context so back-to-backs into 11/14 are detected). A back-to-back whose first
    game is outside the window is
    invisible here, so `caveats` says exactly that and every spot row is marked partial.
    """
    per: dict[str, list[dict]] = {}
    for g in games:
        per.setdefault(g["home"], []).append(g)
        per.setdefault(g["away"], []).append(g)

    out: dict[str, Spot] = {}
    for tri, gs in per.items():
        gs = sorted(gs, key=lambda g: g["date"])
        dates = [g["date"] for g in gs]
        uniq = sorted(set(dates), key=_d)
        b2b = [f"{a}+{b}" for a, b in zip(uniq, uniq[1:]) if _d(b) - _d(a) == timedelta(days=1)]
        three4 = []
        for i in range(len(uniq) - 2):
            if _d(uniq[i + 2]) - _d(uniq[i]) <= timedelta(days=3):
                three4.append("->".join(uniq[i:i + 3]))
        home = sum(1 for g in gs if g["home"] == tri)
        away = sum(1 for g in gs if g["away"] == tri)

        def longest(predicate) -> int:
            best = cur = 0
            for d in uniq:
                day_games = [g for g in gs if g["date"] == d]
                if any(predicate(g) for g in day_games):
                    cur += 1
                    best = max(best, cur)
                else:
                    cur = 0
            return best

        out[tri] = Spot(
            tricode=tri, games_in_window=len(gs), dates=uniq,
            b2b_nights=b2b, three_in_four=three4, home_games=home, away_games=away,
            longest_home_stand=longest(lambda g: g["home"] == tri),
            longest_road_trip=longest(lambda g: g["away"] == tri),
            window_start=window_start, window_end=window_end,
            caveats=[
                f"Window is {window_start}..{window_end} only; games before {window_start} are not in "
                "this snapshot, so a first leg of a back-to-back may be missing.",
                "Rest-before-tip is computed in calendar days from the slate, not from arrival/travel time.",
            ],
        )
    return out


def game_flow_inputs(games: list[dict], spots: dict[str, Spot]) -> list[dict]:
    """Per-game game-flow context. Every field we cannot verify is None on purpose.

    B2B / 3-in-4 are flagged on the night the load COMPLETES: a back-to-back is the team's
    SECOND consecutive day (the second element of a `d1+d2` pair), a 3-in-4 is the team's
    THIRD game inside four days (the last element of a `d1->d2->d3` sequence). Earlier
    revisions of this function substring-matched the game date against the whole pair/sequence
    string, which also flagged the first night of a pair — inflating B2B counts for e.g. a
    team whose two in-window games simply sat on consecutive dates (fixed 2026-11-14, see
    irregularity I-07 in COORDINATION.md and the regression test).
    """
    rows = []
    for g in games:
        hs = spots.get(g["home"])
        as_ = spots.get(g["away"])
        home_b2b_dates = {p.split("+")[1] for p in (hs.b2b_nights if hs else [])}
        away_b2b_dates = {p.split("+")[1] for p in (as_.b2b_nights if as_ else [])}
        home_34_dates = {s.split("->")[-1] for s in (hs.three_in_four if hs else [])}
        away_34_dates = {s.split("->")[-1] for s in (as_.three_in_four if as_ else [])}
        rows.append({
            "game_id": g["game_id"],
            "date": g["date"],
            "matchup": f"{g['away']} @ {g['home']}",
            "home_rest_days": None,          # needs the previous game date outside our window
            "away_rest_days": None,
            "home_b2b": g["date"] in home_b2b_dates,
            "away_b2b": g["date"] in away_b2b_dates,
            "home_3_in_4": g["date"] in home_34_dates,
            "away_3_in_4": g["date"] in away_34_dates,
            "pace_projection": None,         # needs possession/pace data
            "garbage_time_risk": None,        # needs projected margin + rotation depth
            "foul_trouble_risk": None,        # needs referee assignments + player foul rates
            "closing_lineup_note": None,      # needs coaching-pattern data
            "half_court_share": None,         # needs play-type data
        })
    return rows


def duplicate_matchups(games: list[dict]) -> list[dict]:
    """Same pairing, same arena, on consecutive days is a data-integrity red flag: it is
    either a genuine series-style scheduling oddity or a scrape artifact. Flag, never fix."""
    seen: dict[tuple[str, str], list[dict]] = {}
    for g in games:
        seen.setdefault((g["away"], g["home"]), []).append(g)
    out = []
    for (a, h), gs in seen.items():
        if len(gs) > 1:
            ds = sorted({g["date"] for g in gs})
            gap = min([(_d(b) - _d(x)).days for x, b in zip(ds, ds[1:])]) if len(ds) > 1 else 99
            out.append({
                "away": a, "home": h, "dates": ds, "gap_days": gap,
                "game_ids": [g["game_id"] for g in gs],
                "verdict": "FLAGGED - needs manual confirmation against NBA.com schedule pages",
            })
    return out
