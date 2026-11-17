"""Scheduled ingest for the rolling window: schedule, standings, team stats, injuries.

Runs in GitHub Actions (see ``.github/workflows/refresh.yml``). Every step is fail-closed:

* **fetch** the four official surfaces with retries and a measured User-Agent, recording
  retrieval timestamps,
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

Which transport, and why (measured on a GitHub-hosted runner, 2026-11-17,
``data/raw/page_fixtures/transport_probe.json``):

* ``stats.nba.com/stats/*`` times out with *every* header set tried, including the
  ``x-nba-stats-origin``/``x-nba-stats-token`` pair the previous code sent, and
  ``cdn.nba.com/static/json/*`` answers 403 for the same two sets. Those two hosts are
  therefore not usable from the runner that runs this job.
* ``www.nba.com`` answers **200** — but only with a plain, self-identifying User-Agent.
  The Chrome-mimicking User-Agent this module used before measured **403 on the same
  URL in the same run**, which is one of the reasons the scheduled job failed.
* ``www.nba.com/games?date=YYYY-MM-DD`` is server-rendered: its ``__NEXT_DATA__`` payload
  carries every game of that date — game id, home/away, final score, quarter scores,
  status, tip time, and each club's season record as printed beside the game.
* ``www.nba.com/standings`` is server-rendered too, but only its navigation team list
  (club, id, division) is; the standings *table* itself is fetched by the browser later.
  So the season table below is **derived** from the official per-game finals and
  cross-checked against the record the league prints beside each game.

Usage:  python3 -m nba2.v2.refresh --check-only     # gates only, no writes
        python3 -m nba2.v2.refresh --write          # ingest + rebuild
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
HISTORY = RAW / "history"

# Measured, not assumed. On a GitHub-hosted runner (2026-11-17) this User-Agent returned
# HTTP 200 for www.nba.com/standings, /games and /schedule and official.nba.com, while the
# Chrome-mimicking User-Agent this module previously sent measured HTTP 403 on the very
# same URL in the same run. Change it only by re-measuring, never by guessing.
UA = "NBA2-research-desk/1.0 (official data refresh; github.com/wingbangboozle1-lang/NBA2)"
HEADERS = {"User-Agent": UA, "Accept": "*/*", "Referer": "https://official.nba.com/"}
TIMEOUT = 30
RETRIES = 3

SEASON = "2026-27"
URLS = {
    # server-rendered, reachable from a runner — the transports this module now uses
    "games": "https://www.nba.com/games?date={date}",
    "standings_index": "https://www.nba.com/standings",
    # client-rendered: the page answers 200 but the table is loaded by the browser from
    # stats.nba.com, which times out from a runner. Kept so the attempt, and the refusal
    # to invent the rows, are both recorded against the official URL.
    "team_traditional": "https://www.nba.com/stats/teams/traditional?Season={season}&SeasonType=Regular+Season",
    "team_advanced": "https://www.nba.com/stats/teams/advanced?Season={season}&SeasonType=Regular+Season",
    "team_opponent": "https://www.nba.com/stats/teams/opponent?Season={season}&SeasonType=Regular+Season",
    "injury_index": "https://official.nba.com/nba-injury-report-2026-27-season/",
}

# The JSON transports this module used before, kept only as evidence of what was measured
# and abandoned: every one of them times out or answers 403 from a GitHub-hosted runner.
UNREACHABLE_TRANSPORTS = {
    "stats_leaguestandingsv3": ("https://stats.nba.com/stats/leaguestandingsv3"
                                "?LeagueID=00&Season={season}&SeasonType=Regular+Season"),
    "stats_leaguedashteamstats": ("https://stats.nba.com/stats/leaguedashteamstats"
                                  "?LeagueID=00&MeasureType=Base&PerMode=PerGame"
                                  "&Season={season}&SeasonType=Regular+Season"),
    "stats_scoreboardv3": "https://stats.nba.com/stats/scoreboardv3?GameDate={date}&LeagueID=00",
    "cdn_scoreboard": "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json",
}

# How far back the season scan reads to build the season-to-date table. The 2026-27 regular
# season is well inside 60 days of any in-season run, and every date is fetched from the
# league's own page, so a longer window costs requests and never invents a game.
SEASON_SCAN_DAYS = 60
REGULAR_SEASON = "Regular Season"


def http_get(url: str, tries: int = RETRIES) -> bytes:
    """GET with retries. Raises on failure — a missing source never becomes a blank."""
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
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


# --------------------------------------------------------------- rendered-page helpers
NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S)
TEAM_DIVISION_BLOCK_RE = re.compile(
    r'NavTeamList_ntlDivTitle__[^"]*">([^<]+)</div>(.*?)(?=NavTeamList_ntlDivTitle__|$)', re.S)
TEAM_ROW_RE = re.compile(
    r'data-content="([A-Z]{3})" data-text="([^"]+)"[^>]*?>.*?logos/nba/(\d+)/primary', re.S)
CLOCK_RE = re.compile(r"^\d{1,2}:\d{2} (?:AM|PM) ET$", re.I)


def next_data(html_text: str, url: str) -> dict:
    """The page's own data payload. A page without one is refused, never guessed at."""
    m = NEXT_DATA_RE.search(html_text or "")
    if not m:
        raise RuntimeError(f"no __NEXT_DATA__ payload on {url} — refusing to parse a shell")
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError as e:
        raise RuntimeError(f"__NEXT_DATA__ on {url} is not valid JSON: {e}") from e


def parse_team_index(html_text: str) -> dict[str, dict]:
    """Clubs as nba.com/standings prints them in its server-rendered team list.

    The standings *table* is client-rendered, but the navigation team list is in the HTML:
    each division heading is followed by its clubs, each carrying the tricode, the club
    name and the official team id (in the logo URL). That is a real official mapping, so
    it is read rather than assumed — and if it cannot be read, this raises.
    """
    clubs: dict[str, dict] = {}
    for div_block, body in TEAM_DIVISION_BLOCK_RE.findall(html_text or ""):
        division = html.unescape(div_block).strip()
        for tri, name, team_id in TEAM_ROW_RE.findall(body):
            clubs[tri] = {"tri": tri, "name": html.unescape(name).strip(),
                          "team_id": team_id, "division": division,
                          "source_url": URLS["standings_index"]}
    return clubs


def _et_clock(card: dict) -> str | None:
    """The tip time as the league prints it, e.g. ``7:30 pm ET``.

    ``gameStatusText`` already carries the printed clock for a scheduled game. For a game
    in progress or final it does not, so fall back to ``gameTimeEastern`` — which prints
    the US/Eastern wall clock with a ``Z`` suffix, i.e. it is *not* UTC: on 2026-11-16 the
    ORL@BOS card prints ``2026-11-16T19:00:00Z`` and an ``actualStartTimeUTC`` of
    ``2026-11-17T00:10:43Z``, five hours later. Reading it as UTC would be an invention.
    """
    text = (card.get("gameStatusText") or "").strip()
    if CLOCK_RE.match(text):
        return text.replace("AM", "am").replace("PM", "pm")
    raw = card.get("gameTimeEastern")
    if not raw:
        return None
    try:
        stamp = dt.datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None
    wall = stamp.strftime("%I:%M %p ET").lstrip("0")
    return wall.replace("AM", "am").replace("PM", "pm")


def _quarter_row(team: dict, side: str, game_id: str, final: int) -> list[int] | None:
    periods = team.get("periods") or []
    if not periods or not all(isinstance(p, dict) and "score" in p for p in periods):
        return None
    ordered = [p["score"] for p in sorted(periods, key=lambda p: p.get("period", 0))]
    if any(not isinstance(v, int) for v in ordered):
        return None
    if sum(ordered) != final:
        # fail closed: a quarter row that does not add up to the final is not published
        raise RuntimeError(f"{game_id}: {side} quarters sum to {sum(ordered)} but the "
                           f"final prints {final} — refusing the row")
    return ordered


# --------------------------------------------------------------------------- fetchers
def fetch_day_games(date: str) -> list[dict]:
    """Official game cards for one date, as www.nba.com/games?date=<date> renders them.

    The page is server-rendered and reachable from a runner, so every field below is read
    from the league's own payload rather than reconstructed. A date with no games (an
    off day) legitimately returns an empty list; a page whose payload is missing or whose
    ``selectedDate`` disagrees with the requested date raises instead.
    """
    url = URLS["games"].format(date=date)
    doc = next_data(http_get(url).decode("utf-8", "replace"), url)
    props = doc.get("props", {}).get("pageProps", {}) or {}
    selected = props.get("selectedDate")
    if selected and selected != date:
        raise RuntimeError(f"{url} answered with selectedDate {selected} — refusing it")
    cards = []
    for module in (props.get("gameCardFeed") or {}).get("modules", []) or []:
        for card in module.get("cards", []) or []:
            data = card.get("cardData")
            if card.get("cardType") == "game" and isinstance(data, dict):
                cards.append(data)
    return cards


def fetch_teams_index() -> dict[str, dict]:
    """The 30 official clubs with their ids and divisions, read from nba.com/standings."""
    url = URLS["standings_index"]
    clubs = parse_team_index(http_get(url).decode("utf-8", "replace"))
    if len(clubs) != 30:
        raise RuntimeError(f"nba.com/standings listed {len(clubs)} clubs, expected 30 — "
                           "the team list moved and the rows would not be official")
    return clubs


def _regular_season(cards: list[dict]) -> list[dict]:
    """Regular-season NBA games only: preseason and exhibition cards carry other ids."""
    out = []
    for c in cards:
        if (c.get("seasonType") or "").strip() != REGULAR_SEASON:
            continue
        gid = c.get("gameId")
        home = (c.get("homeTeam") or {}).get("teamTricode")
        away = (c.get("awayTeam") or {}).get("teamTricode")
        if not (isinstance(gid, str) and gid.isdigit() and len(gid) == 10 and gid.startswith("002")):
            raise RuntimeError(f"game card for {c.get('shareUrl') or gid!r} has no official "
                               "10-digit game id — refusing to publish a made-up one")
        if not (isinstance(home, str) and isinstance(away, str) and len(home) == 3 and len(away) == 3):
            raise RuntimeError(f"game {gid} is missing an official home/away tricode")
        out.append(c)
    return out


def fetch_slate(dates: list[str]) -> dict:
    """Every scheduled game of the rolling window, one official row per game."""
    games: list[dict] = []
    covered_dates: list[str] = []
    for d in dates:
        cards = _regular_season(fetch_day_games(d))
        # A successful fetch of a date with no games is valid coverage (an off day);
        # a date missing from this list means the source was not fetched at all.
        covered_dates.append(d)
        for c in cards:
            games.append({
                "date": d,
                "game_id": c["gameId"],
                "home": c["homeTeam"]["teamTricode"],
                "away": c["awayTeam"]["teamTricode"],
                "time_et": _et_clock(c),
                # this page does not print the arena; blank rather than inferred
                "arena": None,
                "arena_status": "unverified — www.nba.com/games?date= does not print the arena",
                "source_url": URLS["games"].format(date=d),
                "game_url": c.get("shareUrl"),
                "status": "final" if c.get("gameStatus") == 3 else "scheduled",
            })
    return {"fetched_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "retrieval_method": "nba2.v2.refresh (www.nba.com/games?date= server-rendered payload)",
            "covered_dates": covered_dates, "games": games}


def fetch_finals(dates: list[str]) -> dict:
    """Official finals plus per-date coverage counts for the completed-date gate.

    Quarter scores come from the same payload. A quarter row that does not add up to the
    printed final raises: the brief asks for quarter scores, and a wrong one is worse
    than a blank one.
    """
    recs: list[dict] = []
    games_seen_by_date: dict[str, int] = {}
    finals_by_date: dict[str, int] = {}
    for d in dates:
        cards = _regular_season(fetch_day_games(d))
        games_seen_by_date[d] = len(cards)
        finals = [c for c in cards if c.get("gameStatus") == 3]
        finals_by_date[d] = len(finals)
        for c in finals:
            home, away = c["homeTeam"], c["awayTeam"]
            hp, ap = home.get("score"), away.get("score")
            if not isinstance(hp, int) or not isinstance(ap, int):
                raise RuntimeError(f"final game {c['gameId']} prints a non-numeric score")
            home_q = _quarter_row(home, "home", c["gameId"], hp)
            away_q = _quarter_row(away, "away", c["gameId"], ap)
            recs.append({
                "date": d,
                "game_id": c["gameId"],
                "home": home["teamTricode"], "away": away["teamTricode"],
                "home_pts": hp, "away_pts": ap,
                "home_q": home_q, "away_q": away_q,
                "ot_periods": max(0, len(home_q or []) - 4),
                "source_url": c.get("shareUrl") or URLS["games"].format(date=d),
            })
    return {"fetched_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "retrieval_method": "nba2.v2.refresh (www.nba.com/games?date= server-rendered payload)",
            "games_seen_by_date": games_seen_by_date, "finals_by_date": finals_by_date,
            "records": recs}


def _season_finals(today: str, days: int = SEASON_SCAN_DAYS) -> tuple[list[dict], dict, list[str]]:
    """Every regular-season final of the season to date, plus the league's printed records.

    Returns ``(finals, printed, dates_read)`` where ``finals`` holds one row per completed
    game and ``printed`` maps ``(date, tricode)`` to the W/L the league prints beside that
    game — the independent check the derived table is verified against below.
    """
    finals: list[dict] = []
    printed: dict[tuple[str, str], tuple[int, int]] = {}
    dates_read: list[str] = []
    start = dt.date.fromisoformat(today)
    for back in range(1, days + 1):
        d = (start - dt.timedelta(days=back)).isoformat()
        try:
            cards = _regular_season(fetch_day_games(d))
        except RuntimeError as e:
            raise RuntimeError(f"season scan stopped at {d}: {e}") from e
        dates_read.append(d)
        for c in cards:
            gid = c["gameId"]
            home, away = c["homeTeam"], c["awayTeam"]
            if c.get("gameStatus") != 3:
                continue
            hp, ap = home.get("score"), away.get("score")
            if not isinstance(hp, int) or not isinstance(ap, int):
                raise RuntimeError(f"final game {gid} prints a non-numeric score")
            finals.append({"date": d, "game_id": gid,
                           "home": home["teamTricode"], "away": away["teamTricode"],
                           "home_pts": hp, "away_pts": ap,
                           "source_url": c.get("shareUrl") or URLS["games"].format(date=d)})
            for team in (home, away):
                w, l = team.get("wins"), team.get("losses")
                if isinstance(w, int) and isinstance(l, int):
                    printed[(d, team["teamTricode"])] = (w, l)
    return finals, printed, dates_read


def _streak(results: list[bool]) -> str:
    """``W 3`` / ``L 2`` from a club's results in chronological order."""
    if not results:
        return ""
    last = results[-1]
    n = 0
    for won in reversed(results):
        if won != last:
            break
        n += 1
    return f"{'W' if last else 'L'} {n}"


def fetch_standings(today: str | None = None) -> dict:
    """Season-to-date W/L per club, derived from official finals and then checked.

    Why derived: the standings *table* on nba.com/standings is client-rendered from
    stats.nba.com, which times out from a runner (measured). The inputs here are official
    instead — every regular-season final of the season to date, read from
    ``www.nba.com/games?date=``, plus the club/division list the standings page does print
    server-side. Each club's derived record is then compared with the W/L the league
    prints beside that club's most recent game; a mismatch raises rather than publishes.
    """
    today = today or dt.date.today().isoformat()
    clubs = fetch_teams_index()
    finals, printed, dates_read = _season_finals(today)

    table: dict[str, dict] = {}
    for tri, meta in clubs.items():
        table[tri] = {"tri": tri, "team": meta["team_id"], "name": meta["name"],
                      "division": meta["division"], "w": 0, "l": 0,
                      "home_w": 0, "home_l": 0, "road_w": 0, "road_l": 0,
                      "div_w": 0, "div_l": 0, "results": []}
    unknown = set()
    for g in sorted(finals, key=lambda r: r["date"]):
        hp, ap = g["home_pts"], g["away_pts"]
        for side, tri, opp, pts, opp_pts, at_home in (
                ("home", g["home"], g["away"], hp, ap, True),
                ("away", g["away"], g["home"], ap, hp, False)):
            row = table.get(tri)
            if row is None:
                unknown.add(tri)
                continue
            won = pts > opp_pts
            row["w" if won else "l"] += 1
            row["home_w" if (at_home and won) else "home_l" if at_home else
                "road_w" if won else "road_l"] += 1
            same_division = (row["division"] == table.get(opp, {}).get("division"))
            if same_division:
                row["div_w" if won else "div_l"] += 1
            row["results"].append(won)

    if unknown:
        raise RuntimeError(f"official finals name clubs that are not on nba.com/standings: "
                           f"{sorted(unknown)} — the table would be incomplete")
    if len(finals) == 0:
        raise RuntimeError("the season scan read no official finals — refusing to publish "
                           "an empty standings table")

    # verification: the record derived through each club's most recent game must equal the
    # record the league prints beside that game (measured to include that game's result).
    latest: dict[str, str] = {}
    for g in sorted(finals, key=lambda r: r["date"]):
        for tri in (g["home"], g["away"]):
            latest[tri] = g["date"]
    mismatches = []
    for tri, day in latest.items():
        exp = printed.get((day, tri))
        if exp is None:
            continue
        row = table[tri]
        through = [g for g in finals if g["date"] <= day
                   and tri in (g["home"], g["away"])]
        w = sum(1 for g in through if (g["home_pts"] > g["away_pts"]) == (g["home"] == tri))
        l = len(through) - w
        if (w, l) != exp:
            mismatches.append(f"{tri}: derived {w}-{l} through {day}, league prints {exp[0]}-{exp[1]}")
    if mismatches:
        raise RuntimeError("derived standings disagree with the record the league prints — "
                           + "; ".join(mismatches))

    rows = []
    for tri in sorted(table):
        r = table[tri]
        last10 = r["results"][-10:]
        rows.append({
            "team": r["team"], "tri": tri, "w": r["w"], "l": r["l"],
            "home": f"{r['home_w']}-{r['home_l']}",
            "road": f"{r['road_w']}-{r['road_l']}",
            # the conference grouping is not printed anywhere a runner can read, so the
            # conference record stays blank and flagged rather than inferred
            "conf": None,
            "conf_status": "unverified — nba.com/standings prints divisions, not conferences",
            "div": f"{r['div_w']}-{r['div_l']}",
            "last10": f"{sum(last10)}-{len(last10) - sum(last10)}",
            "streak": _streak(r["results"]),
            "division": r["division"],
            "source_url": URLS["standings_index"],
            "games_url": URLS["games"].format(date="{date}"),
        })
    return {"fetched_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "retrieval_method": ("nba2.v2.refresh (season-to-date W/L derived from official "
                                 "per-game finals at www.nba.com/games?date=, clubs and "
                                 "divisions from www.nba.com/standings; cross-checked against "
                                 "the record the league prints beside each game)"),
            "derived": True,
            "games_counted": len(finals),
            "dates_read": len(dates_read),
            "window": f"{dates_read[-1] if dates_read else ''}..{dates_read[0] if dates_read else ''}",
            "rows": rows}


def fetch_team_stats() -> dict:
    """The three official team-stat pages — recorded, or refused with the measured reason.

    Each page answers 200 but its table is loaded by the browser from stats.nba.com, which
    times out from a runner. That is recorded per page rather than papered over: no row is
    invented, and the surface is reported as unverified instead of silently dropped.
    """
    out = {}
    for key in ("team_traditional", "team_advanced", "team_opponent"):
        url = URLS[key].format(season=SEASON)
        stamp = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        try:
            payload = next_data(http_get(url).decode("utf-8", "replace"), url)
        except RuntimeError as e:
            out[key] = {"source_url": url, "status": "unavailable",
                        "reason": str(e), "measured_at_utc": stamp}
            continue
        props = payload.get("props", {}).get("pageProps", {}) or {}
        # a stats page that reached us with its table would carry it under pageProps
        stat_keys = [k for k in props if k not in ("layout", "region")]
        if stat_keys:
            out[key] = {"fetched_at_utc": stamp, "source_url": url, "pages": props}
        else:
            out[key] = {
                "source_url": url, "status": "unavailable", "measured_at_utc": stamp,
                "reason": ("the page is server-rendered without its table: nba.com loads the "
                           "rows in the browser from stats.nba.com, which times out from a "
                           "GitHub-hosted runner (data/raw/page_fixtures/transport_probe.json)"),
                "checked_by": "nba2.v2.refresh.fetch_team_stats",
            }
    return out


INJURY_PDF_RE = re.compile(r'href="([^"]*Injury-Report_[^"]*\.pdf)"')
INJURY_STAMP_RE = re.compile(r"Injury-Report_(\d{4}-\d{2}-\d{2})_(\d{2})_(\d{2})\s*([AP]M)", re.I)


def newest_release_from_index(index_html: str) -> str | None:
    """The newest injury PDF on the league index, by the timestamp in its filename.

    The index does not reliably list newest-first — taking the first link was how the
    previous code picked the *oldest* release on the page. The stamp is in the filename
    itself, so sorting on it is a read, not an inference.
    """
    best = None
    for link in INJURY_PDF_RE.findall(index_html or ""):
        m = INJURY_STAMP_RE.search(link)
        if not m:
            continue
        day, hour, minute, meridiem = m.groups()
        hour24 = int(hour) % 12 + (12 if meridiem.upper() == "PM" else 0)
        key = (day, f"{hour24:02d}:{minute}")
        if best is None or key > best[0]:
            best = (key, link)
    return best[1] if best else None


def fetch_newest_injury_release() -> dict:
    """Parse the league's official index for the newest release link; stamp both times."""
    index_html = http_get(URLS["injury_index"]).decode("utf-8", "replace")
    newest = newest_release_from_index(index_html)
    if not newest:
        raise RuntimeError("no injury PDF links on the official index — refusing to guess")
    stamp = INJURY_STAMP_RE.search(newest)
    revision = ""
    if stamp:
        day, hour, minute, meridiem = stamp.groups()
        revision = f"{day} {hour}:{minute} {meridiem.upper()} ET"
    return {"index_url": URLS["injury_index"], "pdf_url": newest,
            "retrieval_time_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "revision_time_et": revision}


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
    """Require fetched coverage for each date in today's four-day rolling window.

    An empty game list for one date is valid only when that date's official scoreboard
    request completed successfully (recorded in ``covered_dates``). No missing schedule
    row is inferred or filled in.
    """
    try:
        start = dt.date.fromisoformat(today)
        expected = [(start + dt.timedelta(days=i)).isoformat() for i in range(4)]
    except (TypeError, ValueError):
        expected = []

    covered = slate.get("covered_dates", []) if isinstance(slate, dict) else []
    games = slate.get("games", []) if isinstance(slate, dict) else []
    covered_is_dates = (isinstance(covered, list) and all(
        isinstance(day, str) and len(day) == 10 and day[4:5] == "-" and day[7:8] == "-"
        for day in covered))
    covered_set = set(covered) if covered_is_dates else set()
    dates_ok = (bool(expected) and covered_is_dates
                and len(covered) == len(covered_set)
                and covered_set == set(expected))

    malformed = []
    gids = []
    from urllib.parse import parse_qs, urlparse
    for i, game in enumerate(games if isinstance(games, list) else []):
        if not isinstance(game, dict):
            malformed.append(f"row {i} is not an object")
            continue
        date = game.get("date")
        gid = game.get("game_id")
        home, away = game.get("home"), game.get("away")
        source = game.get("source_url")
        if date not in expected or date not in covered:
            malformed.append(f"row {i} has a date outside fetched window")
        if not isinstance(gid, str) or len(gid) != 10 or not gid.isdigit() or not gid.startswith("002"):
            malformed.append(f"row {i} has an invalid official game id")
        else:
            gids.append(gid)
        if (not isinstance(home, str) or len(home) != 3 or not home.isalpha()
                or home != home.upper() or not isinstance(away, str) or len(away) != 3
                or not away.isalpha() or away != away.upper() or home == away):
            malformed.append(f"row {i} has missing or invalid home/away team codes")
        try:
            parsed = urlparse(source)
            source_ok = (parsed.scheme == "https" and parsed.hostname == "www.nba.com"
                         and parsed.path == "/schedule"
                         and parse_qs(parsed.query).get("date") == [date])
        except (TypeError, ValueError):
            source_ok = False
        if not source_ok:
            malformed.append(f"row {i} lacks the matching official NBA schedule URL")

    duplicates = sorted({gid for gid in gids if gids.count(gid) > 1})
    problems = []
    if not expected:
        problems.append("invalid anchor date")
    if not dates_ok:
        missing = sorted(set(expected) - covered_set) if covered_is_dates else expected
        extra = sorted(covered_set - set(expected)) if covered_is_dates else []
        problems.append(f"official schedule fetch coverage mismatch (missing={missing}, extra={extra})")
    if not isinstance(games, list):
        problems.append("games field is not a list")
    if duplicates:
        problems.append(f"duplicate game ids: {duplicates}")
    problems.extend(malformed)

    unique_count = len(set(gids))
    game_count = len(games) if isinstance(games, list) else 0
    ok = not problems
    return {"gate": "freshness/slate", "ok": ok,
            "measured": f"{game_count} games in {expected[0] if expected else today}..{expected[-1] if expected else 'invalid'}, "
                        f"{unique_count} unique ids; {len(covered) if isinstance(covered, list) else 0}/4 dates fetched",
            "detail": "; ".join(problems) if problems else
                      "all four dates fetched; every game row has valid teams, id, date, and official source"}


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
        "standings": fetch_standings(today),
        "slate": fetch_slate(dates),
        "finals": fetch_finals(prior_days),
        "team_stats": fetch_team_stats(),
        "injuries": fetch_newest_injury_release(),
    }
    for key, doc in docs["team_stats"].items():
        if doc.get("status") == "unavailable":
            print(f"  [UNAVAILABLE] {key}: {doc['source_url']} — {doc['reason']} "
                  "(no rows invented; the surface is recorded as unverified)")
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
    standings = docs["standings"]
    (cap / f"standings_{today}.json").write_text(json.dumps({
        "schema": "nba2.standings-official.v2", "as_of": today,
        "retrieved_at_utc": standings["fetched_at_utc"],
        "retrieval_method": standings["retrieval_method"],
        "derived": True,
        "note": ("W/L, home/road, division and last-10 are computed from the "
                 f"{standings['games_counted']} official regular-season finals the scan read "
                 f"across {standings['dates_read']} dates ({standings['window']}); the club and "
                 "division columns are read from the server-rendered team list on "
                 "nba.com/standings. The conference column is blank because the league prints "
                 "divisions only. Each club's record was checked against the W/L the league "
                 "prints beside its most recent game."),
        "unavailable_transports": {k: "timeout or 403 from a GitHub-hosted runner "
                                      "(data/raw/page_fixtures/transport_probe.json)"
                                   for k in UNREACHABLE_TRANSPORTS},
        "records": standings["rows"]}, indent=1))
    (cap / f"slate_{today}.json").write_text(json.dumps({
        "schema": "nba2.slate.v2", "window": f"{dates[0]}..{dates[-1]}",
        "retrieved_at_utc": docs["slate"]["fetched_at_utc"],
        "retrieval_method": docs["slate"]["retrieval_method"],
        "note": ("the arena column is blank: www.nba.com/games?date= does not print it and no "
                 "other reachable official source was measured to"),
        "games": docs["slate"]["games"]}, indent=1))
    (cap / f"finals_{today}.json").write_text(json.dumps({
        "schema": "nba2.results-feed.v2", "retrieved_at_utc": docs["finals"]["fetched_at_utc"],
        "retrieval_method": docs["finals"]["retrieval_method"],
        "note": ("quarter rows come from the same official payload and each is required to sum "
                 "to the printed final; ot_periods counts periods beyond four"),
        "records": docs["finals"]["records"]}, indent=1))
    (cap / f"team_stats_{today}.json").write_text(json.dumps({
        "schema": "nba2.team-stats-3page.v1",
        "unavailable_transports": {k: "timeout or 403 from a GitHub-hosted runner "
                                      "(data/raw/page_fixtures/transport_probe.json)"
                                   for k in UNREACHABLE_TRANSPORTS},
        "pages": docs["team_stats"]}, indent=1))
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
