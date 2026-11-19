"""Write the 2026-11-19 official capture, then verify it arithmetically.

Method, recorded because it is the whole point: bash egress from this sandbox to nba.com /
stats.nba.com / cdn.nba.com returns HTTP 000 (verified by prior sessions, re-noted here), and
stats.nba.com additionally closes the TLS connection. The platform page-fetch tool DOES reach
the official pages, so every row here was read through it on 2026-11-19 and carries its official
URL. This is the same method session `arena/8892d20c-nba2` used for its 2026-11-17 capture and
the same method `nba2/v2/official.py` documents.

This capture executes step 1 of the RQ-8892-02 re-cut spec
(`analysis/session-8892d20c-capture.md` §4): the model re-cut anchors here, not on the
runner-blocked bot capture (`data/raw/capture_2026-11-18/team_stats_2026-11-18.json`, whose
three team-stat pages are all `status: unavailable` — measured, not assumed).

Reads performed 2026-11-19 (UTC 11:15-12:30), all through the platform page-fetch tool:
* ``www.nba.com/standings`` ................ 30 clubs, W/L + all splits ............. fetched OK
* ``www.nba.com/stats/teams/traditional`` .. 30 rows GP/PTS/+/- (PerGame) .......... fetched OK
* ``www.nba.com/stats/teams/opponent`` ..... 30 rows Opp PTS (PerGame) .............. fetched OK
* ``www.nba.com/stats/teams/advanced`` ..... 30 rows OffRtg/DefRtg/NetRtg/PACE/PIE . fetched OK
* ``www.nba.com/games?date=2026-11-19..22`` 4 day strips, 26 window games .......... fetched OK
* ``www.nba.com/games?date=2026-11-18`` .... 12 official finals .................... fetched OK
* ``statsdmz.nba.com/pdfs/20261118/*`` ..... 12 official gamebook PDFs (line scores) . fetched OK
* ``official.nba.com/nba-injury-report-2026-27-season/`` index + filing rules ..... fetched OK
* ``Injury-Report_2026-11-19_07_15AM.pdf``  44 rows (incl. NOT YET SUBMITTED) ...... fetched OK

Nothing is inferred. Every number is transcribed from the fetch listed under ``sources``, and
``selftest()`` re-derives the league identities that a transcription error would break.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "raw" / "refresh_2026-11-19"
sys.path.insert(0, str(Path(__file__).resolve().parent))

from capture_notes import (  # noqa: E402  (the transcription itself, kept separate for review)
    ADV_1119,
    FINALS_1118,
    INJURY_1119_0715AM,
    OPP_1119,
    SLATE_1119_WINDOW,
    STANDINGS_1119,
    TRAD_1119,
)

STAMP_UTC = "2026-11-19T12:32:00Z"
SESSION = "arena/6b9f3bbe-nba2"
METHOD = ("platform page-fetch tool (fetch_page); bash egress to nba.com/stats.nba.com/cdn.nba.com "
          "returns HTTP 000 from this sandbox, so every read is recorded with this method and its URL")

SOURCES = {
    "standings": "https://www.nba.com/standings",
    "team_trad": ("https://www.nba.com/stats/teams/traditional"
                  "?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame"),
    "team_opp": ("https://www.nba.com/stats/teams/opponent"
                 "?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame"),
    "team_adv": ("https://www.nba.com/stats/teams/advanced"
                 "?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame"),
    "games_strip": "https://www.nba.com/games?date={date}",
    "injury_index": "https://official.nba.com/nba-injury-report-2026-27-season/",
    "injury_pdf": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-19_07_15AM.pdf",
}


def selftest() -> list[str]:
    """Identities a transcription error breaks. Returns a list of problems (empty = clean)."""
    problems: list[str] = []
    if len(STANDINGS_1119) != 30:
        problems.append(f"standings has {len(STANDINGS_1119)} clubs, expected 30")
    if len(TRAD_1119) != 30 or len(OPP_1119) != 30 or len(ADV_1119) != 30:
        problems.append("team-stat pages do not each have 30 clubs")
    if not (set(STANDINGS_1119) == set(TRAD_1119) == set(OPP_1119) == set(ADV_1119)):
        problems.append(f"club sets differ: {set(STANDINGS_1119) ^ set(TRAD_1119)}")

    # 1. every club's home+road+neutral must reproduce its own W-L
    for t, (w, l, _conf, _div, home, road, neu, _ot, _l10, _st) in STANDINGS_1119.items():
        hw, hl = (int(x) for x in home.split("-"))
        rw, rl = (int(x) for x in road.split("-"))
        nw, nl = (int(x) for x in neu.split("-"))
        if hw + rw + nw != w or hl + rl + nl != l:
            problems.append(f"{t}: home+road+neutral {hw + rw + nw}-{hl + rl + nl} != W-L {w}-{l}")

    wins = sum(v[0] for v in STANDINGS_1119.values())
    losses = sum(v[1] for v in STANDINGS_1119.values())
    if wins != losses:
        problems.append(f"league wins {wins} != losses {losses}")

    hw = sum(int(v[4].split("-")[0]) for v in STANDINGS_1119.values())
    hl = sum(int(v[4].split("-")[1]) for v in STANDINGS_1119.values())
    rw = sum(int(v[5].split("-")[0]) for v in STANDINGS_1119.values())
    rl = sum(int(v[5].split("-")[1]) for v in STANDINGS_1119.values())
    if hw != rl:
        problems.append(f"home wins {hw} != road losses {rl}")
    if hl != rw:
        problems.append(f"home losses {hl} != road wins {rw}")

    # 2. the three team-stat pages must describe the same games as the standings card
    for t, (w, l, *_rest) in STANDINGS_1119.items():
        if TRAD_1119[t][0] != w + l:
            problems.append(f"{t}: trad-page GP {TRAD_1119[t][0]} != standings W+L {w + l}")

    # 3. points scored must equal points allowed league-wide (both are per-game averages
    #    rounded to 0.1, so the weighted difference is bounded by 0.1 * team-games)
    tg = sum(v[0] for v in TRAD_1119.values())
    pf = sum(TRAD_1119[t][1] * TRAD_1119[t][0] for t in TRAD_1119)
    pa = sum(OPP_1119[t] * TRAD_1119[t][0] for t in TRAD_1119)
    bound = 0.1 * tg
    if abs(pf - pa) > bound:
        problems.append(f"points imbalance {pf - pa:.1f} exceeds rounding bound {bound:.1f}")

    # 4. PTS - OppPTS must reproduce the traditional page's own +/- within rounding (0.11),
    #    and NetRtg x pace / 100 within the 1.5 pts/game transcription-failure bound
    for t in TRAD_1119:
        margin = TRAD_1119[t][1] - OPP_1119[t]
        if abs(margin - TRAD_1119[t][2]) > 0.11:
            problems.append(f"{t}: PTS-OppPTS {margin:.1f} vs +/- {TRAD_1119[t][2]:.1f}")
        expected_margin = ADV_1119[t][2] * ADV_1119[t][3] / 100.0
        if abs(expected_margin - margin) > 1.5:
            problems.append(f"{t}: NetRtg x pace implies {expected_margin:.2f} pts/game but "
                            f"PTS-OppPTS is {margin:.1f}")

    # 5. the 11/18 finals: each quarter row must sum to its own final, no duplicate id,
    #    and every club on the window slate appears at most once per date
    ids = [g[0] for g in FINALS_1118]
    if len(ids) != len(set(ids)):
        problems.append("duplicate game id in the 11/18 finals")
    for gid, home, away, hp, ap, hq, aq in FINALS_1118:
        if sum(hq) != hp or sum(aq) != ap:
            problems.append(f"{gid}: quarter rows {hq}/{aq} do not sum to {hp}/{ap}")
        if hp == ap:
            problems.append(f"{gid}: tied final")
    per_date: dict[str, set[str]] = {}
    for g in SLATE_1119_WINDOW:
        per_date.setdefault(g[0], set())
        for c in (g[2], g[3]):
            if c in per_date[g[0]]:
                problems.append(f"{c} appears twice on {g[0]}")
            per_date[g[0]].add(c)
            if c not in STANDINGS_1119:
                problems.append(f"slate club not in standings: {c}")
    if len(SLATE_1119_WINDOW) != 26:
        problems.append(f"window slate has {len(SLATE_1119_WINDOW)} games, expected 26 (4+9+6+7)")
    return problems


def main() -> int:
    problems = selftest()
    OUT.mkdir(parents=True, exist_ok=True)

    tg = sum(v[0] for v in TRAD_1119.values())
    pf = sum(TRAD_1119[t][1] * TRAD_1119[t][0] for t in TRAD_1119)
    pa = sum(OPP_1119[t] * TRAD_1119[t][0] for t in TRAD_1119)

    (OUT / "standings_2026-11-19.json").write_text(json.dumps({
        "schema": "nba2.standings-official.v2",
        "as_of": "2026-11-19",
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
                    for t, v in sorted(STANDINGS_1119.items())],
    }, indent=1) + "\n")

    (OUT / "team_stats_2026-11-19.json").write_text(json.dumps({
        "schema": "nba2.team-stats-3page.v1",
        "as_of": "2026-11-19",
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
        "records": [{"team": t, "gp": TRAD_1119[t][0], "pts": TRAD_1119[t][1],
                     "plus_minus": TRAD_1119[t][2], "opp_pts": OPP_1119[t],
                     "off_rtg": ADV_1119[t][0], "def_rtg": ADV_1119[t][1],
                     "net_rtg": ADV_1119[t][2], "pace": ADV_1119[t][3], "pie": ADV_1119[t][4],
                     # one page per field group, kept separate so a reviewer can re-read each
                     "source_urls": {"pts_plus_minus": SOURCES["team_trad"],
                                     "opp_pts": SOURCES["team_opp"],
                                     "ratings_pace_pie": SOURCES["team_adv"]},
                     "source_class": "official"}
                    for t in sorted(TRAD_1119)],
        "crosschecks": {
            "n_clubs": len(TRAD_1119),
            "team_games": tg,
            "league_games": tg / 2,
            "pts_for_weighted": round(pf, 1),
            "pts_against_weighted": round(pa, 1),
            "pts_diff": round(pf - pa, 1),
            "rounding_bound": round(0.1 * tg, 1),
            "pts_balance_within_bound": abs(pf - pa) <= 0.1 * tg,
            "gp_matches_standings_wl": all(TRAD_1119[t][0] == STANDINGS_1119[t][0] + STANDINGS_1119[t][1]
                                           for t in TRAD_1119),
            "margin_vs_netrtg_residuals": {
                t: round((TRAD_1119[t][1] - OPP_1119[t]) - ADV_1119[t][2] * ADV_1119[t][3] / 100.0, 2)
                for t in sorted(TRAD_1119)
            },
            "margin_vs_netrtg_note": ("(PTS - OppPTS) minus (NetRtg x PACE / 100), per club. Zero would mean "
                                      "the traditional, opponent and advanced pages are exactly consistent. "
                                      "Small non-zero values are expected from independent rounding of "
                                      "per-game and per-100-possession rates; the largest residual is flagged."),
            "margin_vs_netrtg_max_abs": round(max(
                abs((TRAD_1119[t][1] - OPP_1119[t]) - ADV_1119[t][2] * ADV_1119[t][3] / 100.0)
                for t in TRAD_1119), 2),
        },
    }, indent=1) + "\n")

    (OUT / "slate_2026-11-19.json").write_text(json.dumps({
        "schema": "nba2.slate.v3",
        "window": {"start": "2026-11-19", "end": "2026-11-22", "days": 3},
        "anchor_date": "2026-11-19",
        "session": SESSION,
        "retrieved_at_utc": STAMP_UTC,
        "retrieval_method": METHOD,
        "source_url": SOURCES["games_strip"].format(date="2026-11-19"),
        "source_class": "official",
        "games": [{"game_id": g[4], "date": g[0], "tip_et": g[1], "away": g[2], "home": g[3],
                   "arena": None, "city": None,
                   "arena_status": "unverified — www.nba.com/games?date= day strips do not print the arena",
                   "cup_group": g[5],
                   "source_url": SOURCES["games_strip"].format(date=g[0]),
                   "game_url": f"https://www.nba.com/game/{g[2].lower()}-vs-{g[3].lower()}-{g[4]}",
                   "source_class": "official"}
                  for g in SLATE_1119_WINDOW],
        "n_games_transcribed": len(SLATE_1119_WINDOW),
        "per_date_counts": {"2026-11-19": 4, "2026-11-20": 9, "2026-11-21": 6, "2026-11-22": 7},
        "note": ("Every date of the 3-day window (T+0 .. T+3) is transcribed row by row from the "
                 "official /games day strips, including the Emirates NBA Cup group labels the 11/20 "
                 "cards print. Arena/city are blank: the day strip does not print them and they are "
                 "not guessed (travel.py uses team-keyed arena coordinates, so travel legs are "
                 "unaffected)."),
    }, indent=1) + "\n")

    finals_out = ROOT / "data" / "raw" / "finals_2026-11-18.json"
    finals_out.write_text(json.dumps({
        "source": "NBA.com Games & Scores day strip (www.nba.com/games?date=2026-11-18) — finals; "
                  "quarter rows from the official gamebook PDFs (statsdmz.nba.com/pdfs/20261118/), "
                  "each required to sum to the printed final",
        "retrieved_at_utc": STAMP_UTC,
        "retrieved_by": SESSION,
        "retrieval_method": METHOD,
        "date": "2026-11-18",
        "source_class": "official",
        "expected_window_games": 12,
        "games_missing_from_payload": [],
        "records": [{"game_id": g[0], "date": "2026-11-18", "home_team": g[1], "away_team": g[2],
                     "home_pts": g[3], "away_pts": g[4], "status": "final",
                     "final_source_url": f"https://www.nba.com/game/{g[2].lower()}-vs-{g[1].lower()}-{g[0]}",
                     "home_q": list(g[5]), "ot_periods": 0, "away_q": list(g[6]),
                     "gamebook_url": f"https://statsdmz.nba.com/pdfs/20261118/20261118_{g[2]}{g[1]}_book.pdf",
                     "source": f"https://www.nba.com/game/{g[2].lower()}-vs-{g[1].lower()}-{g[0]}"}
                    for g in FINALS_1118],
    }, indent=1) + "\n")

    (OUT / "injury_release_2026-11-19.json").write_text(json.dumps({
        "schema": "nba2.injury-transcript.v2",
        "revision_time_et": "2026-11-19 07:15 AM ET",
        "retrieval_time_utc": STAMP_UTC,
        "pdf_url": SOURCES["injury_pdf"],
        "index_url": SOURCES["injury_index"],
        "session": SESSION,
        "retrieval_method": METHOD,
        "source_class": "official",
        "rows": [{"game_date": r[0], "matchup": r[1], "team": r[2] or None,
                  "team_status": ("carried-over" if not r[2] and r[3] else
                                  ("not_submitted" if not r[3] else "stated")),
                  "player": r[3] or None, "current_status": r[4], "reason": r[5],
                  "source_url": SOURCES["injury_pdf"], "source_class": "official"}
                 for r in INJURY_1119_0715AM],
        "note": ("Transcribed from the newest release listed on the official index at retrieval time "
                 "(07:15 AM ET). The PDF page break drops the team cell on continuation rows "
                 "(Kuminga, Pullin) — the PDF's own block-continuation convention carries the "
                 "previous team block (Minnesota, NYK@MIN); this is the same FLAG-V2-INJ-ATTR "
                 "pattern the 11/14 transcription documented. The NYK@MIN listing contains no New "
                 "York player rows in this release: recorded as read, not inferred."),
        "filing_rules_verbatim": (
            "NBA teams must report information concerning player injuries, illnesses, other medical "
            "conditions, or rest for all NBA games. By 5 p.m. local time the day before a game "
            "(other than the second day of a back-to-back), teams must designate a participation "
            "status and identify a specific injury, illness, other medical condition, or other "
            "reason for any player whose participation in the game may be affected for any reason. "
            "For the second game of a back-to-back, teams must report the above information by "
            "1 p.m. local time on the day of the game. In addition, teams are required to submit a "
            "game-day injury report between 11 a.m. and 1 p.m. local time (and between 8 and 10 "
            "a.m. for tip-offs 5 p.m. or earlier) on game days (besides the second game of a "
            "back-to-back). Reports are updated on a continual basis throughout the day."),
    }, indent=1) + "\n")

    (OUT / "capture_index.json").write_text(json.dumps({
        "schema": "nba2.capture-index.v1",
        "retrieved_utc": STAMP_UTC,
        "session": SESSION,
        "method": METHOD,
        "source_pages": {
            "standings": {"name": "NBA.com Standings (official)", "url": SOURCES["standings"],
                          "read": "30 clubs: W, L, CONF, DIV, HOME, ROAD, NEUTRAL, OT, LAST10, STREAK"},
            "team_trad": {"name": "NBA.com Stats - Teams Traditional (official)", "url": SOURCES["team_trad"],
                          "read": "30 rows: GP, PTS, +/- (plus FG/rebound/assist splits)"},
            "team_opp": {"name": "NBA.com Stats - Teams Opponent (official)", "url": SOURCES["team_opp"],
                         "read": "30 rows: Opp PTS (points allowed per game) plus opponent shooting splits"},
            "team_adv": {"name": "NBA.com Stats - Teams Advanced (official)", "url": SOURCES["team_adv"],
                         "read": "30 rows: OffRtg, DefRtg, NetRtg, PACE, PIE, POSS"},
            "window_slate": {"name": "NBA.com Games & Scores day strips (official)",
                             "url": SOURCES["games_strip"].format(date="2026-11-19"),
                             "read": "26 window games (11/19: 4, 11/20: 9 Cup, 11/21: 6, 11/22: 7) with game ids and ET tips"},
            "finals_1118": {"name": "NBA.com Games & Scores 11/18 day strip + official gamebooks",
                            "url": "https://www.nba.com/games?date=2026-11-18",
                            "read": "12 finals cross-checked against 12 gamebook line scores"},
            "injury_index": {"name": "NBA Official - Injury Report index (official)",
                             "url": SOURCES["injury_index"],
                             "read": "the filing rules verbatim and the newest 11/19 release (07:15 AM ET)"},
        },
        "unread": {
            "game_day_injury_reports_11am_1pm": {
                "what": "The 11/19 game-day reports (11 a.m.-1 p.m. local window had not elapsed)",
                "why": "Retrieval happened ~07:20 ET, before the game-day filing window; the 07:15 AM "
                       "release is the newest that existed. The next scheduled refresh re-reads it.",
                "attempted_url": SOURCES["injury_pdf"],
            },
            "slate_arenas": {
                "what": "Arena/city per window game",
                "why": "www.nba.com/games?date= day strips do not print the arena; blank by policy.",
                "attempted_url": SOURCES["games_strip"].format(date="2026-11-19"),
            },
        },
        "selftest": {"problems": problems, "clean": not problems},
        "files": sorted(p.name for p in OUT.glob("*.json")) + ["../finals_2026-11-18.json"],
    }, indent=1) + "\n")

    for p in problems:
        print(f"  [FAIL] {p}")
    print(f"capture written under {OUT.relative_to(ROOT)}: "
          f"{len(STANDINGS_1119)} standings rows, {len(TRAD_1119)} team-stat rows, "
          f"{len(SLATE_1119_WINDOW)} slate rows, {len(FINALS_1118)} finals, "
          f"{len(INJURY_1119_0715AM)} injury rows; selftest {'CLEAN' if not problems else 'FAILED'}")
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
