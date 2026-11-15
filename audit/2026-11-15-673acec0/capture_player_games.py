"""Transcribe the per-player game logs read off two official NBA box-score pages.

Source of every row: the official box score page for that game,
    https://www.nba.com/game/<slug>-<gameid>/box-score
read in this session (2026-11-15). Nothing here is interpolated: each row is one printed
line of the "Traditional" table, and the "Inactive Players" line printed under that table.

Why only two games
------------------
The official box score is per-game HTML and is the only per-player source reachable from
this environment (the CDN box-score JSON returns HTTP 500 and stats.nba.com player game-log
pages render season aggregates only). Each page has to be read and transcribed by hand, so
this session captured the two games that carry the most injured-team value: UTA appears in
both, so minutes shares for Utah rest on two observations rather than one.

The games picked are the two most recent ones involving teams with the largest injured
lists on the 2026-11-15 official injury report (UTA 7 designations, HOU 6).

Every row is checked for arithmetic consistency (team minutes must total 240 in a
regulation game, and the player points must total the team score) in nba2/v2/rotation.py.
"""
from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]

# (game_id, date, team, opponent, is_home, player, player_id, min, pts, reb, ast, status)
# status: played | dnp | dnd | inactive   (dnp/dnd/inactive carry no minutes)
ROWS = [
    # ---- 2026-11-13  UTA @ HOU  (HOU 125, UTA 118) -------------------------------------
    ("0022600039", "2026-11-13", "UTA", "HOU", False, "Josh Okogie", "1629006", "21:43", 7, 2, 1, "played"),
    ("0022600039", "2026-11-13", "UTA", "HOU", False, "Ace Bailey", "1642846", "34:32", 21, 3, 1, "played"),
    ("0022600039", "2026-11-13", "UTA", "HOU", False, "Jaxson Hayes", "1629637", "13:27", 12, 5, 1, "played"),
    ("0022600039", "2026-11-13", "UTA", "HOU", False, "Darryn Peterson", "1643408", "33:58", 28, 7, 2, "played"),
    ("0022600039", "2026-11-13", "UTA", "HOU", False, "Keyonte George", "1641718", "37:32", 27, 4, 7, "played"),
    ("0022600039", "2026-11-13", "UTA", "HOU", False, "Mo Bamba", "1628964", "19:53", 9, 9, 1, "played"),
    ("0022600039", "2026-11-13", "UTA", "HOU", False, "Brice Sensabaugh", "1641729", "26:59", 7, 3, 1, "played"),
    ("0022600039", "2026-11-13", "UTA", "HOU", False, "Isaiah Collier", "1642268", "15:59", 3, 2, 5, "played"),
    ("0022600039", "2026-11-13", "UTA", "HOU", False, "Josh Green", "1630182", "14:21", 2, 0, 0, "played"),
    ("0022600039", "2026-11-13", "UTA", "HOU", False, "Svi Mykhailiuk", "1629004", "7:01", 0, 1, 0, "played"),
    ("0022600039", "2026-11-13", "UTA", "HOU", False, "Tony Bradley", "1628396", "12:28", 0, 5, 1, "played"),
    ("0022600039", "2026-11-13", "UTA", "HOU", False, "Kyle Filipowski", "1642271", "2:07", 2, 0, 0, "played"),
    ("0022600039", "2026-11-13", "UTA", "HOU", False, "Jusuf Nurkic", "", "", None, None, None, "inactive"),
    ("0022600039", "2026-11-13", "UTA", "HOU", False, "Lauri Markkanen", "", "", None, None, None, "inactive"),
    ("0022600039", "2026-11-13", "UTA", "HOU", False, "Jaren Jackson Jr.", "", "", None, None, None, "inactive"),
    ("0022600039", "2026-11-13", "UTA", "HOU", False, "Harrison Ingram", "1631127", "", None, None, None, "inactive"),
    ("0022600039", "2026-11-13", "UTA", "HOU", False, "Kobe Bufkin", "1641723", "", None, None, None, "inactive"),
    ("0022600039", "2026-11-13", "UTA", "HOU", False, "Trey Alexander", "", "", None, None, None, "inactive"),

    ("0022600039", "2026-11-13", "HOU", "UTA", True, "Kevin Durant", "201142", "33:25", 22, 3, 6, "played"),
    ("0022600039", "2026-11-13", "HOU", "UTA", True, "Jabari Smith Jr.", "1631095", "24:03", 6, 3, 0, "played"),
    ("0022600039", "2026-11-13", "HOU", "UTA", True, "Alperen Sengun", "1630578", "37:05", 43, 12, 5, "played"),
    ("0022600039", "2026-11-13", "HOU", "UTA", True, "Amen Thompson", "1641708", "40:53", 12, 10, 3, "played"),
    ("0022600039", "2026-11-13", "HOU", "UTA", True, "Fred VanVleet", "1627832", "33:47", 17, 2, 3, "played"),
    ("0022600039", "2026-11-13", "HOU", "UTA", True, "Tari Eason", "1631106", "33:20", 14, 11, 2, "played"),
    ("0022600039", "2026-11-13", "HOU", "UTA", True, "Reed Sheppard", "1642263", "19:09", 0, 0, 3, "played"),
    ("0022600039", "2026-11-13", "HOU", "UTA", True, "Oscar Tshiebwe", "1631131", "5:57", 0, 5, 0, "played"),
    ("0022600039", "2026-11-13", "HOU", "UTA", True, "Bogdan Bogdanović", "203992", "12:21", 11, 1, 3, "played"),
    ("0022600039", "2026-11-13", "HOU", "UTA", True, "Steven Adams", "203500", "", None, None, None, "dnp"),
    ("0022600039", "2026-11-13", "HOU", "UTA", True, "Clint Capela", "203991", "", None, None, None, "dnp"),
    ("0022600039", "2026-11-13", "HOU", "UTA", True, "Isaiah Crawford", "1642384", "", None, None, None, "dnp"),
    ("0022600039", "2026-11-13", "HOU", "UTA", True, "Marcus Smart", "203935", "", None, None, None, "dnp"),
    ("0022600039", "2026-11-13", "HOU", "UTA", True, "Jae'Sean Tate", "1630256", "", None, None, None, "dnp"),
    ("0022600039", "2026-11-13", "HOU", "UTA", True, "Bruce Thornton", "1643570", "", None, None, None, "dnp"),
    ("0022600039", "2026-11-13", "HOU", "UTA", True, "Julian Phillips", "", "", None, None, None, "inactive"),
    ("0022600039", "2026-11-13", "HOU", "UTA", True, "Quadir Copeland", "", "", None, None, None, "inactive"),

    # ---- 2026-11-11  ORL @ UTA  (ORL 123, UTA 108) -------------------------------------
    ("0022600224", "2026-11-11", "ORL", "UTA", False, "Alex Morales", "1631457", "17:32", 5, 4, 3, "played"),
    ("0022600224", "2026-11-11", "ORL", "UTA", False, "Franz Wagner", "1630532", "39:22", 38, 8, 1, "played"),
    ("0022600224", "2026-11-11", "ORL", "UTA", False, "Wendell Carter Jr.", "1628976", "27:59", 9, 7, 3, "played"),
    ("0022600224", "2026-11-11", "ORL", "UTA", False, "Desmond Bane", "1630217", "34:18", 25, 3, 2, "played"),
    ("0022600224", "2026-11-11", "ORL", "UTA", False, "Anthony Black", "1641710", "38:30", 22, 7, 8, "played"),
    ("0022600224", "2026-11-11", "ORL", "UTA", False, "Jase Richardson", "1642859", "19:52", 6, 1, 2, "played"),
    ("0022600224", "2026-11-11", "ORL", "UTA", False, "Nikola Vučević", "202696", "13:58", 3, 5, 1, "played"),
    ("0022600224", "2026-11-11", "ORL", "UTA", False, "Goga Bitadze", "1629048", "20:01", 4, 7, 0, "played"),
    ("0022600224", "2026-11-11", "ORL", "UTA", False, "Jevon Carter", "1628975", "27:44", 11, 3, 4, "played"),
    ("0022600224", "2026-11-11", "ORL", "UTA", False, "Colin Castleton", "1630658", "0:44", 0, 0, 0, "played"),
    ("0022600224", "2026-11-11", "ORL", "UTA", False, "Jamal Cain", "1631288", "", None, None, None, "dnd"),
    ("0022600224", "2026-11-11", "ORL", "UTA", False, "Tristan da Silva", "1641783", "", None, None, None, "dnd"),
    ("0022600224", "2026-11-11", "ORL", "UTA", False, "Noah Penda", "", "", None, None, None, "inactive"),
    ("0022600224", "2026-11-11", "ORL", "UTA", False, "Izaiyah Nelson", "", "", None, None, None, "inactive"),
    ("0022600224", "2026-11-11", "ORL", "UTA", False, "Jonathan Isaac", "", "", None, None, None, "inactive"),
    ("0022600224", "2026-11-11", "ORL", "UTA", False, "Jalen Suggs", "", "", None, None, None, "inactive"),
    ("0022600224", "2026-11-11", "ORL", "UTA", False, "Paolo Banchero", "", "", None, None, None, "inactive"),

    ("0022600224", "2026-11-11", "UTA", "ORL", True, "Josh Green", "1630182", "25:53", 3, 2, 1, "played"),
    ("0022600224", "2026-11-11", "UTA", "ORL", True, "Ace Bailey", "1642846", "31:05", 18, 7, 2, "played"),
    ("0022600224", "2026-11-11", "UTA", "ORL", True, "Jaxson Hayes", "1629637", "30:03", 11, 8, 0, "played"),
    ("0022600224", "2026-11-11", "UTA", "ORL", True, "Darryn Peterson", "1643408", "32:50", 22, 4, 5, "played"),
    ("0022600224", "2026-11-11", "UTA", "ORL", True, "Keyonte George", "1641718", "33:13", 13, 7, 7, "played"),
    ("0022600224", "2026-11-11", "UTA", "ORL", True, "Svi Mykhailiuk", "1629004", "19:31", 3, 0, 2, "played"),
    ("0022600224", "2026-11-11", "UTA", "ORL", True, "Mo Bamba", "1628964", "17:57", 5, 1, 1, "played"),
    ("0022600224", "2026-11-11", "UTA", "ORL", True, "Josh Okogie", "1629006", "15:13", 7, 3, 0, "played"),
    ("0022600224", "2026-11-11", "UTA", "ORL", True, "Isaiah Collier", "1642268", "11:36", 7, 3, 2, "played"),
    ("0022600224", "2026-11-11", "UTA", "ORL", True, "Brice Sensabaugh", "1641729", "22:39", 19, 3, 1, "played"),
    ("0022600224", "2026-11-11", "UTA", "ORL", True, "Tony Bradley", "1628396", "", None, None, None, "dnp"),
    ("0022600224", "2026-11-11", "UTA", "ORL", True, "Kobe Bufkin", "1641723", "", None, None, None, "dnp"),
    ("0022600224", "2026-11-11", "UTA", "ORL", True, "Kyle Filipowski", "1642271", "", None, None, None, "dnp"),
    ("0022600224", "2026-11-11", "UTA", "ORL", True, "Harrison Ingram", "1631127", "", None, None, None, "dnp"),
    ("0022600224", "2026-11-11", "UTA", "ORL", True, "Lauri Markkanen", "", "", None, None, None, "inactive"),
    ("0022600224", "2026-11-11", "UTA", "ORL", True, "Jaren Jackson Jr.", "", "", None, None, None, "inactive"),
    ("0022600224", "2026-11-11", "UTA", "ORL", True, "Jusuf Nurkic", "", "", None, None, None, "inactive"),
    ("0022600224", "2026-11-11", "UTA", "ORL", True, "Trey Alexander", "", "", None, None, None, "inactive"),
]

GAMES = {
    "0022600039": {
        "date": "2026-11-13", "away": "UTA", "home": "HOU",
        "away_pts": 118, "home_pts": 125, "ot": False,
        "slug": "uta-vs-hou-0022600039",
        "arena": "Toyota Center", "city": "Houston, TX",
    },
    "0022600224": {
        "date": "2026-11-11", "away": "ORL", "home": "UTA",
        "away_pts": 123, "home_pts": 108, "ot": False,
        "slug": "orl-vs-uta-0022600224",
        "arena": "Delta Center", "city": "Salt Lake City, UT",
    },
}


def main() -> None:
    out = []
    for (gid, date, team, opp, home, player, pid, mins, pts, reb, ast, status) in ROWS:
        g = GAMES[gid]
        out.append({
            "game_id": gid,
            "date": date,
            "team": team,
            "opponent": opp,
            "home": home,
            "player": player,
            "player_id": pid,
            "min": mins,
            "pts": pts,
            "reb": reb,
            "ast": ast,
            "status": status,
            "team_pts": g["home_pts"] if home else g["away_pts"],
            "source": f"https://www.nba.com/game/{g['slug']}/box-score",
        })
    doc = {
        "schema": "nba2.player-games.v1",
        "captured_at_utc": "2026-11-15",
        "captured_by": "session arena/673acec0-nba2",
        "retrieval_method": ("official nba.com box score page, Traditional table, read and "
                             "transcribed line by line in this session"),
        "game_page_pattern": "https://www.nba.com/game/<away>-vs-<home>-<game_id>/box-score",
        "games": GAMES,
        "n_games": len(GAMES),
        "n_rows": len(out),
        "rows": out,
        "coverage_note": (
            "2 of the 188 official finals in the results feed. Only these two were read, so "
            "every row is sourced but the sample is small; nba2/v2/rotation.py prints the "
            "coverage it actually has and leaves uncounted cells blank."),
    }
    path = ROOT / "data" / "raw" / "player_games.json"
    path.write_text(json.dumps(doc, indent=2) + "\n")
    print(f"wrote {path.relative_to(ROOT)}: {len(out)} rows over {len(GAMES)} games")
    for gid, g in GAMES.items():
        rs = [r for r in out if r["game_id"] == gid]
        for t in (g["away"], g["home"]):
            pl = [r for r in rs if r["team"] == t and r["status"] == "played"]
            secs = sum(int(r["min"].split(":")[0]) * 60 + int(r["min"].split(":")[1])
                       for r in pl)
            print(f"  {gid} {t}: {len(pl)} players, minutes {secs//60}:{secs%60:02d}, "
                  f"pts {sum(r['pts'] for r in pl)}")


if __name__ == "__main__":
    main()
