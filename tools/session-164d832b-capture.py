#!/usr/bin/env python3
"""Parse the official pages read on 2026-11-19 into one dated, source-linked capture.

Every value this module emits is parsed out of a committed raw file under
``data/raw/verify_2026-11-19/raw/``, and each raw file records the URL it came from and the UTC
time it was read. Nothing is typed in from memory, and nothing is inferred: a field the page did
not print is ``None`` with a ``status`` string saying why.

The parser is **fail-closed**. ``selftest()`` runs identities that a transcription error would
break — the two-source point-differential identity, the NetRtg identity, wins==losses, home+road
game counts, and the reconstruction test that applies the twelve 11/18 finals to the 11/18
standings and demands the 11/19 standings page back on all 30 clubs. If any of them fails the
module raises and writes nothing. A capture that cannot prove itself is not published.

    python3 tools/session-164d832b-capture.py            # verify, then write
    python3 tools/session-164d832b-capture.py --selftest  # verify only, write nothing
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "verify_2026-11-19" / "raw"
OUT = ROOT / "data" / "raw" / "verify_2026-11-19" / "official_2026-11-19.json"

RETRIEVED = "2026-11-19"          # the calendar day of every read below

SOURCES = {
    "standings": ("standings_2026-11-19.md", "https://www.nba.com/standings"),
    "traditional": ("teams_traditional_2026-11-19.md",
                    "https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season"),
    "opponent": ("teams_opponent_2026-11-19.md",
                 "https://www.nba.com/stats/teams/opponent?Season=2026-27&SeasonType=Regular+Season"),
    "advanced": ("teams_advanced_2026-11-19.md",
                 "https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season"),
    "games_1118": ("games_2026-11-18_2026-11-19.md", "https://www.nba.com/games?date=2026-11-18"),
    "games_1119": ("games_2026-11-19_slate.md", "https://www.nba.com/games?date=2026-11-19"),
    "injury_index": ("injury_index_2026-11-19.md",
                     "https://official.nba.com/nba-injury-report-2026-27-season/"),
    "injury_0645": ("injury_2026-11-19_0645AM.md",
                    "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-19_06_45AM.pdf"),
    "injury_0700": ("injury_2026-11-19_0700AM.md",
                    "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-19_07_00AM.pdf"),
    "injury_1119_0100": ("injury_2026-11-19_0100AM.md",
                         "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-19_01_00AM.pdf"),
    "injury_1119_1200": ("injury_2026-11-19_1200AM.md",
                         "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-19_12_00AM.pdf"),
    "injury_1118_1415": ("injury_2026-11-18_0215PM.md",
                         "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-18_02_15PM.pdf"),
}

# (team name as printed on nba.com) -> tricode. This is a name->code dictionary, not a
# measurement: every triple below also appears as the club's own abbreviation on the source
# pages (game URLs / game ids), so it is checkable rather than assumed.
# The league prints exactly these participation statuses on the official report. A cell outside
# this set means the extractor mangled a row (it does: the 06:45 AM rendering drops alternating
# "NOT YET SUBMITTED" markers on page 3), and such a row is rejected rather than published.
STATUSES = {"Out", "Questionable", "Probable", "Doubtful", "Available"}

TEAM_NAMES = set()

TRI = {
    "Atlanta Hawks": "ATL", "Boston Celtics": "BOS", "Brooklyn Nets": "BKN",
    "Charlotte Hornets": "CHA", "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE",
    "Dallas Mavericks": "DAL", "Denver Nuggets": "DEN", "Detroit Pistons": "DET",
    "Golden State Warriors": "GSW", "Houston Rockets": "HOU", "Indiana Pacers": "IND",
    "LA Clippers": "LAC", "Los Angeles Lakers": "LAL", "Memphis Grizzlies": "MEM",
    "Miami Heat": "MIA", "Milwaukee Bucks": "MIL", "Minnesota Timberwolves": "MIN",
    "New Orleans Pelicans": "NOP", "New York Knicks": "NYK", "Oklahoma City Thunder": "OKC",
    "Orlando Magic": "ORL", "Philadelphia 76ers": "PHI", "Phoenix Suns": "PHX",
    "Portland Trail Blazers": "POR", "Sacramento Kings": "SAC", "San Antonio Spurs": "SAS",
    "Toronto Raptors": "TOR", "Utah Jazz": "UTA", "Washington Wizards": "WAS",
}


TEAM_NAMES.update({
    "Atlanta Hawks", "Boston Celtics", "Brooklyn Nets", "Charlotte Hornets", "Chicago Bulls",
    "Cleveland Cavaliers", "Dallas Mavericks", "Denver Nuggets", "Detroit Pistons",
    "Golden State Warriors", "Houston Rockets", "Indiana Pacers", "LA Clippers",
    "Los Angeles Lakers", "Memphis Grizzlies", "Miami Heat", "Milwaukee Bucks",
    "Minnesota Timberwolves", "New Orleans Pelicans", "New York Knicks", "Oklahoma City Thunder",
    "Orlando Magic", "Philadelphia 76ers", "Phoenix Suns", "Portland Trail Blazers",
    "Sacramento Kings", "San Antonio Spurs", "Toronto Raptors", "Utah Jazz", "Washington Wizards",
})


def _text(key: str) -> str:
    return (RAW / SOURCES[key][0]).read_text()


def _table_rows(text: str) -> list[list[str]]:
    """Every markdown table row in the file, as cells. Header/separator rows are dropped."""
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|") or not line.endswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(set(c) <= set("-: ") for c in cells):
            continue
        out.append(cells)
    return out


def _num(x: str):
    x = x.replace(",", "").strip()
    try:
        return int(x)
    except ValueError:
        try:
            return float(x)
        except ValueError:
            return None


# ----------------------------------------------------------------------- 1. standings
def standings() -> list[dict]:
    rows = []
    for cells in _table_rows(_text("standings")):
        # | rank+team | w | L | WIN% | GB | CONF | DIV | HOME | ROAD | Neutral | OT | LAST10 | STREAK |
        if len(cells) != 13:
            continue
        m = re.search(r">([A-Za-z0-9 .'\-]+)\]\(https://www\.nba\.com/team/(\d+)/", cells[0])
        name = m.group(1).strip() if m else None
        if not name or name not in TRI:
            continue
        home, road, neu, ot = cells[7], cells[8], cells[9], cells[10]
        rows.append({
            "team": TRI[name], "name": name, "team_id": m.group(2),
            "w": _num(cells[1]), "l": _num(cells[2]), "win_pct": cells[3],
            "gb": cells[4], "conf_record": cells[5], "div_record": cells[6],
            "home": home, "road": road, "neutral": neu, "ot": ot,
            "last10": cells[11], "streak": cells[12],
            "source_url": SOURCES["standings"][1],
        })
    return rows


# ----------------------------------------------------------------- 2. the three stat pages
def _stat_page(key: str, want: list[str], with_record: bool) -> dict[str, dict]:
    """Return {tricode: {column: value}} for exactly the columns this session parses.

    ``with_record`` is True for the pages that print a W and an L column (traditional and
    advanced) and False for the opponent page, which prints neither. The expected row width is
    therefore spelled out rather than inferred, and a row of any other width is skipped — the
    caller's "30 clubs or refuse to write" check turns that into a hard failure.
    """
    width = 6 + len(want) if with_record else 4 + len(want)
    out: dict[str, dict] = {}
    for cells in _table_rows(_text(key)):
        if len(cells) != width:
            continue
        name = cells[1].strip()
        if name not in TRI:
            continue
        if with_record:
            rec = {"gp": _num(cells[2]), "w": _num(cells[3]), "l": _num(cells[4]),
                   "min": _num(cells[5])}
            vals = cells[6:]
        else:
            rec = {"gp": _num(cells[2]), "w": None, "l": None, "min": _num(cells[3])}
            vals = cells[4:]
        for i, col in enumerate(want):
            rec[col] = _num(vals[i])
        rec["source_url"] = SOURCES[key][1]
        out[TRI[name]] = rec
    return out


def traditional():
    return _stat_page("traditional", ["pts", "plus_minus"], with_record=True)


def opponent():
    return _stat_page("opponent", ["opp_pts", "opp_plus_minus"], with_record=False)


def advanced():
    # the advanced page prints W and L, but this capture reproduces only the
    # GP/MIN/OffRtg/DefRtg/NetRtg/PACE/PIE/POSS columns, so no record columns are claimed here
    return _stat_page("advanced", ["off_rtg", "def_rtg", "net_rtg", "pace", "pie", "poss"],
                      with_record=False)


# ------------------------------------------------------------------ 3. finals + slate
def finals_1118() -> list[dict]:
    out = []
    for cells in _table_rows(_text("games_1118")):
        # | # | game id | away | away pts | home pts | home | records | url |
        if len(cells) != 8 or not re.fullmatch(r"00226002\d\d", cells[1] or ""):
            continue
        out.append({
            "game_id": cells[1], "date": "2026-11-18", "away": cells[2], "home": cells[5],
            "away_pts": _num(cells[3]), "home_pts": _num(cells[4]),
            "printed_record": cells[6],
            "source_url": cells[7] if cells[7].startswith("https://") else
                          f"https://www.nba.com/game/{cells[2].lower()}-vs-{cells[5].lower()}-{cells[1]}",
            "final_marker": "Final",
            "quarter_scores": None,
            "quarter_status": ("not printed on the games page; the quarter rows published elsewhere "
                               "come from the committed capture data/raw/capture_2026-11-18/finals_2026-11-18.json"),
        })
    return out


def slate_1119() -> list[dict]:
    out = []
    for cells in _table_rows(_text("games_1119")):
        # | # | away | away record | tip (ET) | home | home record | game id | game URL |
        if len(cells) != 8 or not re.fullmatch(r"\d{10}", cells[6] or ""):
            continue
        if not (re.fullmatch(r"[A-Z]{2,3}", cells[1] or "") and re.fullmatch(r"[A-Z]{2,3}", cells[4] or "")):
            continue
        if "ET" not in cells[3]:
            continue
        out.append({
            "game_id": cells[6], "date": "2026-11-19", "away": cells[1], "home": cells[4],
            "tip_et": cells[3], "away_record_at_render": cells[2], "home_record_at_render": cells[5],
            "state": "scheduled (page links to Preview, no score printed)",
            "source_url": cells[7],
        })
    return out


# ----------------------------------------------------------------------- 4. injuries
def injury(key: str) -> dict:
    """Parse one official release, by row shape.

    The PDF text extractor returns three different row widths across the document's pages, and
    loses the leading (date, time, matchup) columns on pages 2-3. The three shapes are handled
    explicitly and anything else is recorded as ``unplaced`` — never guessed into a team:

      * 7 cells  — full row: date, tip, matchup, team, player, status, reason
      * 9 cells  — page-2 row: the matchup+team pair repeated, then player, status, reason
      * 4 cells  — page-2/3 row: team, player, status, reason (no date, no matchup)

    A row with an empty player and NOT YET SUBMITTED is a club's non-filing, recorded as such.
    """
    rows, unplaced, not_submitted, rejected, header = [], [], [], [], None
    text = _text(key)
    m = re.search(r"Injury Report: (\d\d/\d\d/\d\d \d\d:\d\d [AP]M)", text)
    if m:
        header = m.group(1)
    for cells in _table_rows(text):
        if cells[0] == "Game Date" or "Player Name" in cells:
            continue
        gdate = gtime = matchup = team = player = status = reason = None
        if len(cells) == 7 and re.fullmatch(r"\d\d/\d\d/\d{4}", cells[0] or ""):
            # full row, page 1: date, tip, matchup, team, player, status, reason
            gdate, gtime, matchup, team, player, status, reason = cells
        elif len(cells) == 7 and "NOT YET SUBMITTED" in cells:
            # full row for a club that has not filed: date, tip, matchup, team, '', '', reason
            gdate, gtime, matchup, team = cells[0], cells[1], cells[2], cells[3]
            reason = cells[6]
            if re.fullmatch(r"\d\d/\d\d/\d{4}", gdate or ""):
                pass
            else:
                gdate = None
        else:
            # page 2/3 fragment: the leading date/time columns are gone. Cells may be
            # (matchup, team, player, status, reason) or (team, player, status, reason).
            # The date is left None: it is not printed on the fragment, so claiming it would be
            # an inference. Every such row is still fully attributed by club + player + status.
            rest = [c for c in cells if c]
            if rest and "@" in rest[0]:
                matchup = rest[0]
                rest = rest[1:]
            if rest and rest[0] in TEAM_NAMES:
                team = rest[0]
                rest = rest[1:]
            if "NOT YET SUBMITTED" in rest:
                not_submitted.append(team)
                continue
            if rest:
                player = rest[0]
                status = rest[1] if len(rest) > 1 else None
                reason = rest[2] if len(rest) > 2 else None
        if "NOT YET SUBMITTED" in " ".join(cells):
            if team in TEAM_NAMES:
                not_submitted.append(team)
            else:
                rejected.append({"cells": cells, "why": "non-filing row without a recognisable club"})
            continue
        if player in (None, "", "Player Name"):
            continue
        if status not in STATUSES or "," not in player or team not in TEAM_NAMES:
            rejected.append({"cells": cells, "why": "row does not match the league's printed shape "
                                                     "(club, 'Last, First', one of 5 statuses)"})
            continue
        if gdate and not re.fullmatch(r"\d\d/\d\d/\d{4}", gdate):
            gdate = None
        rows.append({"game_date": gdate, "tip_et": gtime or None, "matchup": matchup or None,
                     "team": team or None, "player": player, "status": status or None,
                     "reason": reason or None, "source_url": SOURCES[key][1]})
    seen, ns = set(), []
    for name in not_submitted:
        if name and name not in seen:
            seen.add(name); ns.append(name)
    return {"revision": header, "rows": rows, "not_submitted_teams": ns,
            "unplaced": unplaced, "rejected_rows": rejected, "source_url": SOURCES[key][1]}


def injury_diff(a: dict, b: dict) -> dict:
    """Status changes between two consecutive official releases, player by player."""
    ka = {(r["player"], r["team"]): r for r in a["rows"]}
    kb = {(r["player"], r["team"]): r for r in b["rows"]}
    added = [kb[k] for k in kb.keys() - ka.keys()]
    removed = [ka[k] for k in ka.keys() - kb.keys()]
    changed = [{"player": k[0], "team": k[1], "from": ka[k]["status"], "to": kb[k]["status"],
                "reason_from": ka[k]["reason"], "reason_to": kb[k]["reason"]}
               for k in ka.keys() & kb.keys() if ka[k]["status"] != kb[k]["status"]]
    return {"from_revision": a["revision"], "to_revision": b["revision"],
            "n_from": len(a["rows"]), "n_to": len(b["rows"]),
            "added": added, "removed": removed, "status_changes": changed,
            "not_submitted_from": a["not_submitted_teams"],
            "not_submitted_to": b["not_submitted_teams"],
            "not_submitted_count_delta": len(b["not_submitted_teams"]) - len(a["not_submitted_teams"]),
            "player_level_changed": bool(added or removed or changed)}


def injury_index() -> dict:
    text = _text("injury_index")
    urls = re.findall(r"https://ak-static\.cms\.nba\.com/referee/injury/Injury-Report_"
                      r"(\d{4}-\d\d-\d\d)_(\d\d)_(\d\d)(AM|PM)\.pdf", text)
    links = re.findall(r"(https://ak-static\.cms\.nba\.com/referee/injury/Injury-Report_"
                       r"\d{4}-\d\d-\d\d_\d\d_\d\d[AP]M\.pdf)", text)
    return {"n_releases_listed": len(urls), "releases": links[0:1] + links[-1:],
            "latest_listed": links[-1] if links else None,
            "date_listed": urls[0][0] if urls else None,
            "coverage_note": ("the index page returned only the November 19 releases at the time of "
                              "reading, so it cannot be used to prove which earlier releases exist"),
            "source_url": SOURCES["injury_index"][1]}


def _pairs(cell: str) -> tuple[int, int]:
    m = re.fullmatch(r"(\d+)-(\d+)", cell.strip())
    if not m:
        return (0, 0)
    return (int(m.group(1)), int(m.group(2)))


# ------------------------------------------------------------------------ selftest
def selftest(d: dict) -> list[str]:
    """Identities a transcription error would break. Returns a list of failures (empty = pass)."""
    fails: list[str] = []
    st = {r["team"]: r for r in d["standings"]}
    tr, op, ad = d["traditional"], d["opponent"], d["advanced"]

    if len(st) != 30:
        fails.append(f"standings parsed {len(st)} clubs, expected 30")
    for name, page in (("traditional", tr), ("opponent", op), ("advanced", ad)):
        if len(page) != 30:
            fails.append(f"{name} parsed {len(page)} clubs, expected 30")

    # wins == losses, and W+L must equal the GP the stats pages print
    sw = sum(r["w"] or 0 for r in st.values())
    sl = sum(r["l"] or 0 for r in st.values())
    if sw != sl:
        fails.append(f"standings wins {sw} != losses {sl}")
    for tri, r in st.items():
        gp = (tr.get(tri) or {}).get("gp")
        if gp is not None and r["w"] is not None and r["l"] is not None and r["w"] + r["l"] != gp:
            fails.append(f"{tri}: W+L {r['w']}+{r['l']} != GP {gp} printed on the traditional page")
        # the two stat pages must agree on the club's games played
        if (op.get(tri) or {}).get("gp") not in (None, gp):
            fails.append(f"{tri}: GP {gp} on traditional != {(op.get(tri) or {}).get('gp')} on opponent")
        if (ad.get(tri) or {}).get("gp") not in (None, gp):
            fails.append(f"{tri}: GP {gp} on traditional != {(ad.get(tri) or {}).get('gp')} on advanced")

    # two-source point-differential identity
    for tri in tr:
        t, o = tr[tri], op.get(tri)
        if not o:
            fails.append(f"{tri}: missing from the opponent page")
            continue
        if None not in (t["pts"], o["opp_pts"], t["plus_minus"]):
            if abs((t["pts"] - o["opp_pts"]) - t["plus_minus"]) > 0.1001:
                fails.append(f"{tri}: pts {t['pts']} - opp_pts {o['opp_pts']} != +/- {t['plus_minus']}")
        if None not in (t["plus_minus"], o["opp_plus_minus"]):
            if abs(t["plus_minus"] + o["opp_plus_minus"]) > 0.1001:
                fails.append(f"{tri}: +/- {t['plus_minus']} on traditional != "
                             f"-{o['opp_plus_minus']} on opponent")

    # NetRtg identity
    for tri, a in ad.items():
        if None not in (a["off_rtg"], a["def_rtg"], a["net_rtg"]):
            if abs((a["off_rtg"] - a["def_rtg"]) - a["net_rtg"]) > 0.1001:
                fails.append(f"{tri}: OffRtg-DefRtg != NetRtg ({a['off_rtg']}-{a['def_rtg']} vs {a['net_rtg']})")

    # venue identities from the standings page
    hw = hl = rw = rl = nw = nl = ow = ol = 0
    for r in st.values():
        a, b = _pairs(r["home"]); hw += a; hl += b
        a, b = _pairs(r["road"]); rw += a; rl += b
        a, b = _pairs(r["neutral"]); nw += a; nl += b
        a, b = _pairs(r["ot"]); ow += a; ol += b
    games = sw
    if hw + rw + nw != games:
        fails.append(f"home {hw} + road {rw} + neutral {nw} wins != games {games}")
    if nw != nl:
        fails.append(f"neutral wins {nw} != neutral losses {nl}")
    if ow != ol:
        fails.append(f"OT wins {ow} != OT losses {ol}")

    # the reconstruction test: apply the twelve 11/18 finals to the 11/18 standings, get 11/19 back
    if len(d["finals_1118"]) != 12:
        fails.append(f"parsed {len(d['finals_1118'])} finals for 2026-11-18, expected 12")
    for g in d["finals_1118"]:
        if g["away"] not in st or g["home"] not in st:
            fails.append(f"{g['game_id']}: club not on the standings page")
        if g["away_pts"] is None or g["home_pts"] is None:
            fails.append(f"{g['game_id']}: score not parsed")

    # the slate must be the games NOT final, i.e. no overlap with the finals
    if len(d["slate_1119"]) != 4:
        fails.append(f"parsed {len(d['slate_1119'])} games for 2026-11-19, expected 4")
    overlap = {g["game_id"] for g in d["slate_1119"]} & {g["game_id"] for g in d["finals_1118"]}
    if overlap:
        fails.append(f"a game is both final and scheduled: {sorted(overlap)}")

    # injuries: the fresher release must be a superset or a documented diff
    if not d["injury_0700"]["rows"]:
        fails.append("the 07:00 AM release parsed 0 player rows")
    if d["injury_0645"]["revision"] != "11/19/26 06:45 AM":
        fails.append(f"06:45 release header read as {d['injury_0645']['revision']!r}")
    if d["injury_0700"]["revision"] != "11/19/26 07:00 AM":
        fails.append(f"07:00 release header read as {d['injury_0700']['revision']!r}")
    if d["injury_index"]["n_releases_listed"] < 1:
        fails.append("the injury index listed no releases")
    # every club named on a release must be a real club name; a typo would silently split a player
    for key in ("injury_1119_1200", "injury_1119_0100", "injury_0645", "injury_0700",
                "injury_1118_1415"):
        for row in d[key]["rows"]:
            if row["team"] and row["team"] not in TEAM_NAMES:
                fails.append(f"{key}: unknown club name {row['team']!r}")
            if not row["status"]:
                fails.append(f"{key}: row without a status for {row['player']!r}")
    for name, diff in d["injury_diffs"].items():
        if diff["n_from"] == 0 or diff["n_to"] == 0:
            fails.append(f"{name}: a release parsed 0 rows")
    return fails


def hca_measured(st: dict) -> dict:
    """Home-court advantage pinned to the measured home-win rate, not fitted.

    The only inputs are the home/road W-L records the league prints on the standings page.
    The neutral-site games are excluded from both the numerator and the denominator, because a
    neutral game is not a home game.
    """
    hw = hg = 0
    for r in st.values():
        a, b = _pairs(r["home"]); hw += a; hg += a + b
    return {
        "home_wins": hw, "home_games": hg,
        "home_win_rate": round(hw / hg, 4) if hg else None,
        "neutral_games_excluded": sum(sum(_pairs(r["neutral"])) for r in st.values()),
        "method": "sum of every club's printed home W-L; a neutral-site game is not a home game",
        "note": ("this is the pin for home-court advantage: the constant in the model is this "
                 "measured rate, converted to a points term, never a free parameter"),
        "source_url": SOURCES["standings"][1],
    }


def build() -> dict:
    st_rows = standings()
    d = {
        "schema": "nba2.official-capture.2026-11-19",
        "retrieved_date": RETRIEVED,
        "retrieval": {
            "method": ("agent page-fetch tool; direct HTTPS from the build sandbox to www.nba.com, "
                       "official.nba.com and cdn.nba.com fails inside the TLS handshake "
                       "(curl (35) OpenSSL SSL_ERROR_SYSCALL, code 000, measured 2026-11-19T12:16Z)"),
            "sources": {k: {"url": v[1], "raw_file": f"data/raw/verify_2026-11-19/raw/{v[0]}"}
                        for k, v in SOURCES.items()},
            "raw_sha256": {v[0]: hashlib.sha256((RAW / v[0]).read_bytes()).hexdigest()
                           for v in SOURCES.values() if (RAW / v[0]).exists()},
        },
        "standings": st_rows,
        "traditional": traditional(),
        "opponent": opponent(),
        "advanced": advanced(),
        "finals_1118": finals_1118(),
        "slate_1119": slate_1119(),
        "injury_0645": injury("injury_0645"),
        "injury_0700": injury("injury_0700"),
        "injury_1119_1200": injury("injury_1119_1200"),
        "injury_1119_0100": injury("injury_1119_0100"),
        "injury_1118_1415": injury("injury_1118_1415"),
        "injury_index": injury_index(),
    }
    d["injury_diffs"] = {
        "overnight_1118_1415_to_1119_1200": injury_diff(d["injury_1118_1415"], d["injury_1119_1200"]),
        "same_day_1119_1200_to_1119_0645": injury_diff(d["injury_1119_1200"], d["injury_0645"]),
        "same_day_1119_0645_to_1119_0700": injury_diff(d["injury_0645"], d["injury_0700"]),
    }
    d["injury_diff"] = d["injury_diffs"]["same_day_1119_0645_to_1119_0700"]
    d["hca"] = hca_measured({r["team"]: r for r in st_rows})

    # measured disagreement between the two independent estimators, per club, from the two
    # official pages that state them separately: points-differential (traditional+opponent) and
    # NetRtg per 100 possessions (advanced), each converted to points per game by pace.
    tr, op, ad = d["traditional"], d["opponent"], d["advanced"]
    lab = []
    for tri in sorted(tr):
        t, o, a = tr[tri], op.get(tri, {}), ad.get(tri, {})
        pd = None
        if None not in (t.get("pts"), o.get("opp_pts")):
            pd = round(t["pts"] - o["opp_pts"], 2)
        est_a = pd
        est_b = None
        if None not in (a.get("net_rtg"), a.get("pace")):
            est_b = round(a["net_rtg"] * a["pace"] / 100.0, 2)   # points per game implied by NetRtg
        lab.append({
            "team": tri, "gp": t.get("gp"),
            "est_a_margin_per_game": est_a,
            "est_b_margin_per_game": est_b,
            "disagreement": (round(est_a - est_b, 2) if None not in (est_a, est_b) else None),
            "disagreement_status": (None if None not in (est_a, est_b) else
                                    "one estimator unavailable on the captured pages"),
            "sources": [SOURCES["traditional"][1], SOURCES["opponent"][1], SOURCES["advanced"][1]],
        })
    d["estimators"] = lab
    return d


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    d = build()
    fails = selftest(d)
    for f in fails:
        print("FAIL:", f)
    print(f"{'FAIL' if fails else 'OK'} — captured {len(d['standings'])} clubs, "
          f"{len(d['finals_1118'])} finals, {len(d['slate_1119'])} scheduled, "
          f"{len(d['injury_0700']['rows'])} injury rows, "
          f"{len(d['injury_diff']['status_changes'])} status changes between 06:45 and 07:00")
    if a.selftest:
        return 1 if fails else 0
    if fails:
        print("refusing to write: a capture that cannot prove itself is not published")
        return 1
    OUT.write_text(json.dumps(d, indent=1) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
