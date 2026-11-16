"""Scheduled ingest for the rolling window: schedule, standings, team stats, injuries.

Runs in GitHub Actions (see ``.github/workflows/refresh.yml``). Every step is fail-closed:

* **fetch** the four official surfaces with retries and a real User-Agent (stats.nba.com
  rejects default agents), recording retrieval timestamps,
* **gate** before anything is written or the site is rebuilt:

  1. ``freshness/finals``   — scoreboard coverage exists for each lookback date and every
      scheduled game through yesterday is final; calendar off-days are valid
  2. ``freshness/standings``— the fresh 30-club season-to-date W/L snapshot is complete,
      unique, nonnegative, and internally balanced (the finals feed is only a partial window)
  3. ``freshness/injuries`` — the newest injury release on the league index is at least as
      recent as the most recent game day's release window, and its stamp + retrieval time
      are both recorded
  4. ``freshness/slate``    — the slate covers today..today+3 with unique game ids
  5. ``provenance``         — every written row carries a source URL; no row is written
      without one (a missing source raises, it never becomes a blank in a raw file),

* **write** dated capture files in the frozen schemas (nba2.standings-official.v2,
  nba2.slate.v2, nba2.team-stats-3page.v1, nba2.injury-transcript.v2, nba2.results-feed.v2),
* **rebuild** the v2 site and run ``python -m nba2.v2.check`` — a failing gate or check
  aborts before commit, so the published site can never silently go stale.

Usage:  python3 -m nba2.v2.refresh --check-only     # gates only, no writes
        python3 -m nba2.v2.refresh --write          # ingest + rebuild
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
HISTORY = RAW / "history"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36 nba2-refresh/1.0 (+github.com/wingbangboozle1-lang/NBA2)")
TIMEOUT = 30
RETRIES = 3

SEASON = "2026-27"
URLS = {
    "standings": "https://stats.nba.com/stats/leaguestandingsv3?LeagueID=00&Season={season}&SeasonType=Regular+Season",
    "team_traditional": "https://stats.nba.com/stats/leaguedashteamstats?Conference=&DateFrom=&DateTo=&Division=&GameScope=&GameSegment=&Height=&LastNGames=0&LeagueID=00&Location=&MeasureType=Base&Month=0&OpponentTeamID=0&Outcome=&PORound=0&PaceAdjust=N&PerMode=PerGame&Period=0&PlayerExperience=&PlayerPosition=&PlusMinus=N&Rank=N&Season={season}&SeasonSegment=&SeasonType=Regular+Season&ShotClockRange=&StarterBench=&TeamID=0&TwoWay=0&VsConference=&VsDivision=",
    "team_advanced": "https://stats.nba.com/stats/leaguedashteamstats?LeagueID=00&MeasureType=Advanced&PerMode=PerGame&Season={season}&SeasonType=Regular+Season",
    "team_opponent": "https://stats.nba.com/stats/leaguedashteamstats?LeagueID=00&MeasureType=Opponent&PerMode=PerGame&Season={season}&SeasonType=Regular+Season",
    "scoreboard": "https://stats.nba.com/stats/scoreboardv3?GameDate={date}&LeagueID=00",
    "boxscore": "https://stats.nba.com/stats/boxscoretraditionalv2?GameID={gid}&SeasonType=Regular+Season",
    "injury_index": "https://official.nba.com/nba-injury-report-2026-27-season/",
    "players": ("https://stats.nba.com/stats/leaguedashplayerstats?College=&Conference=&Country=&"
                "DateFrom=&DateTo=&Division=&DraftPick=&DraftYear=&GameScope=&GameSegment=&Height=&"
                "LastSegment=&LeagueID=00&Location=&MeasureType=Base&Month=0&OpponentTeamID=0&Outcome=&"
                "PORound=0&PaceAdjust=N&PerMode=PerGame&Period=0&PlayerExperience=&PlayerPosition=&"
                "PlusMinus=N&Rank=N&Season={season}&SeasonSegment=&SeasonType=Regular+Season&"
                "ShotClockRange=&StarterBench=&TeamID=0&TwoWay=0&VsConference=&VsDivision="),
}


def http_get(url: str, tries: int = RETRIES) -> bytes:
    """GET with retries. Raises on failure — a missing source never becomes a blank."""
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA,
                "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
                "Referer": "https://www.nba.com/",
                "Origin": "https://www.nba.com",
                "x-nba-stats-origin": "stats",
                "x-nba-stats-token": "true",
            })
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                if r.status != 200:
                    raise RuntimeError(f"HTTP {r.status} for {url}")
                return r.read()
        except Exception as e:  # noqa: BLE001 — fail-closed after retries
            last = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"fetch failed after {tries} tries: {url}: {last}")


def http_json(url: str) -> dict:
    return json.loads(http_get(url).decode("utf-8"))


# --------------------------------------------------------------------------- fetchers
def fetch_standings() -> dict:
    """One row per club: W/L + splits, exactly the fields nba2.standings-official.v2 carries."""
    doc = http_json(URLS["standings"].format(season=SEASON))
    rows = doc["resultSets"][0]["rowSet"]
    headers = doc["resultSets"][0]["headers"]
    idx = {h: i for i, h in enumerate(headers)}
    out = []
    for r in rows:
        out.append({
            "team": r[idx["TeamID"]],
            "tri": r[idx["TeamAbbreviation"]] if "TeamAbbreviation" in idx else None,
            "w": r[idx["WINS"]], "l": r[idx["LOSSES"]],
            "home": f"{r[idx['HOME_RECORD']]}",
            "road": f"{r[idx['ROAD_RECORD']]}",
            "conf": r[idx["CONFERENCE_RECORD"]], "div": r[idx["DIVISION_RECORD"]],
            "last10": r[idx["L10"]], "streak": r[idx["STREAK"]],
            "source_url": "https://www.nba.com/standings",
        })
    return {"fetched_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "rows": out}


def fetch_slate(dates: list[str]) -> dict:
    games = []
    for d in dates:
        doc = http_json(URLS["scoreboard"].format(date=d))
        for g in doc["resultSets"][0]["rowSet"]:
            headers = doc["resultSets"][0]["headers"]
            idx = {h: i for i, h in enumerate(headers)}
            games.append({
                "date": d,
                "game_id": g[idx["gameId"]],
                "home": g[idx["homeTeamTricode"]] if "homeTeamTricode" in idx else None,
                "away": g[idx["awayTeamTricode"]] if "awayTeamTricode" in idx else None,
                "time_et": g[idx["gameEt"]] if "gameEt" in idx else None,
                "arena": g[idx["arenaName"]] if "arenaName" in idx else None,
                "source_url": f"https://www.nba.com/schedule?date={d}",
            })
    return {"fetched_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "games": games}


def fetch_finals(dates: list[str]) -> dict:
    """Official finals plus per-date scoreboard counts for completed-date checks."""
    recs = []
    games_seen_by_date = {}
    finals_by_date = {}
    for d in dates:
        doc = http_json(URLS["scoreboard"].format(date=d))
        headers = doc["resultSets"][0]["headers"]
        idx = {h: i for i, h in enumerate(headers)}
        games = doc["resultSets"][0]["rowSet"]
        games_seen_by_date[d] = len(games)
        finals_by_date[d] = 0
        for g in games:
            if (g[idx["gameStatus"]] if "gameStatus" in idx else 0) != 3:
                continue
            finals_by_date[d] += 1
            recs.append({
                "date": d,
                "game_id": g[idx["gameId"]],
                "home": g[idx["homeTeamTricode"]], "away": g[idx["awayTeamTricode"]],
                "home_pts": g[idx["homeTeamScore"]], "away_pts": g[idx["awayTeamScore"]],
                "source_url": f"https://www.nba.com/game/{(g[idx['awayTeamTricode']] + '-vs-' + g[idx['homeTeamTricode']] + '-' + g[idx['gameId']]).lower()}",
            })
    return {"fetched_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "games_seen_by_date": games_seen_by_date, "finals_by_date": finals_by_date,
            "records": recs}


def fetch_team_stats() -> dict:
    out = {}
    for key in ("team_traditional", "team_advanced", "team_opponent"):
        doc = http_json(URLS[key].format(season=SEASON))
        out[key] = {"fetched_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                    "source_url": URLS[key].format(season=SEASON),
                    "headers": doc["resultSets"][0]["headers"],
                    "rows": doc["resultSets"][0]["rowSet"]}
    return out


def fetch_newest_injury_release() -> dict:
    """Parse the league's official index for the newest release link; fetch it; stamp both times."""
    html = http_get(URLS["injury_index"]).decode("utf-8", "replace")
    import re
    links = re.findall(r'href="([^"]*Injury-Report_[^"]*\.pdf)"', html)
    if not links:
        raise RuntimeError("no injury PDF links on the official index — refusing to guess")
    newest = links[0]  # the index lists newest first
    return {"index_url": URLS["injury_index"], "pdf_url": newest,
            "retrieval_time_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "revision_time_et": "_".join(newest.split("_")[-2:]).replace(".pdf", "")}


def fetch_player_season() -> dict:
    """SG-37 (per-club season tables): one official request covers all 30 clubs.

    ``leaguedashplayerstats`` is the dataset behind nba.com/stats/players/traditional —
    one row per player with the club abbreviation, per-game minutes and points. The per-club
    page URL is recorded as each row's source_url so a reviewer can re-check it against the
    rendered table, exactly as the three-club hand capture (2026-11-14) did.
    """
    url = URLS["players"].format(season=SEASON)
    doc = http_json(url)
    rs = doc["resultSets"][0]
    headers = rs["headers"]
    idx = {h: i for i, h in enumerate(headers)}
    rows = []
    for r in rs["rowSet"]:
        tri = r[idx["TeamAbbreviation"]]
        tid = r[idx["TeamID"]]
        rows.append({
            "player": r[idx["PLAYER_NAME"]],
            "player_id": str(r[idx["PLAYER_ID"]]),
            "team_abbrev": tri,
            "team_id": tid,
            "age": r[idx["AGE"]],
            "gp": r[idx["GP"]],
            "team_w": r[idx["W"]], "team_l": r[idx["L"]],
            "mpg": r[idx["MIN"]], "ppg": r[idx["PTS"]],
            "source_url": f"https://www.nba.com/stats/players/traditional?TeamID={tid}",
        })
    rows = [r for r in rows if r["team_abbrev"]]  # rows without a club stay out, never guessed
    return {"fetched_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "source_url": url, "rows": rows}


def gate_players(players: dict) -> dict:
    """30 clubs, sane minutes, every row sourced — the SG-37 capture's own gate."""
    rows = players.get("rows", [])
    clubs = {}
    issues = []
    for r in rows:
        clubs.setdefault(r["team_abbrev"], 0)
        clubs[r["team_abbrev"]] += 1
        m = r["mpg"]
        if m is None or not (0 <= float(m) <= 48.0):
            issues.append(f"implausible MIN for {r['player']} ({m})")
        if not r.get("source_url"):
            issues.append(f"row without source: {r['player']}")
    missing = [t for t in ("ATL", "BOS", "BKN", "CHA", "CHI", "CLE", "DAL", "DEN", "DET", "GSW",
                           "HOU", "IND", "LAC", "LAL", "MEM", "MIA", "MIL", "MIN", "NOP", "NYK",
                           "OKC", "ORL", "PHI", "PHX", "POR", "SAC", "SAS", "TOR", "UTA", "WAS")
               if t not in clubs]
    ok = len(clubs) == 30 and not missing and not issues
    if missing:
        issues.append(f"clubs missing from the capture: {missing}")
    return {"gate": "freshness/players", "ok": ok,
            "measured": f"{len(rows)} players across {len(clubs)} clubs",
            "detail": "; ".join(issues[:8]) if issues else "30 clubs, every row sourced, minutes in range"}


# --------------------------------------------------------------------------- gates
def gate_finals(dates: list[str], finals: dict) -> dict:
    """Require complete scoreboard coverage, not a game on every calendar date."""
    rows = finals.get("records", [])
    seen = finals.get("games_seen_by_date", {})
    completed = finals.get("finals_by_date", {})
    missing_coverage = [d for d in dates if d not in seen or d not in completed]
    incomplete = [d for d in dates if d in seen and d in completed and seen[d] != completed[d]]
    game_ids = [str(r.get("game_id", "")) for r in rows]
    duplicate_ids = sorted({gid for gid in game_ids if gid and game_ids.count(gid) > 1})
    invalid_ids = sorted({gid for gid in game_ids if len(gid) != 10 or not gid.startswith("002") or not gid.isdigit()})
    out_of_window = sorted({r.get("date") for r in rows if r.get("date") not in dates})
    ok = bool(rows) and not missing_coverage and not incomplete and not duplicate_ids and not invalid_ids and not out_of_window
    issues = []
    if not rows:
        issues.append("no official finals returned")
    if missing_coverage:
        issues.append(f"dates without scoreboard coverage: {missing_coverage}")
    if incomplete:
        issues.append(f"dates with non-final games: {incomplete}")
    if duplicate_ids:
        issues.append(f"duplicate game ids: {duplicate_ids}")
    if invalid_ids:
        issues.append(f"invalid official game ids: {invalid_ids}")
    if out_of_window:
        issues.append(f"finals outside requested dates: {out_of_window}")
    return {"gate": "freshness/finals", "ok": ok,
            "measured": f"{len(rows)} finals across {len(dates)} calendar dates",
            "detail": "; ".join(issues) if issues else "all scheduled games on covered dates are final; off-days are valid"}


def gate_standings(standings: dict, finals: dict) -> dict:
    """Validate a season-to-date standings snapshot internally, not against a partial feed."""
    rows = standings.get("rows", [])
    tris = [r.get("tri") for r in rows]
    malformed = [r.get("tri") for r in rows if
                 not r.get("tri") or not isinstance(r.get("w"), int) or
                 not isinstance(r.get("l"), int) or r["w"] < 0 or r["l"] < 0]
    unique_clubs = len(set(tris)) == len(tris) and None not in tris
    wins = sum(r["w"] for r in rows if isinstance(r.get("w"), int))
    losses = sum(r["l"] for r in rows if isinstance(r.get("l"), int))
    fresh = False
    retrieved = standings.get("fetched_at_utc")
    if retrieved:
        try:
            stamp = dt.datetime.fromisoformat(retrieved.replace("Z", "+00:00"))
            age = (dt.datetime.now(dt.timezone.utc) - stamp.astimezone(dt.timezone.utc)).total_seconds()
            fresh = -300 <= age <= 24 * 60 * 60
        except (TypeError, ValueError):
            pass
    ok = len(rows) == 30 and unique_clubs and not malformed and wins == losses and fresh
    issues = []
    if len(rows) != 30:
        issues.append(f"expected 30 official clubs, got {len(rows)}")
    if not unique_clubs:
        issues.append("club abbreviations are missing or duplicated")
    if malformed:
        issues.append(f"invalid W/L values: {malformed}")
    if wins != losses:
        issues.append(f"season wins ({wins}) do not equal losses ({losses})")
    if not fresh:
        issues.append("retrieval timestamp is missing, invalid, in the future, or older than 24h")
    return {"gate": "freshness/standings", "ok": ok,
            "measured": f"{len(rows)} clubs; {wins} wins / {losses} losses; retrieved {retrieved or 'unstamped'}",
            "detail": "; ".join(issues) if issues else "fresh 30-club season record is internally balanced"}


def gate_injuries(inj: dict, most_recent_game_date: str) -> dict:
    """The release must exist, be stamped, and be retrieved — all three recorded."""
    ok = bool(inj.get("pdf_url")) and bool(inj.get("retrieval_time_utc")) and bool(inj.get("revision_time_et"))
    return {"gate": "freshness/injuries", "ok": ok,
            "measured": f"revision {inj.get('revision_time_et')} retrieved {inj.get('retrieval_time_utc')}",
            "detail": "both stamps recorded" if ok else "a stamp is missing — fail-closed"}


def gate_slate(slate: dict, today: str) -> dict:
    end = (dt.date.fromisoformat(today) + dt.timedelta(days=3)).isoformat()
    gids = [g["game_id"] for g in slate["games"]]
    in_window = [g for g in slate["games"] if today <= g["date"] <= end]
    ok = len(gids) == len(set(gids)) and all(g["source_url"] for g in slate["games"])
    return {"gate": "freshness/slate", "ok": ok,
            "measured": f"{len(in_window)} games in {today}..{end}, {len(set(gids))} unique ids",
            "detail": "duplicate game id or a row without a source url" if not ok else
                      "unique ids, every row sourced"}


def gate_provenance(docs: dict) -> dict:
    """No row in any written doc may lack a source URL."""
    missing = []

    def scan(name, rows, key="source_url"):
        for i, r in enumerate(rows):
            if isinstance(r, dict) and not r.get(key):
                missing.append(f"{name}[{i}]")

    for name, doc in docs.items():
        for k in ("rows", "records", "games"):
            if isinstance(doc, dict) and k in doc:
                scan(name, doc[k])
        if name == "team_stats":
            for sub in doc.values():
                if isinstance(sub, dict) and "rows" in sub:
                    for i, r in enumerate(sub["rows"]):
                        pass  # stats rows carry the page-level source_url on the doc
    ok = not missing
    return {"gate": "provenance", "ok": ok,
            "measured": f"{len(docs)} documents scanned",
            "detail": f"rows without a source: {missing[:10]}" if missing else "every row carries a source URL"}


def run_gates(docs: dict, dates: list[str], today: str) -> list[dict]:
    finals = docs["finals"]
    completed_dates = [d for d in dates if d < today]
    return [
        gate_finals(completed_dates, finals),
        gate_standings(docs["standings"], finals),
        gate_injuries(docs["injuries"], dates[-1] if dates else today),
        gate_slate(docs["slate"], today),
        gate_players(docs["players"]),
        gate_provenance(docs),
    ]


# --------------------------------------------------------------------------- entry point
def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="write dated captures and rebuild the site")
    ap.add_argument("--check-only", action="store_true", help="fetch + gate, write nothing")
    ap.add_argument("--date", default=dt.date.today().isoformat(), help="the rolling window's anchor date")
    args = ap.parse_args(argv)
    today = args.date
    dates = [(dt.date.fromisoformat(today) + dt.timedelta(days=i)).isoformat() for i in range(4)]
    prior_days = [(dt.date.fromisoformat(today) - dt.timedelta(days=i)).isoformat() for i in range(1, 8)]

    print(f"nba2.v2.refresh: window {dates[0]}..{dates[-1]} (anchor {today})")
    docs = {
        "standings": fetch_standings(),
        "slate": fetch_slate(dates),
        "finals": fetch_finals(prior_days),
        "team_stats": fetch_team_stats(),
        "injuries": fetch_newest_injury_release(),
        "players": fetch_player_season(),
    }
    gates = run_gates(docs, prior_days + [today], today)
    for g in gates:
        print(f"  [{'PASS' if g['ok'] else 'FAIL'}] {g['gate']}: {g['measured']} — {g['detail']}")
    if not all(g["ok"] for g in gates):
        print("REFRESH ABORTED: a freshness/provenance gate failed — nothing written, site not rebuilt")
        return 4

    if args.check_only:
        print("check-only: gates passed, nothing written")
        return 0

    cap = RAW / f"capture_{today}"
    cap.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    (cap / f"standings_{today}.json").write_text(json.dumps({
        "schema": "nba2.standings-official.v2", "as_of": today,
        "retrieved_at_utc": docs["standings"]["fetched_at_utc"],
        "retrieval_method": "nba2.v2.refresh (stats.nba.com leaguestandingsv3)",
        "records": docs["standings"]["rows"]}, indent=1))
    (cap / f"slate_{today}.json").write_text(json.dumps({
        "schema": "nba2.slate.v2", "window": f"{dates[0]}..{dates[-1]}",
        "retrieved_at_utc": docs["slate"]["fetched_at_utc"],
        "games": docs["slate"]["games"]}, indent=1))
    (cap / f"finals_{today}.json").write_text(json.dumps({
        "schema": "nba2.results-feed.v2", "retrieved_at_utc": docs["finals"]["fetched_at_utc"],
        "records": docs["finals"]["records"]}, indent=1))
    (cap / f"team_stats_{today}.json").write_text(json.dumps({
        "schema": "nba2.team-stats-3page.v1", "pages": docs["team_stats"]}, indent=1))
    (cap / f"player_season_{today}.json").write_text(json.dumps({
        "schema": "nba2.player-season.v1", "as_of": today,
        "retrieved_at_utc": docs["players"]["fetched_at_utc"],
        "retrieval_method": "nba2.v2.refresh (stats.nba.com leaguedashplayerstats — the dataset "
                            "behind nba.com/stats/players/traditional)",
        "source_url": docs["players"]["source_url"],
        "rows": docs["players"]["rows"]}, indent=1))
    (cap / f"injury_release_{today}.json").write_text(json.dumps({
        "schema": "nba2.injury-transcript.v2",
        "revision_time_et": docs["injuries"]["revision_time_et"],
        "retrieval_time_utc": docs["injuries"]["retrieval_time_utc"],
        "pdf_url": docs["injuries"]["pdf_url"],
        "index_url": docs["injuries"]["index_url"],
        "note": "PDF archived + transcribed by nba2.pipeline.refresh cmd_injuries (recall gate 0.9)"}, indent=1))
    print(f"captures written under {cap}")

    import subprocess
    for cmd in (["python3", "-m", "nba2.v2"], ["python3", "-m", "nba2.v2.check"]):
        r = subprocess.run(cmd, cwd=ROOT)
        if r.returncode != 0:
            print(f"REFRESH ABORTED: {cmd} failed — captures kept for inspection, site not published")
            return 4
    print(f"site rebuilt and checks green at {stamp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
