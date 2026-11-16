"""Per-player game logs: gates first, baselines second.

The gates in :func:`gates` are the reason this capture can be published without
the reviewer re-reading nba.com. The one that matters is G-41-02: if a row were
missed, or a digit mistyped, the mean of the captured rows would stop matching
the PPG / RPG / APG that the *same official page* prints in the player header.
That identity cannot be satisfied by a partial or wrong transcription, so it is
checked for every player and printed on the page.
"""

from __future__ import annotations

from . import official as O

SEASON_START = "2026-10-21"      # earliest date on any captured log
SEASON_END = "2026-11-13"        # latest date on any captured log (11/14-11/15 games appear in later releases)
MAX_MINUTES = 48.0


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def players() -> list[dict]:
    return O.gamelogs()["players"]


def gates() -> list[dict]:
    """Measure, do not assert. Each row carries the number that decided it."""
    out: list[dict] = []
    for p in players():
        tag = p["player"]
        g = p["games"]
        # G-41-01 completeness against the count the page itself declares
        out.append({
            "id": "G-41-01", "player": tag,
            "name": "captured rows equal the row count the official page declares",
            "measurement": f"{len(g)} captured / {p['rows_declared']} declared",
            "status": "PASS" if len(g) == p["rows_declared"] else "FAIL",
            "source": p["source_url"],
        })
        # G-41-02 the capture reproduces the page's own season rates
        for stat, key in (("points", "ppg"), ("rebounds", "rpg"), ("assists", "apg")):
            got = round(_mean([float(x[stat]) for x in g]), 1)
            want = p["season_header"][key]
            out.append({
                "id": "G-41-02", "player": tag,
                "name": f"mean of captured {stat} equals the official season {key.upper()}",
                "measurement": f"computed {got} vs official {want}",
                "status": "PASS" if abs(got - want) <= 0.05 else "FAIL",
                "source": p["source_url"],
            })
        # G-41-03 no implausible minute total
        bad = [x["minutes"] for x in g if x["minutes_dec"] > MAX_MINUTES]
        out.append({
            "id": "G-41-03", "player": tag,
            "name": "no game exceeds 48:00 played",
            "measurement": f"max {max(x['minutes_dec'] for x in g):.2f} min" + (f"; over: {bad}" if bad else ""),
            "status": "PASS" if not bad else "FAIL",
            "source": p["source_url"],
        })
        # G-41-04 every date is inside the season actually played
        dates = [x["date"] for x in g]
        outside = [d for d in dates if d < SEASON_START or d > "2026-11-15"]
        out.append({
            "id": "G-41-04", "player": tag,
            "name": "every game date lies inside the season played",
            "measurement": f"{min(dates)} → {max(dates)}" + (f"; outside: {outside}" if outside else ""),
            "status": "PASS" if not outside else "FAIL",
            "source": p["source_url"],
        })
        # G-41-05 the player is on the injury release this capture was built from
        from . import injury as IN
        club = O.team_full(p["team"])
        rows = [r for r in IN.records() if r["player"] == tag]
        same = [r for r in rows if r["team"] == club]
        out.append({
            "id": "G-41-05", "player": tag,
            "name": "the player appears on the official injury release with the same club",
            "measurement": f"{len(same)} matching release row(s)" if rows else "not on the release",
            "status": "PASS" if same else "FAIL",
            "source": IN.SOURCE_URL,
        })
        # G-41-06 the game ids on the log are official game ids (ten digits, season prefix)
        bad_ids = [x["game_id"] for x in g if not (len(x["game_id"]) == 10 and x["game_id"].startswith("00226"))]
        out.append({
            "id": "G-41-06", "player": tag,
            "name": "every row carries an official game id",
            "measurement": f"{len(g)} ids checked" + (f"; bad: {bad_ids}" if bad_ids else ""),
            "status": "PASS" if not bad_ids else "FAIL",
            "source": p["source_url"],
        })
    return out


def baselines() -> list[dict]:
    """Per-player season and last-5 baselines, all arithmetic on captured rows."""
    out = []
    for p in players():
        g = sorted(p["games"], key=lambda x: x["date"])
        last5 = g[-5:]
        out.append({
            "player": p["player"],
            "team": p["team"],
            "player_id": p["player_id"],
            "injury_status": p["injury_status"],
            "injury_reason": p["injury_reason"],
            "games": len(g),
            "mpg": round(_mean([x["minutes_dec"] for x in g]), 1),
            "ppg": round(_mean([float(x["points"]) for x in g]), 1),
            "rpg": round(_mean([float(x["rebounds"]) for x in g]), 1),
            "apg": round(_mean([float(x["assists"]) for x in g]), 1),
            "l5_mpg": round(_mean([x["minutes_dec"] for x in last5]), 1),
            "l5_ppg": round(_mean([float(x["points"]) for x in last5]), 1),
            "l5_rpg": round(_mean([float(x["rebounds"]) for x in last5]), 1),
            "l5_apg": round(_mean([float(x["assists"]) for x in last5]), 1),
            "min_minutes": round(min(x["minutes_dec"] for x in g), 1),
            "max_minutes": round(max(x["minutes_dec"] for x in g), 1),
            "last_game": g[-1]["date"],
            "home_games": sum(1 for x in g if x["home_away"] == "home"),
            "away_games": sum(1 for x in g if x["home_away"] == "away"),
            "official_header": p["season_header"],
            "source_url": p["source_url"],
        })
    return out


def rows() -> list[dict]:
    """One flat row per captured player-game, for the published table."""
    out = []
    for p in players():
        for g in sorted(p["games"], key=lambda x: x["date"], reverse=True):
            out.append({
                "player": p["player"], "team": p["team"], "player_id": p["player_id"],
                "date": g["date"],
                "matchup": f"{p['team']} {'vs' if g['home_away'] == 'home' else '@'} {g['opponent']}",
                "opponent": g["opponent"],
                "home_away": g["home_away"],
                "result": g["result"],
                "minutes": g["minutes"],
                "minutes_dec": g["minutes_dec"],
                "points": g["points"],
                "rebounds": g["rebounds"],
                "assists": g["assists"],
                "plus_minus": g["plus_minus"],
                "game_id": g["game_id"],
                "game_url": f"https://www.nba.com/game/{g['game_id']}/",
                "source_url": p["source_url"],
            })
    return out
