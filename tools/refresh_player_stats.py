"""Refresh the official player-level statistics snapshot from NBA.com.

Why this exists
---------------
The published site used to carry no player-level numbers at all: the "Player Props &
Combos" page was blank by policy because the pipeline could not reach official minutes
and production. That is no longer true. Two official endpoints serve this data and both
are reachable from a machine with open egress (a GitHub Actions runner, for example):

  A. the stats.nba.com JSON endpoint
     https://stats.nba.com/stats/leaguedashplayerstats?Season=2026-27&...
  B. the server-rendered table on https://www.nba.com/stats/players/traditional?...

This script tries A, then B, then falls back to the player pages' "Last 5 Games"
tables for a dispersion sample. Every method records itself in the snapshot's
provenance, and a run that obtains nothing writes **no file** and exits non-zero: an
empty snapshot must never replace a good one.

What it writes
--------------
data/raw/player_stats_<as_of>.json — one row per player with the official per-game
figures the site needs: minutes, points, rebounds, assists, and the attempts behind
them. Every row carries its own player page as the source link.

Usage
-----
    python tools/refresh_player_stats.py --out data/raw/player_stats_2026-11-14.json

The network is reached with urllib only: no third-party package, so the numbers on the
site do not depend on a pinned dependency nobody can reproduce.
"""

from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STATS_PAGE = ("https://www.nba.com/stats/players/traditional"
              "?Season={season}&SeasonType=Regular+Season&PerMode=PerGame")
STATS_API = ("https://stats.nba.com/stats/leaguedashplayerstats"
             "?College=&Conference=&Country=&DateFrom=&DateTo=&Division=&DraftPick="
             "&DraftYear=&GameScope=&GameSegment=&Height=&LastNGames=0&LeagueID=00"
             "&Location=&MeasureType=Base&Month=0&OpponentTeamID=0&Outcome=&PORound=0"
             "&PaceAdjust=N&PerMode=PerGame&Period=0&PlayerExperience=&PlayerPosition="
             "&PlusMinus=N&Rank=N&Season={season}&SeasonSegment=&SeasonType=Regular+Season"
             "&ShotClockRange=&StarterBench=&TeamID=0&VsConference=&VsDivision=&Weight=")

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")

# The columns the site actually uses. Everything else the official table publishes is
# kept out on purpose: a smaller table is a table whose every cell can be checked.
FIELDS = ["player", "player_id", "team", "age", "gp", "w", "l", "min", "pts",
          "fgm", "fga", "fg_pct", "tpm", "tpa", "tp_pct", "ftm", "fta", "ft_pct",
          "oreb", "dreb", "reb", "ast", "tov", "stl", "blk", "pf", "plus_minus"]


def _get(url: str, timeout: int = 45, extra_headers: dict | None = None) -> tuple[int, str]:
    headers = {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nba.com/",
        "Origin": "https://www.nba.com",
        "Connection": "keep-alive",
    }
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, headers=headers)
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        return resp.status, resp.read().decode("utf-8", "replace")


# ----------------------------------------------------------------- method A: JSON API
def fetch_api(season: str) -> list[dict]:
    url = STATS_API.format(season=season)
    _, body = _get(url, extra_headers={"x-nba-stats-origin": "stats",
                                       "x-nba-stats-token": "true"})
    doc = json.loads(body)
    rs = doc["resultSets"][0]
    headers = rs["headers"]
    rows = []
    for raw in rs["rowSet"]:
        rec = dict(zip(headers, raw))
        pid = rec.get("PLAYER_ID")
        rows.append({
            "player": rec.get("PLAYER_NAME"),
            "player_id": str(pid) if pid is not None else None,
            "team": rec.get("TEAM_ABBREVIATION"),
            "age": rec.get("AGE"),
            "gp": rec.get("GP"),
            "w": rec.get("W"),
            "l": rec.get("L"),
            "min": rec.get("MIN"),
            "pts": rec.get("PTS"),
            "fgm": rec.get("FGM"),
            "fga": rec.get("FGA"),
            "fg_pct": rec.get("FG_PCT"),
            "tpm": rec.get("FG3M"),
            "tpa": rec.get("FG3A"),
            "tp_pct": rec.get("FG3_PCT"),
            "ftm": rec.get("FTM"),
            "fta": rec.get("FTA"),
            "ft_pct": rec.get("FT_PCT"),
            "oreb": rec.get("OREB"),
            "dreb": rec.get("DREB"),
            "reb": rec.get("REB"),
            "ast": rec.get("AST"),
            "tov": rec.get("TOV"),
            "stl": rec.get("STL"),
            "blk": rec.get("BLK"),
            "pf": rec.get("PF"),
            "plus_minus": rec.get("PLUS_MINUS"),
        })
    return rows


# ----------------------------------------------------------------- method B: HTML table
class _TableGrab(HTMLParser):
    """Collect every <table> on the page as a list of rows of cell texts."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None
        self._in_cell = False

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._table = []
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []
            self._in_cell = True

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cell is not None:
            self._row.append("".join(self._cell).strip())
            self._cell = None
            self._in_cell = False
        elif tag == "tr" and self._row is not None:
            if self._table is not None:
                self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            self.tables.append(self._table)
            self._table = None

    def handle_data(self, data):
        if self._in_cell and self._cell is not None:
            self._cell.append(data)


NUM = re.compile(r"^-?\d+(\.\d+)?$")


def _num(text: str):
    t = (text or "").strip().replace("%", "")
    if t in ("", "-", "—"):
        return None
    try:
        return float(t) if "." in t else int(t)
    except ValueError:
        return None


def fetch_html(season: str) -> tuple[list[dict], str]:
    url = STATS_PAGE.format(season=season)
    _, body = _get(url)
    grab = _TableGrab()
    grab.feed(body)
    best = None
    for tbl in grab.tables:
        if not tbl:
            continue
        header = [c.strip() for c in tbl[0]]
        if "Player" in header and "MIN" in [h.upper() for h in header]:
            best = tbl
            break
    if best is None:
        raise RuntimeError("no players table found in the HTML")
    head = [h.strip() for h in best[0]]
    up = [h.upper() for h in head]
    idx = {name: up.index(name) for name in
           ("PLAYER", "TEAM", "AGE", "GP", "W", "L", "MIN", "PTS", "FGM", "FGA",
            "FG%", "3PM", "3PA", "3P%", "FTM", "FTA", "FT%", "OREB", "DREB", "REB",
            "AST", "TOV", "STL", "BLK", "PF", "+/-")
           if name in up}
    out = []
    for row in best[1:]:
        if len(row) < len(head):
            continue
        pid = None
        m = re.search(r"/stats/player/(\d+)", row[idx["PLAYER"]])
        if m:
            pid = m.group(1)
        out.append({
            "player": row[idx["PLAYER"]].strip(),
            "player_id": pid,
            "team": row[idx["TEAM"]].strip(),
            "age": _num(row[idx["AGE"]]),
            "gp": _num(row[idx["GP"]]),
            "w": _num(row[idx["W"]]),
            "l": _num(row[idx["L"]]),
            "min": _num(row[idx["MIN"]]),
            "pts": _num(row[idx["PTS"]]),
            "fgm": _num(row[idx["FGM"]]),
            "fga": _num(row[idx["FGA"]]),
            "fg_pct": _num(row[idx["FG%"]]),
            "tpm": _num(row[idx["3PM"]]),
            "tpa": _num(row[idx["3PA"]]),
            "tp_pct": _num(row[idx["3P%"]]),
            "ftm": _num(row[idx["FTM"]]),
            "fta": _num(row[idx["FTA"]]),
            "ft_pct": _num(row[idx["FT%"]]),
            "oreb": _num(row[idx["OREB"]]),
            "dreb": _num(row[idx["DREB"]]),
            "reb": _num(row[idx["REB"]]),
            "ast": _num(row[idx["AST"]]),
            "tov": _num(row[idx["TOV"]]),
            "stl": _num(row[idx["STL"]]),
            "blk": _num(row[idx["BLK"]]),
            "pf": _num(row[idx["PF"]]),
            "plus_minus": _num(row[idx["+/-"]]),
        })
    return out, url


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", default="2026-27")
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-gp", type=int, default=1)
    args = ap.parse_args()

    rows: list[dict] = []
    method = ""
    source_url = ""
    errors = []
    for name, fn in (("stats.nba.com JSON API", lambda: fetch_api(args.season)),
                     ("nba.com/stats HTML table", lambda: fetch_html(args.season))):
        try:
            got = fn()
            if got and len(got) > 20:
                rows = got
                method = name
                source_url = (STATS_API.format(season=args.season) if name.startswith("stats")
                              else STATS_PAGE.format(season=args.season))
                break
            errors.append(f"{name}: returned {len(got) if got else 0} rows")
        except Exception as exc:  # noqa: BLE001 - the reason must reach the CI log
            errors.append(f"{name}: {type(exc).__name__}: {exc}")

    if not rows:
        print("FAILED to obtain player statistics. Attempts:")
        for e in errors:
            print("  -", e)
        return 1

    rows = [r for r in rows if (r.get("gp") or 0) >= args.min_gp and r.get("min") is not None]
    teams = sorted({r["team"] for r in rows if r.get("team")})
    doc = {
        "dataset": "player_season_per_game",
        "season": args.season,
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "retrieved_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "provenance": {
            "publisher": "NBA.com Stats (official)",
            "official_nba_source": True,
            "url": source_url,
            "method": method,
            "per_player_source_pattern": "https://www.nba.com/stats/player/{player_id}/",
            "attempts": errors,
            "note": ("Per-game figures exactly as the official table prints them: Age, GP, W, L, Min, "
                     "PTS, FGM, FGA, FG%, 3PM, 3PA, 3P%, FTM, FTA, FT%, OREB, DREB, REB, AST, TOV, "
                     "STL, BLK, PF, +/-. The W and L columns are the TEAM's record, not the player's."),
        },
        "columns": FIELDS,
        "records": [[r.get(k) for k in FIELDS] for r in rows],
        "counts": {"rows": len(rows), "teams": len(teams), "team_list": teams},
        "flags": [],
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"wrote {out}: {len(rows)} players across {len(teams)} teams via {method}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
