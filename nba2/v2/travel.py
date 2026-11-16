"""Rest, back-to-backs, 3-in-4 and travel distance from sourced arena coordinates.

The brief pins these inputs: rest days, B2B, 3-in-4 and travel distance computed from
sourced arena coordinates. Coordinates come from ``data/raw/capture_2026-11-15/arenas_2026-11-15.json``
(nba2.arena-coords.v1) — arena names official (NBA.com schedule), the geocodes themselves
third-party (Wikimedia REST / Wikidata P625) and labelled as such everywhere.

Distances are great-circle (haversine) miles between arena centroids — a *derived*
quantity, published so it can be re-checked. The identity haversine(39.7486,-105.0075 →
39.7486,-105.0075) = 0 and known city pairs (e.g. Crypto.com Arena ↔ Intuit Dome ≈ 12.5 mi)
are regression-tested in test_v2.py.
"""

from __future__ import annotations

import math
from datetime import date, timedelta

from . import capture2 as C2

EARTH_MI = 3958.7613


def haversine_mi(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_MI * math.asin(math.sqrt(a))


def arena_coords() -> dict[str, tuple[float, float]]:
    return {r["team"]: (r["lat"], r["lon"]) for r in C2.arena_rows()}


def leg_miles(from_team: str, to_team: str) -> float | None:
    """Great-circle miles between two teams' arenas; None when a coordinate is missing
    (never estimated)."""
    coords = arena_coords()
    if from_team not in coords or to_team not in coords:
        return None
    (la1, lo1), (la2, lo2) = coords[from_team], coords[to_team]
    return round(haversine_mi(la1, lo1, la2, lo2), 1)


def team_game_dates(teams: tuple[str, ...] | None = None) -> dict[str, list[str]]:
    """Every played/scheduled date per team, from the 188 verified finals plus the slate."""
    import glob
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    dates: dict[str, list[str]] = {}
    seen = set()

    def add(tri: str, d: str):
        if teams and tri not in teams:
            return
        dates.setdefault(tri, []).append(d)

    for f in sorted(glob.glob(str(root / "data" / "raw" / "history" / "games_*.json"))):
        with open(f) as fh:
            games = json.load(fh)["games"]
        for g in games:
            if g["game_id"] in seen:
                continue
            seen.add(g["game_id"])
            add(g["away"], g["date"])
            add(g["home"], g["date"])
    for g in C2.results_rows():
        if g["game_id"] in seen:
            continue
        seen.add(g["game_id"])
        add(g["away"], g["date"])
        add(g["home"], g["date"])
    for g in C2.slate_rows():
        if g["game_id"] in seen:
            continue
        seen.add(g["game_id"])
        add(g["away"], g["date"])
        add(g["home"], g["date"])
    for t in dates:
        dates[t] = sorted(set(dates[t]))
    return dates


def rest_context(game_date: str, team: str, dates: dict[str, list[str]] | None = None) -> dict:
    """Rest context for one team entering one game.

    ``days_rest`` = calendar days since the previous game (0 = back-to-back).
    ``b2b`` = played the day before. ``three_in_four`` = this game plus ≥2 more inside the
    4-day window ending today. ``prev_date`` / ``prev_arena_team`` feed the travel leg;
    ``travel_miles`` is haversine from the previous game's arena city to this one, or None
    when the previous game's venue is unknown (flagged, not estimated)."""
    dates = dates or team_game_dates()
    dl = [d for d in dates.get(team, []) if d <= game_date]
    prev = [d for d in dl if d < game_date]
    prev_date = prev[-1] if prev else None
    days_rest = (date.fromisoformat(game_date) - date.fromisoformat(prev_date)).days - 1 if prev_date else None
    window_start = (date.fromisoformat(game_date) - timedelta(days=3)).isoformat()
    in_window = [d for d in dates.get(team, []) if window_start < d <= game_date]
    three_in_four = len(in_window) >= 3
    return {
        "team": team, "date": game_date,
        "prev_date": prev_date,
        "days_rest": days_rest,
        "b2b": (days_rest == 0) if days_rest is not None else None,
        "three_in_four": three_in_four,
        "games_in_4": len(in_window),
    }


def travel_legs_for_game(game_date: str, away: str, home: str,
                         dates: dict[str, list[str]] | None = None) -> dict:
    """Travel leg + rest for both sides of one game. The travel leg is each team's
    distance from the arena of its *previous* game to the arena of this game. A team
    whose previous game is unknown returns travel_miles None + ``travel_flagged``."""
    dates = dates or team_game_dates()
    out = {}
    for tri, this_game_arena in ((away, home), (home, home)):
        ctx = rest_context(game_date, tri, dates)
        # find where the team played its previous game (home or away → that arena)
        prev_miles = None
        flagged = False
        if ctx["prev_date"]:
            prev_arena_team = _venue_team_on(dates, tri, ctx["prev_date"])
            if prev_arena_team:
                prev_miles = leg_miles(prev_arena_team, this_game_arena)
            else:
                flagged = True
        else:
            flagged = True
        ctx["travel_miles"] = prev_miles
        ctx["travel_flagged"] = flagged
        out[tri] = ctx
    return out


def _venue_team_on(dates: dict[str, list[str]], team: str, on_date: str) -> str | None:
    """The *host* tricode of the game ``team`` played on ``on_date`` (its arena)."""
    import glob
    import json

    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    for f in sorted(glob.glob(str(root / "data" / "raw" / "history" / "games_*.json"))):
        with open(f) as fh:
            games = json.load(fh)["games"]
        for g in games:
            if g["date"] == on_date and team in (g["away"], g["home"]):
                return g["home"]
    for g in C2.results_rows():
        if g["date"] == on_date and team in (g["away"], g["home"]):
            return g["home"]
    for g in C2.slate_rows():
        if g["date"] == on_date and team in (g["away"], g["home"]):
            return g["home"]
    return None
