"""Write the 2026-11-17 official capture, then verify it arithmetically.

Method, recorded because it is the whole point: bash egress from this sandbox to nba.com /
stats.nba.com / cdn.nba.com returns HTTP 000 (verified: `curl -s -o /dev/null -w %{http_code}`
gives 000 for all three), and `stats.nba.com` additionally closes the TLS connection
(`python -m nba2.v2.refresh --write` -> `TLS/SSL connection has been closed (EOF)`). The
platform page-fetch tool DOES reach the official pages, so every row here was read through it
on 2026-11-17 and carries its official URL.

What this file does NOT do: it does not touch the published model. `nba2.v2.official.TEAMS`
is a static transcription; replacing a vintage is a coordinated re-cut across v2/v3/v4/v5
(see analysis/session-8892d20c-capture.md). Promoting only v2 would leave the published
pages on four different dates, which the README already names as a defect.

Nothing here is inferred. Every number is transcribed from the fetch listed under `sources`,
and `selftest()` re-derives the league identities that a transcription error would break.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "raw" / "refresh_2026-11-17"

STAMP_UTC = "2026-11-17T15:52:00Z"
SESSION = "arena/8892d20c-nba2"
METHOD = ("platform page-fetch tool (fetch_page); bash egress to nba.com/stats.nba.com/cdn.nba.com "
          "returns HTTP 000 from this sandbox, so every read is recorded with this method and its URL")

SOURCES = {
    "standings": "https://www.nba.com/standings",
    "schedule": "https://www.nba.com/schedule?date=2026-11-17",
    "team_trad": ("https://www.nba.com/stats/teams/traditional"
                  "?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame"),
    "team_opp": ("https://www.nba.com/stats/teams/opponent"
                 "?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame"),
    "team_adv": ("https://www.nba.com/stats/teams/advanced"
                 "?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame"),
    "injury_index": "https://official.nba.com/nba-injury-report-2026-27-season/",
}

# ------------------------------------------------------------------ official standings 11/17
# nba.com/standings, read 2026-11-17. Columns exactly as the page prints them:
#   w, l, conf_record, div_record, home, road, neutral, ot, last10, streak
# (home + road + neutral) must equal (w, l) for every club - the selftest enforces it.
STANDINGS = {
    # Eastern Conference
    "PHI": (12, 3, "12-3", "4-1", "6-2", "6-1", "0-0", "0-0", "8-2", "W 3"),
    "BOS": (11, 3, "10-2", "4-0", "6-1", "5-2", "0-0", "1-0", "8-2", "L 1"),
    "DET": (8, 4, "8-3", "0-0", "3-2", "5-2", "0-0", "1-0", "6-4", "L 1"),
    "MIA": (8, 6, "4-2", "1-1", "4-3", "4-3", "0-0", "1-0", "8-2", "W 5"),
    "ATL": (8, 6, "8-2", "4-1", "3-3", "5-3", "0-0", "0-1", "6-4", "W 1"),
    "NYK": (7, 6, "7-6", "2-3", "4-3", "3-3", "0-0", "1-0", "7-3", "W 1"),
    "CLE": (8, 7, "6-5", "2-0", "6-2", "2-5", "0-0", "1-0", "5-5", "W 2"),
    "ORL": (6, 7, "4-4", "0-2", "1-4", "5-3", "0-0", "0-1", "5-5", "W 4"),
    "TOR": (5, 8, "4-4", "0-3", "2-4", "3-4", "0-0", "0-1", "3-7", "L 4"),
    "IND": (5, 9, "3-6", "0-1", "2-4", "3-4", "0-1", "0-0", "3-7", "L 1"),
    "CHA": (4, 9, "4-7", "2-2", "3-4", "1-5", "0-0", "0-0", "2-8", "L 2"),
    "WAS": (4, 11, "4-8", "2-3", "2-5", "2-6", "0-0", "0-1", "2-8", "L 8"),
    "BKN": (3, 10, "2-8", "0-3", "1-4", "2-6", "0-0", "0-1", "3-7", "L 2"),
    "CHI": (3, 10, "2-9", "1-1", "1-4", "2-6", "0-0", "1-0", "2-8", "L 1"),
    "MIL": (1, 13, "1-10", "1-2", "1-7", "0-6", "0-0", "0-0", "0-10", "L 10"),
    # Western Conference
    "SAS": (12, 2, "11-2", "2-1", "5-2", "7-0", "0-0", "1-0", "10-0", "W 12"),
    "LAL": (12, 2, "7-2", "5-1", "5-1", "7-1", "0-0", "0-0", "9-1", "W 8"),
    "HOU": (11, 4, "6-3", "2-1", "7-1", "4-3", "0-0", "0-0", "6-4", "L 1"),
    "MIN": (10, 4, "6-2", "2-0", "6-2", "4-2", "0-0", "0-1", "7-3", "W 1"),
    "MEM": (10, 4, "7-3", "1-1", "3-4", "7-0", "0-0", "0-1", "6-4", "W 3"),
    "POR": (9, 4, "9-4", "4-1", "3-2", "6-2", "0-0", "0-0", "6-4", "L 1"),
    "OKC": (9, 5, "6-5", "1-2", "5-0", "4-5", "0-0", "0-0", "5-5", "W 1"),
    "DEN": (7, 5, "5-5", "0-2", "2-3", "4-2", "1-0", "1-0", "6-4", "L 1"),
    "GSW": (8, 6, "6-6", "3-2", "6-1", "2-5", "0-0", "1-0", "7-3", "L 3"),
    "DAL": (7, 7, "3-5", "1-3", "5-2", "2-5", "0-0", "0-0", "5-5", "L 3"),
    "PHX": (6, 7, "4-7", "2-2", "5-4", "1-3", "0-0", "0-0", "5-5", "W 1"),
    "LAC": (4, 8, "3-6", "1-4", "4-3", "0-5", "0-0", "0-1", "3-7", "W 2"),
    "NOP": (5, 10, "4-8", "1-1", "4-6", "1-4", "0-0", "2-1", "4-6", "W 1"),
    "SAC": (1, 12, "1-10", "0-2", "0-8", "1-4", "0-0", "0-0", "1-9", "L 6"),
    "UTA": (1, 13, "1-11", "0-2", "1-7", "0-6", "0-0", "0-2", "0-10", "L 12"),
}

# ------------------------------------------------- three official team-stat pages, 11/17
# traditional -> GP, PTS (points per game), +/- ; opponent -> Opp PTS (points allowed) ;
# advanced -> OffRtg, DefRtg, NetRtg, PACE, PIE. All read 2026-11-17, PerMode=PerGame,
# SeasonType=Regular+Season, Season=2026-27.
TEAMSTATS = {
    #      GP, PTS,    +/-,  OppPTS, OffRtg, DefRtg, NetRtg, PACE,   PIE
    "ATL": (14, 117.8, 1.7, 116.1, 112.8, 111.1, 1.7, 103.69, 49.0),
    "BKN": (13, 111.2, -6.7, 117.8, 110.8, 117.4, -6.6, 99.55, 45.9),
    "BOS": (14, 114.8, 11.5, 103.3, 118.2, 106.1, 12.1, 96.53, 55.4),
    "CHA": (13, 99.1, -10.8, 109.8, 102.5, 113.6, -11.1, 96.65, 42.7),
    "CHI": (13, 114.6, -11.3, 125.9, 109.1, 120.0, -10.9, 104.17, 44.9),
    "CLE": (15, 118.1, 2.3, 115.8, 116.9, 114.7, 2.2, 100.30, 51.5),
    "DAL": (14, 112.1, -2.5, 114.6, 111.8, 114.5, -2.7, 100.18, 48.6),
    "DEN": (12, 113.8, 0.7, 113.2, 115.1, 114.9, 0.2, 97.86, 52.2),
    "DET": (12, 115.7, 5.4, 110.3, 114.1, 109.2, 4.9, 99.48, 53.7),
    "GSW": (14, 115.1, 2.5, 112.6, 114.6, 112.3, 2.2, 99.58, 51.0),
    "HOU": (15, 117.8, 8.3, 109.5, 120.9, 112.3, 8.6, 97.50, 55.5),
    "IND": (14, 112.1, -2.4, 114.5, 110.9, 112.9, -2.0, 101.25, 49.6),
    "LAC": (12, 112.3, -4.2, 116.5, 111.4, 115.3, -3.9, 100.05, 48.3),
    "LAL": (14, 122.8, 7.9, 114.9, 122.1, 114.0, 8.0, 100.64, 54.2),
    "MEM": (14, 121.7, 9.4, 112.3, 120.0, 110.9, 9.1, 100.61, 54.3),
    "MIA": (14, 119.4, 0.2, 119.1, 116.0, 116.2, -0.1, 101.96, 50.6),
    "MIL": (14, 106.1, -13.6, 119.7, 105.4, 118.9, -13.6, 100.68, 42.1),
    "MIN": (14, 117.4, 11.3, 106.1, 115.2, 104.1, 11.1, 101.21, 55.1),
    "NOP": (15, 115.8, -7.1, 122.9, 111.7, 118.4, -6.7, 101.62, 46.6),
    "NYK": (13, 109.9, 5.9, 104.0, 113.7, 108.2, 5.5, 95.66, 53.5),
    "OKC": (14, 112.1, 5.1, 107.1, 113.4, 108.4, 5.1, 98.82, 53.8),
    "ORL": (13, 108.8, -3.3, 112.2, 110.5, 113.0, -2.6, 98.10, 48.6),
    "PHI": (15, 114.1, 2.8, 111.3, 113.7, 111.1, 2.6, 100.23, 51.3),
    "PHX": (13, 113.0, -3.4, 116.4, 114.5, 117.5, -3.0, 98.88, 48.5),
    "POR": (13, 117.9, 6.5, 111.4, 117.2, 110.6, 6.6, 100.65, 52.8),
    "SAC": (13, 107.8, -13.5, 121.2, 106.8, 119.8, -13.0, 101.08, 42.6),
    "SAS": (14, 118.8, 12.9, 105.9, 119.2, 106.6, 12.6, 98.77, 56.9),
    "TOR": (13, 113.8, 1.0, 112.8, 113.6, 112.2, 1.4, 99.55, 49.0),
    "UTA": (14, 107.1, -10.9, 118.0, 105.1, 116.2, -11.1, 100.22, 45.0),
    "WAS": (15, 111.3, -7.9, 119.2, 109.9, 117.6, -7.8, 99.91, 45.8),
}

# ------------------------------------------------------ schedule: tonight's slate (T+0)
# nba.com/schedule?date=2026-11-17. Five games. Tip times are the ones the page prints next
# to each card; game ids are the ones in each official /game/ link.
SLATE_11_17 = [
    # game_id,      date,        tip_et,  away, home, arena,                city,           state
    ("0022600253", "2026-11-17", "19:30", "NYK", "TOR", "Scotiabank Arena", "Toronto", "ON"),
    ("0022600254", "2026-11-17", "20:00", "POR", "MIN", "Target Center", "Minneapolis", "MN"),
    ("0022600255", "2026-11-17", "20:00", "DET", "SAS", "Frost Bank Center", "San Antonio", "TX"),
    ("0022600257", "2026-11-17", "22:30", "UTA", "LAC", "Intuit Dome", "Inglewood", "CA"),
    ("0022600256", "2026-11-17", "23:00", "CHA", "LAL", "Crypto.com Arena", "Los Angeles", "CA"),
]

# The other dates of the 3-day window were read (11/18: 12 games, 11/19: 4, 11/20: 9 Cup
# games) but their per-game rows are deliberately NOT transcribed here. Reason, recorded
# rather than papered over: on the 11/18-11/20 cards the fetched text places the tip-time
# label above a broadcast strip, and a row-by-row re-read is required before a tip time can
# be attached to a specific game id. A wrong tip time is worse than a blank one.
WINDOW_INVENTORY_UNTRANSCRIBED = {
    "2026-11-18": {"games_on_page": 12, "reason": "per-game rows pending re-read; tip labels interleave with broadcast strips"},
    "2026-11-19": {"games_on_page": 4, "reason": "per-game rows pending re-read; tip labels interleave with broadcast strips"},
    "2026-11-20": {"games_on_page": 9, "reason": "Emirates NBA Cup group cards; tip labels interleave with broadcast strips"},
}


def selftest() -> list[str]:
    """Identities a transcription error breaks. Returns a list of problems (empty = clean)."""
    problems: list[str] = []
    if len(STANDINGS) != 30:
        problems.append(f"standings has {len(STANDINGS)} clubs, expected 30")
    if len(TEAMSTATS) != 30:
        problems.append(f"team stats has {len(TEAMSTATS)} clubs, expected 30")
    if set(STANDINGS) != set(TEAMSTATS):
        problems.append(f"club sets differ: {set(STANDINGS) ^ set(TEAMSTATS)}")

    # 1. every club's home+road+neutral must reproduce its own W-L
    for t, (w, l, _conf, _div, home, road, neu, _ot, _l10, _st) in STANDINGS.items():
        hw, hl = (int(x) for x in home.split("-"))
        rw, rl = (int(x) for x in road.split("-"))
        nw, nl = (int(x) for x in neu.split("-"))
        if hw + rw + nw != w or hl + rl + nl != l:
            problems.append(f"{t}: home+road+neutral {hw + rw + nw}-{hl + rl + nl} != W-L {w}-{l}")

    wins = sum(v[0] for v in STANDINGS.values())
    losses = sum(v[1] for v in STANDINGS.values())
    if wins != losses:
        problems.append(f"league wins {wins} != losses {losses}")

    hw = sum(int(v[4].split("-")[0]) for v in STANDINGS.values())
    hl = sum(int(v[4].split("-")[1]) for v in STANDINGS.values())
    rw = sum(int(v[5].split("-")[0]) for v in STANDINGS.values())
    rl = sum(int(v[5].split("-")[1]) for v in STANDINGS.values())
    if hw != rl:
        problems.append(f"home wins {hw} != road losses {rl}")
    if hl != rw:
        problems.append(f"home losses {hl} != road wins {rw}")

    # 2. the three team-stat pages must describe the same games as the standings card
    for t, (w, l, *_rest) in STANDINGS.items():
        gp = TEAMSTATS[t][0]
        if gp != w + l:
            problems.append(f"{t}: trad-page GP {gp} != standings W+L {w + l}")

    # 3. points scored must equal points allowed league-wide (both are per-game averages
    #    rounded to 0.1, so the weighted difference is bounded by 0.1 * team-games)
    tg = sum(v[0] for v in TEAMSTATS.values())
    pf = sum(TEAMSTATS[t][1] * TEAMSTATS[t][0] for t in TEAMSTATS)
    pa = sum(TEAMSTATS[t][3] * TEAMSTATS[t][0] for t in TEAMSTATS)
    bound = 0.1 * tg
    if abs(pf - pa) > bound:
        problems.append(f"points imbalance {pf - pa:.1f} exceeds rounding bound {bound:.1f}")

    # 4. The official pages must describe one season. Margin per game should reconstruct from
    #    NetRtg x pace / 100. This is NOT an exact identity - the three pages round
    #    independently and rate/pace are per-100-possession while PTS is per game - so the
    #    residual is published per club and only a residual large enough to signal a
    #    transcription error (> 1.5 pts/game) fails the capture. ORL is the observed outlier
    #    on the official pages themselves (see residual below); it is reported, not smoothed.
    for t, (_gp, pts, plus_minus, opp, _o, _d, net, pace, _pie) in TEAMSTATS.items():
        expected_margin = net * pace / 100.0
        actual_margin = pts - opp
        if abs(expected_margin - actual_margin) > 1.5:
            problems.append(f"{t}: NetRtg x pace implies {expected_margin:.2f} pts/game but "
                            f"PTS-OppPTS is {actual_margin:.1f}")

    # 5. no duplicate game id, and every club appears at most once on tonight's slate
    ids = [g[0] for g in SLATE_11_17]
    if len(ids) != len(set(ids)):
        problems.append("duplicate game id on the 11/17 slate")
    clubs = [c for g in SLATE_11_17 for c in (g[3], g[4])]
    if len(clubs) != len(set(clubs)):
        problems.append("a club appears twice on the 11/17 slate")
    for g in SLATE_11_17:
        if g[3] not in STANDINGS or g[4] not in STANDINGS:
            problems.append(f"slate club not in standings: {g[3]}@{g[4]}")
    return problems


def main() -> int:
    problems = selftest()
    OUT.mkdir(parents=True, exist_ok=True)

    tg = sum(v[0] for v in TEAMSTATS.values())
    pf = sum(TEAMSTATS[t][1] * TEAMSTATS[t][0] for t in TEAMSTATS)
    pa = sum(TEAMSTATS[t][3] * TEAMSTATS[t][0] for t in TEAMSTATS)

    (OUT / "standings_2026-11-17.json").write_text(json.dumps({
        "schema": "nba2.standings-official.v2",
        "as_of": "2026-11-17",
        "session": SESSION,
        "retrieved_at_utc": STAMP_UTC,
        "retrieval_method": METHOD,
        "source_url": SOURCES["standings"],
        "source_class": "official",
        "columns": ["team", "w", "l", "conf", "div", "home", "road", "neutral", "ot", "last10", "streak"],
        "records": [{"team": t, "w": v[0], "l": v[1], "conf": v[2], "div": v[3],
                     "home": v[4], "road": v[5], "neutral": v[6], "ot": v[7],
                     "last10": v[8], "streak": v[9],
                     "source_url": SOURCES["standings"], "source_class": "official"}
                    for t, v in STANDINGS.items()],
    }, indent=1) + "\n")

    (OUT / "team_stats_2026-11-17.json").write_text(json.dumps({
        "schema": "nba2.team-stats-3page.v1",
        "as_of": "2026-11-17",
        "session": SESSION,
        "retrieved_at_utc": STAMP_UTC,
        "retrieval_method": METHOD,
        "source_class": "official",
        "pages": {
            "traditional": {"url": SOURCES["team_trad"], "columns": ["gp", "pts", "plus_minus"]},
            "opponent": {"url": SOURCES["team_opp"], "columns": ["opp_pts"]},
            "advanced": {"url": SOURCES["team_adv"],
                         "columns": ["off_rtg", "def_rtg", "net_rtg", "pace", "pie"]},
        },
        "records": [{"team": t, "gp": v[0], "pts": v[1], "plus_minus": v[2], "opp_pts": v[3],
                     "off_rtg": v[4], "def_rtg": v[5], "net_rtg": v[6], "pace": v[7], "pie": v[8],
                     # one page per field group, kept separate so a reviewer can re-read each
                     "source_url": SOURCES["team_adv"],
                     "source_urls": {"pts_plus_minus": SOURCES["team_trad"],
                                     "opp_pts": SOURCES["team_opp"],
                                     "ratings_pace_pie": SOURCES["team_adv"]},
                     "source_class": "official"}
                    for t, v in TEAMSTATS.items()],
        "crosschecks": {
            "n_clubs": len(TEAMSTATS),
            "team_games": tg,
            "league_games": tg / 2,
            "pts_for_weighted": round(pf, 1),
            "pts_against_weighted": round(pa, 1),
            "pts_diff": round(pf - pa, 1),
            "rounding_bound": round(0.1 * tg, 1),
            "pts_balance_within_bound": abs(pf - pa) <= 0.1 * tg,
            "gp_matches_standings_wl": all(TEAMSTATS[t][0] == STANDINGS[t][0] + STANDINGS[t][1]
                                           for t in TEAMSTATS),
            "margin_vs_netrtg_residuals": {
                t: round((TEAMSTATS[t][1] - TEAMSTATS[t][3]) - TEAMSTATS[t][6] * TEAMSTATS[t][7] / 100.0, 2)
                for t in TEAMSTATS
            },
            "margin_vs_netrtg_note": ("(PTS - OppPTS) minus (NetRtg x PACE / 100), per club. Zero would mean "
                                      "the traditional, opponent and advanced pages are exactly consistent. "
                                      "Small non-zero values are expected from independent rounding of "
                                      "per-game and per-100-possession rates; the largest residual is flagged."),
            "margin_vs_netrtg_max_abs": round(max(
                abs((TEAMSTATS[t][1] - TEAMSTATS[t][3]) - TEAMSTATS[t][6] * TEAMSTATS[t][7] / 100.0)
                for t in TEAMSTATS), 2),
        },
    }, indent=1) + "\n")

    (OUT / "slate_2026-11-17.json").write_text(json.dumps({
        "schema": "nba2.slate.v2",
        "window": {"start": "2026-11-17", "end": "2026-11-20", "days": 3},
        "anchor_date": "2026-11-17",
        "session": SESSION,
        "retrieved_at_utc": STAMP_UTC,
        "retrieval_method": METHOD,
        "source_url": SOURCES["schedule"],
        "source_class": "official",
        "games": [{"game_id": g[0], "date": g[1], "tip_et": g[2], "away": g[3], "home": g[4],
                   "arena": g[5], "city": g[6], "state": g[7],
                   # per-row source: the official game page the id/tip/venue were read from
                   "source_url": f"https://www.nba.com/game/{g[3].lower()}-vs-{g[4].lower()}-{g[0]}",
                   "source_class": "official"} for g in SLATE_11_17],
        "n_games_transcribed": len(SLATE_11_17),
        "window_inventory_untranscribed": WINDOW_INVENTORY_UNTRANSCRIBED,
        "note": ("Only the T+0 (2026-11-17) cards are transcribed row by row. The later dates of "
                 "the window were read for inventory and are deliberately blank per game until a "
                 "row-by-row re-read attaches each tip time to its own game id."),
    }, indent=1) + "\n")

    (OUT / "capture_index.json").write_text(json.dumps({
        "schema": "nba2.capture-index.v1",
        "retrieved_utc": STAMP_UTC,
        "session": SESSION,
        "method": METHOD,
        "source_pages": {
            "standings": {"name": "NBA.com Standings (official)", "url": SOURCES["standings"],
                          "read": "30 clubs: W, L, CONF, DIV, HOME, ROAD, NEUTRAL, OT, LAST10, STREAK"},
            "schedule": {"name": "NBA.com Schedule (official)", "url": SOURCES["schedule"],
                         "read": "the five 2026-11-17 cards in full (game id, ET tip, arena, city, state); "
                                 "inventory counts for 11/18-11/20"},
            "team_trad": {"name": "NBA.com Stats - Teams Traditional (official)", "url": SOURCES["team_trad"],
                          "read": "30 rows: GP, PTS, +/- (plus FG/rebound/assist splits)"},
            "team_opp": {"name": "NBA.com Stats - Teams Opponent (official)", "url": SOURCES["team_opp"],
                         "read": "30 rows: Opp PTS (points allowed per game) plus opponent shooting splits"},
            "team_adv": {"name": "NBA.com Stats - Teams Advanced (official)", "url": SOURCES["team_adv"],
                         "read": "30 rows: OffRtg, DefRtg, NetRtg, PACE, PIE, POSS"},
            "injury_index": {"name": "NBA Official - Injury Report index (official)", "url": SOURCES["injury_index"],
                             "read": "the filing rules and every published 11/17 release from 12:00 a.m. ET to 10:30 a.m. ET"},
        },
        "unread": {
            "injury_pdf_rows": {
                "what": "The row-level contents of the 2026-11-17 injury releases",
                "why": ("The index was read and the newest release URL of 2026-11-17 was identified, but the "
                        "~100 row transcriptions were not performed in this session's scope. The published "
                        "injury pages keep their own dated release with its own stamp; nothing is back-filled."),
                "attempted_url": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-17_10_30AM.pdf",
            },
            "window_dates_11_18_to_11_20": {
                "what": "Per-game rows for 11/18, 11/19 and 11/20",
                "why": "inventory counts read; per-game transcription pending a row-by-row re-read (see slate file)",
                "attempted_url": SOURCES["schedule"],
            },
        },
        "selftest": {"problems": problems, "clean": not problems},
        "files": sorted(p.name for p in OUT.glob("*.json")),
    }, indent=1) + "\n")

    for p in problems:
        print(f"  [FAIL] {p}")
    print(f"capture written under {OUT.relative_to(ROOT)}: "
          f"{len(STANDINGS)} standings rows, {len(TEAMSTATS)} team-stat rows, "
          f"{len(SLATE_11_17)} slate rows; selftest {'CLEAN' if not problems else 'FAILED'}")
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
