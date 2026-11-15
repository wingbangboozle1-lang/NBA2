"""Arena coordinates and travel/schedule context — brief line 10.

    "Compute rest, back-to-back and 3-in-4 from the official schedule (already possible)
     and add travel distance from a sourced arena-coordinate table."

Two halves, and only one of them is fully sourced today
-------------------------------------------------------
**Schedule context (fully official).** Rest days, back-to-backs and 3-in-4s are computed
from the official schedule dates and the official results feed. Every number here is
derived from dates the league itself published, and nothing is estimated.

**Travel distance (sourced, third-party, city-level).** The arena and its city are printed
by the official schedule page for every game, so those are official. The *coordinates* are
not: no official endpoint reachable from this environment publishes arena geocodes, so the
table uses city centroids from a public dataset:

* US clubs — ``github.com/kelvins/US-Cities-Database`` (``csv/us_cities.csv``)
* Toronto  — ``github.com/dr5hn/countries-states-cities-database``
             (``json/countries+states+cities.json``)

Every row in ``data/arenas.csv`` carries both links, and the distance published from them
is a city-to-city great-circle distance whose error is the size of a metro area. That
limitation is stated on the site rather than buried, and the coordinate column is classed
``third_party`` so the provenance gate flags it.

Coverage, stated rather than hidden
-----------------------------------
Only the 22 clubs that HOST a game inside the pages this project read have an arena row;
the other eight (ATL, CHA, CHI, DET, GSW, HOU, NYK, POR) play every game in the capture
window on the road, so no official page read here prints their arena. A previous-game
location is known only when the club that hosted it is in the table; otherwise the travel
cell is blank with that reason. The fix is capture-side, and it is wired: the ingest job
stores the arena and city the official schedule prints for every game it ingests
(``nba2/pipeline/refresh.py``), so coverage grows with each night instead of requiring a
manual transcription.

Run:  python3 -m nba2.v2.arenas
"""

from __future__ import annotations

import csv
import json
import math
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARENAS_CSV = ROOT / "data" / "arenas.csv"

EARTH_KM = 6371.0088
MISSING_ARENA = ("no official page read in this session prints this club's arena — it does "
                 "not host inside the captured window")
MISSING_ORIGIN = ("the previous game's host arena is not in the coordinate table, so the "
                  "origin is unknown and no distance is printed")


def load_arenas() -> dict[str, dict]:
    out: dict[str, dict] = {}
    if not ARENAS_CSV.exists():
        return out
    with ARENAS_CSV.open(newline="") as fh:
        for r in csv.DictReader(fh):
            row = dict(r)
            row["lat"] = float(r["lat"]) if r["lat"] else None
            row["lon"] = float(r["lon"]) if r["lon"] else None
            out[r["team"]] = row
    return out


def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    (la1, lo1), (la2, lo2) = a, b
    p1, p2 = math.radians(la1), math.radians(la2)
    dp = p2 - p1
    dl = math.radians(lo2 - lo1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(2 * EARTH_KM * math.asin(math.sqrt(h)), 1)


def distance_km(arenas: dict, a: str, b: str) -> tuple[float | None, str]:
    """Great-circle km between two clubs' arenas. (None, reason) when it cannot be computed."""
    if a not in arenas:
        return None, MISSING_ARENA
    if b not in arenas:
        return None, MISSING_ARENA
    if arenas[a]["lat"] is None or arenas[b]["lat"] is None:
        return None, "a coordinate is missing from the sourced table"
    return haversine_km((arenas[a]["lat"], arenas[a]["lon"]),
                        (arenas[b]["lat"], arenas[b]["lon"])), ""


def _d(s: str) -> date:
    return date.fromisoformat(s)


def schedule_context() -> dict:
    """Rest, back-to-back, 3-in-4 and travel for every team-game in the published window."""
    from . import official as O
    from .results import load_rows

    arenas = load_arenas()
    played = load_rows()                       # official finals, ascending by date
    played_by_team: dict[str, list[dict]] = {}
    for g in played:
        played_by_team.setdefault(g["away"], []).append(g)
        played_by_team.setdefault(g["home"], []).append(g)
    for t in played_by_team:
        played_by_team[t].sort(key=lambda g: (g["date"], g["game_id"]))

    window = sorted(O.SLATE, key=lambda r: (r[0], r[1]))
    rows = []
    for (dstr, tstr, away, home, gid, arena, city, tv, cup) in window:
        d = _d(dstr)
        for team, opp, at_home in ((away, home, False), (home, away, True)):
            prior = [g for g in played_by_team.get(team, []) if _d(g["date"]) < d]
            last = prior[-1] if prior else None
            rest = (d - _d(last["date"])).days - 1 if last else None
            # "3-in-4" = this is at least the club's third game in four nights, i.e. it
            # already played twice inside the previous three nights. Counting four nights
            # back instead would flag a club whose two games were d-4 and d-3, which is a
            # day off before tonight, not a 3-in-4.
            n_3 = len([g for g in played_by_team.get(team, [])
                       if d - timedelta(days=3) <= _d(g["date"]) < d])
            n_4 = len([g for g in played_by_team.get(team, [])
                       if d - timedelta(days=4) <= _d(g["date"]) < d])
            # where the team played last: the host of that game
            origin_team = None
            if last:
                origin_team = last["home"]
            km, why = (None, "")
            origin_label = ""
            if origin_team is None:
                why = "no prior official game in the feed for this club"
            else:
                km, why = distance_km(arenas, origin_team, home)
                if km is not None:
                    origin_label = (f"{arenas[origin_team]['arena']}, "
                                    f"{arenas[origin_team]['city']}")
            rows.append({
                "date": dstr, "time_et": tstr, "game_id": gid, "team": team,
                "opponent": opp, "home": at_home,
                "previous_game_date": last["date"] if last else "",
                "previous_game": (f"{last['away']} @ {last['home']}" if last else ""),
                "rest_days": rest,
                "back_to_back": bool(last and (d - _d(last["date"])).days == 1),
                "third_in_four": bool(last and n_3 >= 2),
                "games_in_last_4_days": n_4,
                "games_in_previous_3_nights": n_3,
                "travel_km": km, "travel_mi": round(km / 1.609344, 1) if km else None,
                "travel_from": origin_label,
                "travel_to": f"{arena}, {city}" if arena else "",
                "travel_missing_reason": why if km is None else "",
                "src": (f"https://www.nba.com/game/{away.lower()}-vs-{home.lower()}-{gid}"),
                "src_sched": O.SOURCES["schedule"][1],
            })

    n_travel = sum(1 for r in rows if r["travel_km"] is not None)
    return {
        "schema": "nba2.schedule-context.v1",
        "window": [O.WINDOW_START, O.WINDOW_END],
        "n_rows": len(rows),
        "rows": rows,
        "arenas": arenas,
        "n_arenas": len(arenas),
        "teams_without_arena": sorted({"ATL", "CHA", "CHI", "DET", "GSW", "HOU", "NYK", "POR"}
                                      - set(arenas)),
        "n_travel_known": n_travel,
        "travel_coverage": round(n_travel / len(rows), 3) if rows else 0.0,
        "n_back_to_back": sum(1 for r in rows if r["back_to_back"]),
        "n_third_in_four": sum(1 for r in rows if r["third_in_four"]),
        "coordinate_class": "third_party",
        "coordinate_note": (
            "City centroids from a public dataset, not surveyed arena positions; the "
            "distance is a city-to-city great-circle and is accurate to roughly the size "
            "of a metro area. Arena and city strings are official (nba.com schedule)."),
        "improvement_path": (
            "the ingest job now records the arena and city the official schedule prints "
            "for every game it ingests, so the eight clubs with no row today gain one as "
            "soon as they host, and historical coverage grows night by night"),
    }


def main() -> int:
    c = schedule_context()
    print(f"window {c['window'][0]} .. {c['window'][1]}: {c['n_rows']} team-games")
    print(f"arenas in the sourced table: {c['n_arenas']} "
          f"(no row yet: {', '.join(c['teams_without_arena']) or 'none'})")
    print(f"back-to-backs: {c['n_back_to_back']}   3-in-4s: {c['n_third_in_four']}")
    print(f"travel distance computable: {c['n_travel_known']}/{c['n_rows']} "
          f"({c['travel_coverage']:.1%})")
    for r in c["rows"]:
        km = f"{r['travel_km']:.0f} km" if r["travel_km"] is not None else "—"
        print(f"  {r['date']} {r['team']:>3} {'vs' if r['home'] else '@'} {r['opponent']:<3} "
              f"rest {r['rest_days']}  b2b {int(r['back_to_back'])}  "
              f"3in4 {int(r['third_in_four'])}  travel {km}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
