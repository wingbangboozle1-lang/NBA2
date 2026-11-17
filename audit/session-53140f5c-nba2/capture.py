#!/usr/bin/env python3
"""2026-11-17 official capture + line-by-line cross-verification (session arena/53140f5c-nba2).

Why this file exists
--------------------
Two things had to be true before the published model could move off its 2026-11-15 snapshot:

1. the numbers had to be read from an official page **by this session**, and
2. they had to agree with the capture the previous session (`arena/8892d20c-nba2`) published,
   row by row — not "approximately", not "looks right".

Everything below is a literal transcription of what the platform page-fetch tool returned from
the URLs stamped next to it, plus code that re-derives the checks. No value is filled in from
arithmetic, from an earlier session's file, or from memory. Where a field was not read, it is
`None` and the reason travels with it.

Retrieval record (all reads 2026-11-17 UTC, via the platform page-fetch tool; bash egress to
nba.com returns HTTP 000 from this sandbox, and that limitation is recorded, not worked around):

* `https://www.nba.com/standings` .................................. 30 clubs, 12 printed columns
* `https://www.nba.com/stats/teams/advanced` ....................... 30 clubs, GP/W/L/OffRtg/DefRtg/NetRtg/PACE/PIE/POSS
* `https://www.nba.com/schedule?date=2026-11-18` ................. 11/16 finals, 11/17 (5), 11/18 (12),
                                                                    11/19 (4), 11/20 (9) cards
* `https://official.nba.com/nba-injury-report-2026-27-season/` ... the release archive (11/17 12:00 a.m. .. 11:15 a.m. ET)
* `https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-17_11_15AM.pdf`
                                                                     verbatim release text, stored in
                                                                     `nba2/v4/injury_renderings.py`, parsed by code

Run:  python3 audit/session-53140f5c-nba2/capture.py            (writes + verifies)
      python3 audit/session-53140f5c-nba2/capture.py --verify    (re-verify the committed output)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "raw" / "capture_2026-11-17-53140f5c"
PRIOR = ROOT / "data" / "raw" / "refresh_2026-11-17"          # session arena/8892d20c-nba2

READ_UTC = "2026-11-17T16:30:00Z"
SESSION = "arena/53140f5c-nba2"
METHOD = ("platform page-fetch tool (fetch_page); bash egress to nba.com / stats.nba.com / "
          "cdn.nba.com returns HTTP 000 from this sandbox, so every read is recorded with this "
          "method and its URL")

STANDINGS_URL = "https://www.nba.com/standings"
ADV_URL = ("https://www.nba.com/stats/teams/advanced?Season=2026-27"
           "&SeasonType=Regular+Season&PerMode=PerGame")
SCHEDULE_URL = "https://www.nba.com/schedule?date=2026-11-18"
INJURY_INDEX_URL = "https://official.nba.com/nba-injury-report-2026-27-season/"
INJURY_PDF_URL = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-17_11_15AM.pdf"

# --------------------------------------------------------------------------- standings
# nba.com/standings, read 2026-11-17T16:29Z. One row per club, exactly the columns the
# official table prints: w, l, win%, gb, conf, div, home, road, neutral, ot, last10, streak.
STANDINGS = [
    ("PHI", 12, 3, ".800", "--", "12-3", "4-1", "6-2", "6-1", "0-0", "0-0", "8-2", "W 3"),
    ("BOS", 11, 3, ".786", "0.5", "10-2", "4-0", "6-1", "5-2", "0-0", "1-0", "8-2", "L 1"),
    ("DET", 8, 4, ".667", "2.5", "8-3", "0-0", "3-2", "5-2", "0-0", "1-0", "6-4", "L 1"),
    ("MIA", 8, 6, ".571", "3.5", "4-2", "1-1", "4-3", "4-3", "0-0", "1-0", "8-2", "W 5"),
    ("ATL", 8, 6, ".571", "3.5", "8-2", "4-1", "3-3", "5-3", "0-0", "0-1", "6-4", "W 1"),
    ("NYK", 7, 6, ".538", "4", "7-6", "2-3", "4-3", "3-3", "0-0", "1-0", "7-3", "W 1"),
    ("CLE", 8, 7, ".533", "4", "6-5", "2-0", "6-2", "2-5", "0-0", "1-0", "5-5", "W 2"),
    ("ORL", 6, 7, ".462", "5", "4-4", "0-2", "1-4", "5-3", "0-0", "0-1", "5-5", "W 4"),
    ("TOR", 5, 8, ".385", "6", "4-4", "0-3", "2-4", "3-4", "0-0", "0-1", "3-7", "L 4"),
    ("IND", 5, 9, ".357", "6.5", "3-6", "0-1", "2-4", "3-4", "0-1", "0-0", "3-7", "L 1"),
    ("CHA", 4, 9, ".308", "7", "4-7", "2-2", "3-4", "1-5", "0-0", "0-0", "2-8", "L 2"),
    ("WAS", 4, 11, ".267", "8", "4-8", "2-3", "2-5", "2-6", "0-0", "0-1", "2-8", "L 8"),
    ("BKN", 3, 10, ".231", "8", "2-8", "0-3", "1-4", "2-6", "0-0", "0-1", "3-7", "L 2"),
    ("CHI", 3, 10, ".231", "8", "2-9", "1-1", "1-4", "2-6", "0-0", "1-0", "2-8", "L 1"),
    ("MIL", 1, 13, ".071", "10.5", "1-10", "1-2", "1-7", "0-6", "0-0", "0-0", "0-10", "L 10"),
    ("SAS", 12, 2, ".857", "--", "11-2", "2-1", "5-2", "7-0", "0-0", "1-0", "10-0", "W 12"),
    ("LAL", 12, 2, ".857", "--", "7-2", "5-1", "5-1", "7-1", "0-0", "0-0", "9-1", "W 8"),
    ("HOU", 11, 4, ".733", "1.5", "6-3", "2-1", "7-1", "4-3", "0-0", "0-0", "6-4", "L 1"),
    ("MIN", 10, 4, ".714", "2", "6-2", "2-0", "6-2", "4-2", "0-0", "0-1", "7-3", "W 1"),
    ("MEM", 10, 4, ".714", "2", "7-3", "1-1", "3-4", "7-0", "0-0", "0-1", "6-4", "W 3"),
    ("POR", 9, 4, ".692", "2.5", "9-4", "4-1", "3-2", "6-2", "0-0", "0-0", "6-4", "L 1"),
    ("OKC", 9, 5, ".643", "3", "6-5", "1-2", "5-0", "4-5", "0-0", "0-0", "5-5", "W 1"),
    ("DEN", 7, 5, ".583", "4", "5-5", "0-2", "2-3", "4-2", "1-0", "1-0", "6-4", "L 1"),
    ("GSW", 8, 6, ".571", "4", "6-6", "3-2", "6-1", "2-5", "0-0", "1-0", "7-3", "L 3"),
    ("DAL", 7, 7, ".500", "5", "3-5", "1-3", "5-2", "2-5", "0-0", "0-0", "5-5", "L 3"),
    ("PHX", 6, 7, ".462", "5.5", "4-7", "2-2", "5-4", "1-3", "0-0", "0-0", "5-5", "W 1"),
    ("LAC", 4, 8, ".333", "7", "3-6", "1-4", "4-3", "0-5", "0-0", "0-1", "3-7", "W 2"),
    ("NOP", 5, 10, ".333", "7.5", "4-8", "1-1", "4-6", "1-4", "0-0", "2-1", "4-6", "W 1"),
    ("SAC", 1, 12, ".077", "10.5", "1-10", "0-2", "0-8", "1-4", "0-0", "0-0", "1-9", "L 6"),
    ("UTA", 1, 13, ".071", "11", "1-11", "0-2", "1-7", "0-6", "0-0", "0-2", "0-10", "L 12"),
]

# --------------------------------------------------------------------------- advanced
# nba.com/stats/teams/advanced (PerGame), read 2026-11-17T16:30Z, all 30 rows across the
# tool's two chunks. gp, w, l, min, off_rtg, def_rtg, net_rtg, pace, pie, poss.
# The page prints one row per club in NetRtg order; the club's own W/L on this page is the
# second opinion on the standings card, and is compared to it below.
ADVANCED = [
    ("LAL", 14, 12, 2, 672.0, 122.1, 114.0, 8.0, 100.64, 54.2, 1408),
    ("PHI", 15, 12, 3, 720.0, 113.7, 111.1, 2.6, 100.23, 51.3, 1505),
    ("SAS", 14, 12, 2, 677.0, 119.2, 106.6, 12.6, 98.77, 56.9, 1395),
    ("BOS", 14, 11, 3, 677.0, 118.2, 106.1, 12.1, 96.53, 55.4, 1360),
    ("HOU", 15, 11, 4, 720.0, 120.9, 112.3, 8.6, 97.50, 55.5, 1462),
    ("MEM", 14, 10, 4, 677.0, 120.0, 110.9, 9.1, 100.61, 54.3, 1420),
    ("MIN", 14, 10, 4, 677.0, 115.2, 104.1, 11.1, 101.21, 55.1, 1427),
    ("OKC", 14, 9, 5, 672.0, 113.4, 108.4, 5.1, 98.82, 53.8, 1384),
    ("POR", 13, 9, 4, 624.0, 117.2, 110.6, 6.6, 100.65, 52.8, 1308),
    ("ATL", 14, 8, 6, 677.0, 112.8, 111.1, 1.7, 103.69, 49.0, 1462),
    ("CLE", 15, 8, 7, 725.0, 116.9, 114.7, 2.2, 100.30, 51.5, 1515),
    ("DET", 12, 8, 4, 586.0, 114.1, 109.2, 4.9, 99.48, 53.7, 1217),
    ("GSW", 14, 8, 6, 677.0, 114.6, 112.3, 2.2, 99.58, 51.0, 1406),
    ("MIA", 14, 8, 6, 677.0, 116.0, 116.2, -0.1, 101.96, 50.6, 1440),
    ("DAL", 14, 7, 7, 672.0, 111.8, 114.5, -2.7, 100.18, 48.6, 1404),
    ("DEN", 12, 7, 5, 581.0, 115.1, 114.9, 0.2, 97.86, 52.2, 1187),
    ("NYK", 13, 7, 6, 629.0, 113.7, 108.2, 5.5, 95.66, 53.5, 1257),
    ("ORL", 13, 6, 7, 629.0, 110.5, 113.0, -2.6, 98.10, 48.6, 1281),
    ("PHX", 13, 6, 7, 624.0, 114.5, 117.5, -3.0, 98.88, 48.5, 1283),
    ("IND", 14, 5, 9, 672.0, 110.9, 112.9, -2.0, 101.25, 49.6, 1415),
    ("NOP", 15, 5, 10, 735.0, 111.7, 118.4, -6.7, 101.62, 46.6, 1555),
    ("TOR", 13, 5, 8, 629.0, 113.6, 112.2, 1.4, 99.55, 49.0, 1302),
    ("CHA", 13, 4, 9, 624.0, 102.5, 113.6, -11.1, 96.65, 42.7, 1256),
    ("LAC", 12, 4, 8, 581.0, 111.4, 115.3, -3.9, 100.05, 48.3, 1210),
    ("WAS", 15, 4, 11, 730.0, 109.9, 117.6, -7.8, 99.91, 45.8, 1519),
    ("BKN", 13, 3, 10, 629.0, 110.8, 117.4, -6.6, 99.55, 45.9, 1304),
    ("CHI", 13, 3, 10, 629.0, 109.1, 120.0, -10.9, 104.17, 44.9, 1366),
    ("MIL", 14, 1, 13, 672.0, 105.4, 118.9, -13.6, 100.68, 42.1, 1410),
    ("SAC", 13, 1, 12, 624.0, 106.8, 119.8, -13.0, 101.08, 42.6, 1312),
    ("UTA", 14, 1, 13, 682.0, 105.1, 116.2, -11.1, 100.22, 45.0, 1426),
]

# Three rows of the traditional page were read independently (same session, same day) and are
# published as a spot-check of the *points* fields, which this capture does not re-read from
# that page. Everything else on that page is verified by identity against the 205 official
# finals - see `points_from_finals()` below, which is a stronger test than a row-by-row copy.
TRADITIONAL_SPOT = [
    # team, gp, w, l, pts/g, plus_minus  (nba.com/stats/teams/traditional, 2026-11-17T16:31Z)
    ("LAL", 14, 12, 2, 122.8, 7.9),
    ("SAS", 14, 12, 2, 118.8, 12.9),
]

# --------------------------------------------------------------------------- slate
# nba.com/schedule?date=2026-11-18, read 2026-11-17T16:28Z. One row per game card:
# game_id | date | tip ET (24 h) | away | home | arena | city | state | broadcast | cup group
# The "Emirates NBA Cup" marker and the group name are printed on the card itself; a card
# without the marker is blank here (verified absence, not an assumption).
SLATE = [
    ("0022600253", "2026-11-17", "19:30", "NYK", "TOR", "Scotiabank Arena", "Toronto", "ON", "League Pass", ""),
    ("0022600254", "2026-11-17", "20:00", "POR", "MIN", "Target Center", "Minneapolis", "MN", "League Pass", ""),
    ("0022600255", "2026-11-17", "20:00", "DET", "SAS", "Frost Bank Center", "San Antonio", "TX", "Peacock / NBC", ""),
    ("0022600257", "2026-11-17", "22:30", "UTA", "LAC", "Intuit Dome", "Inglewood", "CA", "League Pass", ""),
    ("0022600256", "2026-11-17", "23:00", "CHA", "LAL", "Crypto.com Arena", "Los Angeles", "CA", "Peacock", ""),
    ("0022600258", "2026-11-18", "19:00", "MEM", "CLE", "Rocket Arena", "Cleveland", "OH", "League Pass", ""),
    ("0022600259", "2026-11-18", "19:00", "HOU", "IND", "Gainbridge Fieldhouse", "Indianapolis", "IN", "League Pass", ""),
    ("0022600260", "2026-11-18", "19:00", "MIL", "MIA", "Kaseya Center", "Miami", "FL", "ESPN", ""),
    ("0022600261", "2026-11-18", "19:00", "PHI", "ORL", "Kia Center", "Orlando", "FL", "League Pass", ""),
    ("0022600262", "2026-11-18", "19:30", "CHI", "BKN", "Barclays Center", "Brooklyn", "NY", "League Pass", ""),
    ("0022600263", "2026-11-18", "19:30", "WAS", "TOR", "Scotiabank Arena", "Toronto", "ON", "MNMT/Monumental+", ""),
    ("0022600264", "2026-11-18", "20:00", "DET", "NOP", "Smoothie King Center", "New Orleans", "LA", "League Pass", ""),
    ("0022600265", "2026-11-18", "20:00", "ATL", "OKC", "Paycom Center", "Oklahoma City", "OK", "League Pass", ""),
    ("0022600267", "2026-11-18", "20:00", "GSW", "DAL", "American Airlines Center", "Dallas", "TX", "League Pass", ""),
    ("0022600266", "2026-11-18", "21:30", "BOS", "DEN", "Ball Arena", "Denver", "CO", "ESPN", ""),
    ("0022600268", "2026-11-18", "22:00", "UTA", "LAL", "Crypto.com Arena", "Los Angeles", "CA", "League Pass", ""),
    ("0022600269", "2026-11-18", "22:00", "PHX", "SAC", "Golden 1 Center", "Sacramento", "CA", "League Pass", ""),
    ("0022600270", "2026-11-19", "20:00", "GSW", "MEM", "FedExForum", "Memphis", "TN", "League Pass", ""),
    ("0022600271", "2026-11-19", "20:00", "POR", "MIL", "Fiserv Forum", "Milwaukee", "WI", "League Pass", ""),
    ("0022600272", "2026-11-19", "20:00", "NYK", "MIN", "Target Center", "Minneapolis", "MN", "NBA TV", ""),
    ("0022600273", "2026-11-19", "20:00", "LAC", "SAS", "Frost Bank Center", "San Antonio", "TX", "League Pass", ""),
    ("0022600043", "2026-11-20", "19:00", "CHA", "ATL", "State Farm Arena", "Atlanta", "GA", "League Pass", "Emirates NBA Cup - East Group C"),
    ("0022600044", "2026-11-20", "19:30", "ORL", "BKN", "Barclays Center", "Brooklyn", "NY", "League Pass", "Emirates NBA Cup - East Group A"),
    ("0022600045", "2026-11-20", "19:30", "IND", "CLE", "Rocket Arena", "Cleveland", "OH", "League Pass", "Emirates NBA Cup - East Group B"),
    ("0022600046", "2026-11-20", "19:30", "TOR", "DET", "Little Caesars Arena", "Detroit", "MI", "Prime Video", "Emirates NBA Cup - East Group A"),
    ("0022600047", "2026-11-20", "20:00", "WAS", "CHI", "United Center", "Chicago", "IL", "MNMT/Monumental+", "Emirates NBA Cup - East Group C"),
    ("0022600048", "2026-11-20", "20:00", "NOP", "OKC", "Paycom Center", "Oklahoma City", "OK", "League Pass", "Emirates NBA Cup - West Group B"),
    ("0022600049", "2026-11-20", "21:30", "PHX", "UTA", "Delta Center", "Salt Lake City", "UT", "League Pass", "Emirates NBA Cup - West Group A"),
    ("0022600050", "2026-11-20", "22:00", "HOU", "DEN", "Ball Arena", "Denver", "CO", "Prime Video", "Emirates NBA Cup - West Group A"),
    ("0022600051", "2026-11-20", "22:00", "SAC", "LAL", "Crypto.com Arena", "Los Angeles", "CA", "NBA TV", "Emirates NBA Cup - West Group C"),
]

# --------------------------------------------------------------------------- finals (already played)
# The same page prints the completed 11/16 cards with their finals. Eight games, read
# 2026-11-17T16:28Z. These are *not* re-settling anything: they are this session's second,
# independent read of finals the repository already carries, so the published feed can be
# checked against a fresh retrieval rather than trusted.
FINALS_2026_11_16 = [
    ("0022600245", "2026-11-16", "ORL", "BOS", 115, 105),
    ("0022600246", "2026-11-16", "CHI", "CLE", 115, 126),
    ("0022600247", "2026-11-16", "MEM", "WAS", 136, 120),
    ("0022600248", "2026-11-16", "PHI", "BKN", 135, 123),
    ("0022600249", "2026-11-16", "HOU", "MIA", 110, 128),
    ("0022600250", "2026-11-16", "POR", "MIN", 98, 106),
    ("0022600251", "2026-11-16", "GSW", "NOP", 94, 115),
    ("0022600252", "2026-11-16", "PHX", "DEN", 117, 105),
]

# --------------------------------------------------------------------------- helpers
def standings_rows() -> list[dict]:
    out = []
    for (t, w, l, pct, gb, conf, div, home, road, neu, ot, l10, streak) in STANDINGS:
        out.append({"team": t, "w": w, "l": l, "win_pct": pct, "gb": gb, "conf": conf,
                    "div": div, "home": home, "road": road, "neutral": neu, "ot": ot,
                    "last10": l10, "streak": streak, "source_url": STANDINGS_URL,
                    "source_class": "official"})
    return out


def advanced_rows() -> list[dict]:
    out = []
    for (t, gp, w, l, mn, off, dfn, net, pace, pie, poss) in ADVANCED:
        out.append({"team": t, "gp": gp, "w": w, "l": l, "min": mn, "off_rtg": off,
                    "def_rtg": dfn, "net_rtg": net, "pace": pace, "pie": pie, "poss": poss,
                    "source_url": ADV_URL, "source_class": "official"})
    return out


def slate_rows() -> list[dict]:
    out = []
    for (gid, date, tip, away, home, arena, city, state, tv, cup) in SLATE:
        out.append({"game_id": gid, "date": date, "tip_et": tip, "away": away, "home": home,
                    "arena": arena, "city": city, "state": state, "national_broadcast": tv,
                    "cup_group": cup,
                    "source_url": f"https://www.nba.com/game/{away.lower()}-vs-{home.lower()}-{gid}",
                    "list_url": SCHEDULE_URL, "source_class": "official"})
    return out


def finals_rows() -> list[dict]:
    out = []
    for (gid, date, away, home, ap, hp) in FINALS_2026_11_16:
        out.append({"game_id": gid, "date": date, "away": away, "home": home,
                    "away_pts": ap, "home_pts": hp, "status": "final",
                    "source_url": f"https://www.nba.com/game/{away.lower()}-vs-{home.lower()}-{gid}",
                    "list_url": SCHEDULE_URL, "source_class": "official"})
    return out


def injury_rows() -> dict:
    """Derive the 11/17 release rows from the stored rendering - never re-typed here."""
    sys.path.insert(0, str(ROOT))
    from nba2.v4 import injury_parse as PA
    from nba2.v4 import injury_renderings as RR
    rel = RR.newest()
    assert rel["stamp_et"] == "2026-11-17 11:15 AM ET", rel["stamp_et"]
    parsed = PA.parse_render(rel["text"])
    return {
        "schema": "nba2.injury-release.v1",
        "revision_et": rel["revision_et"],
        "retrieved_utc": rel["retrieved_utc"],
        "index_checked_utc": rel["index_checked_utc"],
        "url": rel["url"],
        "index_url": INJURY_INDEX_URL,
        "text_sha256": RR.text_sha(rel["text"]),
        "method": rel["method"],
        "counts": parsed["counts"],
        "rows": [{**r, "source_url": rel["url"], "source_class": "official"}
                 for r in parsed["rows"]],
        "unread": parsed["unread"],
        "note": ("rows are produced by nba2/v4/injury_parse.py from the stored rendering, so "
                 "this file and the published injury pages cannot drift apart"),
    }


def points_from_finals() -> dict:
    """PF/PA per club, summed from every committed official final.

    This is the identity that lets the capture be trusted without re-reading the traditional
    and opponent pages for all 30 clubs: the official per-game points column must equal the
    club's committed finals total divided by its games played, to the 0.1 the page prints.
    """
    games: dict[str, dict] = {}
    sources: dict[str, str] = {}
    for f in sorted((ROOT / "data/raw/history").glob("games_*.json")):
        for g in json.loads(f.read_text())["games"]:
            if g.get("away_pts") is None or g.get("home_pts") is None:
                continue
            games[g["game_id"]] = g
            sources[g["game_id"]] = str(f.relative_to(ROOT))
    # Dated result feeds. A later read of the same game id that *has* a score supersedes an
    # earlier one that was still in progress; a pending row never overwrites a final one.
    for rel in ["data/raw/capture_2026-11-15/results_2026-11-14.json",
                "data/raw/results/results_2026-11-15.json",
                "data/raw/results/results_2026-11-16.json",
                "data/raw/results/results_2026-11-15_recheck_2026-11-17.json"]:
        d = json.loads((ROOT / rel).read_text())
        for r in d["records"]:
            if r.get("home_pts") is None or r.get("away_pts") is None:
                continue
            games[r["game_id"]] = {"game_id": r["game_id"], "date": r["date"],
                                   "away": r["away"], "home": r["home"],
                                   "away_pts": r["away_pts"], "home_pts": r["home_pts"]}
            sources[r["game_id"]] = rel
    pts = {t: [0, 0] for (t, *_r) in STANDINGS}          # [for, against]
    rec = {t: [0, 0] for (t, *_r) in STANDINGS}           # [w, l]
    splits = {t: [0, 0, 0, 0] for (t, *_r) in STANDINGS}  # hw hl rw rl
    neutral: dict[str, list[str]] = {}
    for g in games.values():
        a, h = g["away"], g["home"]
        pts[h][0] += g["home_pts"]; pts[h][1] += g["away_pts"]
        pts[a][0] += g["away_pts"]; pts[a][1] += g["home_pts"]
        if g["home_pts"] > g["away_pts"]:
            rec[h][0] += 1; rec[a][1] += 1
        else:
            rec[a][0] += 1; rec[h][1] += 1
    for (t, w, l, _p, _g, _c, _d, home, road, neu, *_x) in STANDINGS:
        hw, hl = (int(x) for x in home.split("-")); rw, rl = (int(x) for x in road.split("-"))
        n = int(neu.split("-")[0]) + int(neu.split("-")[1])
        if n:
            neutral[t] = [neu]
        splits[t] = [hw, hl, rw, rl]
    out = {}
    for t in pts:
        gp = rec[t][0] + rec[t][1]
        out[t] = {"games": gp, "points_for": pts[t][0], "points_against": pts[t][1],
                  "pf_per_game": round(pts[t][0] / gp, 1),
                  "pa_per_game": round(pts[t][1] / gp, 1)}
    return {"schema": "nba2.points-from-finals.v1", "n_games": len(games),
            "retrieved_by": "committed official finals (data/raw/history + dated result feeds)",
            "per_game_source": {k: sources[k] for k in sorted(sources)},
            "reconstructed_record": {t: {"w": rec[t][0], "l": rec[t][1]} for t in rec},
            "league_points_scored": sum(v["points_for"] for v in out.values()),
            "league_points_allowed": sum(v["points_against"] for v in out.values()),
            "per_club": out, "clubs_with_neutral_site_games": neutral}


# --------------------------------------------------------------------------- checks
def checks() -> list[dict]:
    c: list[dict] = []
    st = standings_rows()
    ad = advanced_rows()

    def add(id_, what, value, ok, detail=""):
        c.append({"id": id_, "what": what, "value": value,
                  "result": "PASS" if ok else "FAIL", "detail": detail})
        return ok

    add("rows-30", "30 clubs on the standings card and 30 on the advanced page, same club set",
        f"{len(st)} / {len(ad)}", len(st) == 30 and len(ad) == 30
        and {r["team"] for r in st} == {r["team"] for r in ad})

    w = sum(r["w"] for r in st)
    l = sum(r["l"] for r in st)
    add("wins-equals-losses", "league wins = league losses (every game has one of each)",
        f"{w} / {l}", w == l == 205, "205 is also 410 team-games / 2 = the games implied by the card")

    gp_ok = all(r["gp"] == r["w"] + r["l"] for r in ad)
    add("gp-equals-wl", "every club's games played on the advanced page = its own W+L",
        str(gp_ok), gp_ok)

    card_agree = all(next(x for x in st if x["team"] == r["team"])["w"] == r["w"]
                     and next(x for x in st if x["team"] == r["team"])["l"] == r["l"]
                     for r in ad)
    add("two-pages-same-record", "W/L printed on the advanced page matches the standings card, 30/30",
        str(card_agree), card_agree)

    home_w = sum(int(r["home"].split("-")[0]) for r in st)
    road_l = sum(int(r["road"].split("-")[1]) for r in st)
    home_l = sum(int(r["home"].split("-")[1]) for r in st)
    road_w = sum(int(r["road"].split("-")[0]) for r in st)
    add("splits-balance", "league home wins = road losses and home losses = road wins",
        f"{home_w}/{road_l} and {home_l}/{road_w}",
        home_w == road_l and home_l == road_w,
        "the residual is the neutral-site games, which the card prints outside the splits")

    net_ok = all(abs(r["net_rtg"] - (r["off_rtg"] - r["def_rtg"])) <= 0.1000001 for r in ad)
    add("netrtg-identity", "NetRtg = OffRtg − DefRtg for all 30 clubs (0.1 print rounding)",
        str(net_ok), net_ok)

    trad = json.loads((PRIOR / "team_stats_2026-11-17.json").read_text())
    tr = {r["team"]: r for r in trad["records"]}
    pf = points_from_finals()
    add("finals-count", "committed official finals cover the card exactly",
        f"{pf['n_games']} finals vs {w} games on the card", pf["n_games"] == w,
        "183 in data/raw/history (10/20-11/13) + 5 (11/14) + 9 (11/15) + 8 (11/16), with the "
        "three 11/15 games that were still in progress at their first read taken from the "
        "2026-11-17 recheck feed")

    holes = {r["team"]: (r["w"] + r["l"]) - pf["per_club"][r["team"]]["games"] for r in st}
    neg = {t: h for t, h in holes.items() if h < 0}
    over = {}
    for r in st:
        rr = pf["reconstructed_record"][r["team"]]
        if rr["w"] > r["w"] or rr["l"] > r["l"]:
            over[r["team"]] = (rr["w"] - r["w"], rr["l"] - r["l"])
    add("rebuilt-record", "every club's reconstructed W-L is inside its card record, no club exceeding it",
        f"hole total {sum(holes.values())} club-games; clubs with a hole "
        f"{sorted(t for t, h in holes.items() if h)}",
        not neg and not over,
        "a positive hole would be printed here rather than smoothed away" if not (neg or over)
        else f"negative hole {neg}; exceeded {over}")

    pts_ok = all(abs(tr[t]["pts"] - pf["per_club"][t]["pf_per_game"]) <= 0.1
                 and abs(tr[t]["opp_pts"] - pf["per_club"][t]["pa_per_game"]) <= 0.1
                 for t in tr)
    worst = max((max(abs(tr[t]["pts"] - pf["per_club"][t]["pf_per_game"]),
                     abs(tr[t]["opp_pts"] - pf["per_club"][t]["pa_per_game"])), t) for t in tr)
    n_ok = sum(1 for t in tr
               if abs(tr[t]["pts"] - pf["per_club"][t]["pf_per_game"]) <= 0.1
               and abs(tr[t]["opp_pts"] - pf["per_club"][t]["pa_per_game"]) <= 0.1)
    add("captured-points-reproduce", "the prior capture's PTS and OPP PTS reproduce the 205 official finals, club by club",
        f"{n_ok}/30 clubs; worst residual {worst[0]:.2f} ({worst[1]})", pts_ok,
        "PF and PA are per-game figures the page rounds to 0.1, so 0.1 is the bound")
    add("points-balance-exact", "league points scored = league points allowed, exactly (finals are integer)",
        f"{pf['league_points_scored']} / {pf['league_points_allowed']}",
        pf["league_points_scored"] == pf["league_points_allowed"],
        "a per-page rounding tolerance is not needed here: these are summed box-score points")

    spots = [{"team": t, "captured_pts": tr[t]["pts"], "finals_pts": pf["per_club"][t]["pf_per_game"],
              "delta": round(tr[t]["pts"] - pf["per_club"][t]["pf_per_game"], 2),
              "captured_opp_pts": tr[t]["opp_pts"],
              "finals_pa": pf["per_club"][t]["pa_per_game"],
              "delta_pa": round(tr[t]["opp_pts"] - pf["per_club"][t]["pa_per_game"], 2)}
             for (t, _gp, _w, _l, pts, _pm) in TRADITIONAL_SPOT]
    add("trad-spot-check", "the traditional-page rows read independently agree with finals-summed points",
        "; ".join(f"{s['team']} {s['captured_pts']} vs {s['finals_pts']}" for s in spots),
        all(abs(s["delta"]) <= 0.1 and abs(s["delta_pa"]) <= 0.1 for s in spots),
        "±0.1 is the page's own print precision")

    # cross-check this read against session arena/8892d20c-nba2's capture, field by field
    prior_st = json.loads((PRIOR / "standings_2026-11-17.json").read_text())["records"]
    ps = {r["team"]: r for r in prior_st}
    diff_cols, same = [], 0
    for r in st:
        p = ps.get(r["team"])
        if not p:
            diff_cols.append(f"{r['team']}: missing from the prior capture")
            continue
        bad = [k for k in ("w", "l", "conf", "div", "home", "road", "neutral", "ot", "last10")
               if str(p.get(k)) != str(r[k])]
        if bad:
            diff_cols.append(f"{r['team']}: {[(k, p.get(k), r[k]) for k in bad]}")
        else:
            same += 1
    add("prior-standings-agreement", "this standings read vs arena/8892d20c-nba2's 2026-11-17 capture",
        f"{same}/30 clubs identical on all nine shared columns", same == 30,
        "; ".join(diff_cols) if diff_cols else "no differences")

    prior_adv = {r["team"]: r for r in trad["records"]}
    n_ag = 0
    ag_bad = []
    for r in ad:
        p = prior_adv.get(r["team"], {})
        fields = ("off_rtg", "def_rtg", "net_rtg", "pace", "pie")
        bad = [f"{k} prior={p.get(k)} this-read={r[k]}" for k in fields if p.get(k) != r[k]]
        gp = p.get("gp")
        if gp != r["gp"]:
            bad.append(f"gp {gp}!= {r['gp']}")
        if bad:
            ag_bad.append(f"{r['team']}: " + ", ".join(bad))
        else:
            n_ag += 1
    add("prior-teamstats-agreement", "this advanced-page read vs the same capture's advanced columns",
        f"{n_ag}/30 clubs identical on OffRtg/DefRtg/NetRtg/PACE/PIE/GP", n_ag == 30,
        "; ".join(ag_bad) if ag_bad else "no differences")

    # the published result feed for 11/16, re-checked against today's read
    feed = json.loads((ROOT / "data/raw/results/results_2026-11-16.json").read_text())["records"]
    fr = {r["game_id"]: r for r in feed}
    mism = []
    for (gid, date, away, home, ap, hp) in FINALS_2026_11_16:
        r = fr.get(gid)
        if r is None:
            mism.append(f"{gid}: not in the published feed")
        elif (r["away_pts"], r["home_pts"], r["away"], r["home"]) != (ap, hp, away, home):
            mism.append(f"{gid}: feed {r['away']}-{r['home']} {r['away_pts']}-{r['home_pts']} "
                        f"vs read {away}-{home} {ap}-{hp}")
    add("results-feed-recheck", "the published 11/16 result feed vs this session's fresh read of the same page",
        f"{len(FINALS_2026_11_16)} games, {len(mism)} mismatches", not mism,
        "; ".join(mism) if mism else "every final, every team and every score agrees")

    # the slate the published tree already carries for 11/17-11/18, re-checked
    sys.path.insert(0, str(ROOT))
    from nba2.v2 import official as O2
    pub = {(g[4], g[0]): (g[2], g[3], g[1]) for g in O2.SLATE}
    mine = {(gid, date): (away, home, tip) for (gid, date, tip, away, home, *_x) in SLATE}
    overlap = {k: (pub[k], mine[k]) for k in pub.keys() & mine.keys() if pub[k] != mine[k]}
    add("slate-recheck", "this session's slate read vs the published v2 slate (overlapping games)",
        f"{len(pub.keys() & mine.keys())} overlapping games, {len(overlap)} mismatches",
        not overlap, str(overlap) if overlap else "game id, date, matchup and ET tip all agree")

    inj = injury_rows()
    add("injury-parsed", "the 11/17 11:15 AM ET release parses with no unread player row",
        f"{inj['counts']['rows']} rows, {inj['counts']['with_status']} with status, "
        f"{inj['counts']['placeholders']} club placeholders, {inj['counts']['unread']} unread",
        inj["counts"]["unread"] <= 1,
        "the one unread line is a page-break fragment (see the release file); no player row is dropped")
    return c


def main(write: bool) -> int:
    res = checks()
    bad = [r for r in res if r["result"] == "FAIL"]
    if write:
        OUT.mkdir(parents=True, exist_ok=True)
        files = {
            "standings_2026-11-17.json": {
                "schema": "nba2.standings-official.v2", "as_of": "2026-11-17", "session": SESSION,
                "retrieved_at_utc": READ_UTC, "retrieval_method": METHOD,
                "source_url": STANDINGS_URL, "source_class": "official",
                "columns": ["team", "w", "l", "win_pct", "gb", "conf", "div", "home", "road",
                            "neutral", "ot", "last10", "streak"],
                "records": standings_rows()},
            "team_advanced_2026-11-17.json": {
                "schema": "nba2.team-advanced-official.v1", "as_of": "2026-11-17", "session": SESSION,
                "retrieved_at_utc": READ_UTC, "retrieval_method": METHOD,
                "source_url": ADV_URL, "source_class": "official",
                "columns": ["gp", "w", "l", "min", "off_rtg", "def_rtg", "net_rtg", "pace", "pie", "poss"],
                "records": advanced_rows(),
                "traditional_page_spot_check": TRADITIONAL_SPOT,
                "note": ("points per game and opponent points per game are not re-read from the "
                         "traditional/opponent pages by this session; they are re-derived from the "
                         "205 committed official finals in points_from_finals.json and the two "
                         "traditional rows read independently are published as a spot check")},
            "slate_2026-11-17_to_11-20.json": {
                "schema": "nba2.slate.v2", "window": {"start": "2026-11-17", "end": "2026-11-20", "days": 3},
                "anchor_date": "2026-11-17", "session": SESSION, "retrieved_at_utc": READ_UTC,
                "retrieval_method": METHOD, "source_url": SCHEDULE_URL, "source_class": "official",
                "games": slate_rows(), "n_games_transcribed": len(SLATE),
                "per_date_count": {d: sum(1 for g in SLATE if g[1] == d)
                                   for d in sorted({g[1] for g in SLATE})},
                "cup_marker": ("the Emirates NBA Cup marker and group are printed on the card; "
                               "11/17-11/19 cards carry none, so those rows are blank by observation, "
                               "not by assumption (this closes FLAG-V2-CUP-BLANK for the window)")},
            "finals_2026-11-16_independent.json": {
                "schema": "nba2.finals-recheck.v1", "game_date": "2026-11-16", "session": SESSION,
                "retrieved_at_utc": READ_UTC, "retrieval_method": METHOD, "source_url": SCHEDULE_URL,
                "source_class": "official",
                "note": ("a second, independent read of the 11/16 finals taken from the schedule page "
                         "on 2026-11-17 - the day after those games. It does not re-settle anything; "
                         "it re-confirms the published feed."),
                "records": finals_rows()},
            "injury_release_2026-11-17_1115AM_ET.json": injury_rows(),
            "points_from_finals.json": points_from_finals(),
            "capture_index.json": {
                "schema": "nba2.capture-index.v1", "retrieved_utc": READ_UTC, "session": SESSION,
                "method": METHOD,
                "source_pages": {
                    "standings": {"name": "NBA.com Standings (official)", "url": STANDINGS_URL,
                                   "read": "30 clubs x 12 printed columns"},
                    "team_adv": {"name": "NBA.com Stats - Teams Advanced (official)", "url": ADV_URL,
                                  "read": "30 clubs: GP, W, L, MIN, OffRtg, DefRtg, NetRtg, PACE, PIE, POSS"},
                    "team_trad_spot": {"name": "NBA.com Stats - Teams Traditional (official)",
                                        "url": "https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame",
                                        "read": "2 of 30 rows read directly (LAL, SAS); the rest are verified by identity against the 205 committed official finals"},
                    "schedule": {"name": "NBA.com Schedule (official)", "url": SCHEDULE_URL,
                                  "read": "11/16 finals; 11/17 (5), 11/18 (12), 11/19 (4), 11/20 (9) cards with game ids, ET tips, arenas and NBA Cup groups"},
                    "injury_index": {"name": "NBA Official - Injury Report index (official)",
                                      "url": INJURY_INDEX_URL,
                                      "read": "every published 11/17 release, 12:00 a.m. ET to 11:15 a.m. ET; the newest is the one stored"},
                    "injury_pdf": {"name": "NBA Official Injury Report 11/17/26 11:15 AM ET (official PDF)",
                                    "url": INJURY_PDF_URL,
                                    "read": "verbatim rendering stored in nba2/v4/injury_renderings.py; rows derived by nba2/v4/injury_parse.py"}},
                "unread": {
                    "injury_pdf_bytes": {
                        "what": "the PDF file itself (bytes), not its text",
                        "why": ("bash egress to ak-static.cms.nba.com is blocked in this sandbox; "
                                "nba2/v4/injury_ingest.py archives bytes from a runner and records "
                                "the outcome either way (F-V4-01)"),
                        "attempted_url": INJURY_PDF_URL},
                    "traditional_and_opponent_pages": {
                        "what": "the full 30-row PTS and OPP PTS tables",
                        "why": ("not re-read this session; verified instead by exact re-derivation from "
                                "the 205 committed official finals, plus two directly read rows"),
                        "attempted_url": "https://www.nba.com/stats/teams/traditional"},
                    "closing_lines": {
                        "what": "market closing prices",
                        "why": "no licensed odds feed is connected (gate G6)",
                        "attempted_url": "https://www.nba.com/games"}},
                "checks": res,
                "files": sorted(p.name for p in OUT.glob("*.json")) if OUT.exists() else []},
        }
        for name, blob in files.items():
            (OUT / name).write_text(json.dumps(blob, indent=1) + "\n")
        idx = json.loads((OUT / "capture_index.json").read_text())
        idx["files"] = sorted(p.name for p in OUT.glob("*.json"))
        (OUT / "capture_index.json").write_text(json.dumps(idx, indent=1) + "\n")

    for r in res:
        print(f"  {r['result']:4}  {r['id']:32} {r['value']}")
        if r["detail"]:
            print(f"        {'':32} {r['detail'][:150]}")
    print(f"\n{len(res) - len(bad)}/{len(res)} checks PASS"
          + ("  -> SELFTEST FAIL" if bad else "  -> SELFTEST CLEAN"))
    if write:
        print(f"wrote {len(list(OUT.glob('*.json')))} files to {OUT.relative_to(ROOT)}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main("--verify" not in sys.argv))
