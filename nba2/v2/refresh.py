"""Scheduled ingest for the rolling window: schedule, standings, team stats, injuries.

Runs in GitHub Actions (see ``.github/workflows/refresh.yml``). Every step is fail-closed:

* **fetch** the four official surfaces with retries and a real User-Agent (stats.nba.com
  rejects default agents), recording retrieval timestamps,
* **gate** before anything is written or the site is rebuilt:

  1. ``freshness/finals``   — every completed game through yesterday has an official final
  2. ``freshness/standings``— season-to-date standings rebuild exactly from committed history
      plus the fresh scoreboard finals (W/L per club)
  3. ``freshness/injuries`` — select the newest timestamped PDF link on the official index
      and require its revision and retrieval stamps (the gate does not yet compare recency
      against the last game date; see the audit finding)
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
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urljoin

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
}

INJURY_PDF_LINK_RE = re.compile(
    r'href=["\']([^"\']*Injury-Report_(\d{4}-\d{2}-\d{2})_(\d{2})_(\d{2})(AM|PM)\.pdf)["\']',
    re.IGNORECASE,
)


def newest_release_from_index(html: str) -> dict | None:
    """Choose the chronologically newest official injury PDF, independent of HTML order.

    The official index has historically rendered releases in ascending timestamp order.
    Taking ``links[0]`` (the earlier implementation) therefore selected the oldest report.
    Parse each filename's release stamp instead of assuming the page's presentation order.
    """
    candidates = []
    for match in INJURY_PDF_LINK_RE.finditer(html):
        raw_url, date_s, hour_s, minute_s, ampm = match.groups()
        try:
            stamp = dt.datetime.strptime(
                f"{date_s} {hour_s}:{minute_s} {ampm.upper()}",
                "%Y-%m-%d %I:%M %p",
            )
        except ValueError:
            continue
        candidates.append((stamp, urljoin(URLS["injury_index"], raw_url)))
    if not candidates:
        return None
    stamp, url = max(candidates, key=lambda item: item[0])
    return {
        "pdf_url": url,
        "revision_time_et": stamp.strftime("%Y-%m-%d %I:%M %p ET"),
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
    # A successful empty result is valid schedule coverage (the league can have an off
    # day); a missing date in this list means the source was not fetched. The same list is
    # published under both names: "covered_dates" is the merged-tree name, "checked_dates"
    # is the name the PR #80 gate fixtures use, and the gate reads either.
    covered_dates = []
    for d in dates:
        doc = http_json(URLS["scoreboard"].format(date=d))
        covered_dates.append(d)
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
            "covered_dates": covered_dates, "checked_dates": covered_dates,
            "games": games}


def fetch_finals(dates: list[str]) -> dict:
    """Official scoreboard rows for checked dates, plus verified-final rows.

    Keeping the scheduled-game/status inventory lets the freshness gate distinguish an
    official no-game date from a failed or incomplete scoreboard response. Current-day
    games are included when already final so the standings check can match the same live
    standings page; the gate only requires dates through yesterday to be complete.
    """
    recs = []
    scheduled_by_date = {}
    checked_dates = []
    games_seen_by_date = {}
    finals_by_date = {}
    for d in dates:
        doc = http_json(URLS["scoreboard"].format(date=d))
        checked_dates.append(d)
        headers = doc["resultSets"][0]["headers"]
        idx = {h: i for i, h in enumerate(headers)}
        day_games = []
        day_final_count = 0
        for g in doc["resultSets"][0]["rowSet"]:
            gid = str(g[idx["gameId"]]) if "gameId" in idx else ""
            raw_status = g[idx["gameStatus"]] if "gameStatus" in idx else None
            try:
                game_status = int(raw_status)
            except (TypeError, ValueError):
                game_status = None
            status_text = g[idx["gameStatusText"]] if "gameStatusText" in idx else ""
            day_games.append({"game_id": gid, "game_status": game_status,
                              "game_status_text": status_text})
            if game_status != 3:
                continue
            day_final_count += 1
            away = g[idx["awayTeamTricode"]]
            home = g[idx["homeTeamTricode"]]
            game_id = str(g[idx["gameId"]])
            recs.append({
                "date": d,
                "game_id": game_id,
                "home": home, "away": away,
                "home_pts": g[idx["homeTeamScore"]], "away_pts": g[idx["awayTeamScore"]],
                "source_url": f"https://www.nba.com/game/{(away + '-vs-' + home + '-' + game_id).lower()}",
            })
        scheduled_by_date[d] = day_games
        games_seen_by_date[d] = len(day_games)
        finals_by_date[d] = day_final_count
    return {"fetched_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "checked_dates": checked_dates,
            "scheduled_games_by_date": scheduled_by_date,
            "games_seen_by_date": games_seen_by_date,
            "finals_by_date": finals_by_date,
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
    """Parse the official index and choose the newest timestamped PDF link."""
    html = http_get(URLS["injury_index"]).decode("utf-8", "replace")
    release = newest_release_from_index(html)
    if not release:
        raise RuntimeError("no timestamped injury PDF links on the official index — refusing to guess")
    revision = release["revision_time_et"]
    return {"index_url": URLS["injury_index"], "pdf_url": release["pdf_url"],
            "retrieval_time_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "revision_time_et": revision}


# --------------------------------------------------------------------------- gates
def gate_finals(dates: list[str], finals: dict) -> dict:
    """Require checked scoreboard inventory and a verified final for every scheduled game.

    Empty inventories are valid off-days only when the date was actually checked. The
    detailed per-game inventory is preferred; the count-based schema remains supported
    for existing captures and fixtures, but records-only input fails closed.
    """
    issues = []
    records = finals.get("records", []) if isinstance(finals, dict) else []
    if not isinstance(records, list):
        records = []
        issues.append("final records are not a list")

    scheduled = finals.get("scheduled_games_by_date") if isinstance(finals, dict) else None
    checked_value = finals.get("checked_dates") if isinstance(finals, dict) else None
    checked = {d for d in checked_value if isinstance(d, str)} if isinstance(checked_value, (list, tuple, set)) else set()
    if (not checked and isinstance(finals, dict)
            and isinstance(finals.get("games_seen_by_date"), dict)
            and isinstance(finals.get("finals_by_date"), dict)):
        checked = set(finals["games_seen_by_date"]) & set(finals["finals_by_date"])
    unchecked = [d for d in dates if d not in checked]
    malformed_finals = []
    duplicate_finals = []
    final_ids_by_date = {}

    # Full per-game status inventory from the official scoreboard.
    if scheduled is not None:
        record_ids = set()
        for i, record in enumerate(records):
            normalised = _normalise_final_record(record)
            if normalised is None or normalised["date"] is None or not normalised["game_id"]:
                game_id = record.get("game_id", record.get("gameId", "unknown")) if isinstance(record, dict) else "unknown"
                malformed_finals.append(f"record {i} ({game_id}): missing date, teams, or valid final scores")
                continue
            gid = normalised["game_id"]
            if gid in record_ids:
                duplicate_finals.append(gid)
            record_ids.add(gid)
            final_ids_by_date.setdefault(normalised["date"], set()).add(gid)

        missing_inventory = [d for d in dates if not isinstance(scheduled, dict) or d not in scheduled]
        if not isinstance(scheduled, dict):
            scheduled = {}
        pending = []
        malformed_inventory = []
        scheduled_count = 0
        expected_final_ids = {}
        for d in dates:
            day_games = scheduled.get(d)
            if not isinstance(day_games, list):
                if d not in missing_inventory:
                    missing_inventory.append(d)
                continue
            day_ids = set()
            day_final_ids = set()
            for i, game in enumerate(day_games):
                if not isinstance(game, dict):
                    malformed_inventory.append(f"{d}[{i}] is not a game object")
                    continue
                gid = str(game.get("game_id") or "")
                status = game.get("game_status")
                status_text = game.get("game_status_text") or status or "unknown"
                is_final = str(status).strip() == "3"
                if not gid:
                    malformed_inventory.append(f"{d}[{i}] has no game id")
                    continue
                if gid in day_ids:
                    malformed_inventory.append(f"{d} has duplicate scheduled game id {gid}")
                day_ids.add(gid)
                scheduled_count += 1
                if is_final:
                    day_final_ids.add(gid)
                    if gid not in final_ids_by_date.get(d, set()):
                        pending.append(f"{d}/{gid} (status {status_text}; final record missing)")
                else:
                    pending.append(f"{d}/{gid} (status {status_text})")
            expected_final_ids[d] = day_final_ids

        orphaned = []
        for d in dates:
            extras = final_ids_by_date.get(d, set()) - expected_final_ids.get(d, set())
            orphaned.extend(f"{d}/{gid}" for gid in sorted(extras))
        if orphaned:
            issues.append(f"final records absent from final scoreboard inventory: {orphaned[:12]}")
        if unchecked:
            issues.append(f"scoreboard dates not checked: {unchecked}")
        if missing_inventory:
            issues.append(f"scoreboard game inventory missing for dates: {sorted(set(missing_inventory))}")
        if malformed_inventory:
            issues.append(f"malformed scoreboard inventory: {malformed_inventory[:8]}")
        if malformed_finals:
            issues.append(f"malformed final records: {malformed_finals[:8]}")
        if duplicate_finals:
            issues.append(f"duplicate final game ids: {sorted(set(duplicate_finals))}")
        if pending:
            issues.append(f"scheduled games without verified finals: {pending[:12]}")
        measured = f"{len(records)} finals / {scheduled_count} scheduled games over {len(dates)} checked dates"

    # Existing official captures record checked dates and per-date totals rather than each
    # game's status. They can still distinguish a checked off-day from missing coverage.
    elif (isinstance(finals, dict) and isinstance(finals.get("games_seen_by_date"), dict)
          and isinstance(finals.get("finals_by_date"), dict)):
        seen_by_date = finals["games_seen_by_date"]
        finals_by_date = finals["finals_by_date"]
        missing_inventory = [d for d in dates if d not in seen_by_date or d not in finals_by_date]
        invalid_counts = []
        incomplete = []
        for d in dates:
            if d in missing_inventory:
                continue
            seen, final_count = seen_by_date[d], finals_by_date[d]
            if (not isinstance(seen, int) or isinstance(seen, bool) or seen < 0
                    or not isinstance(final_count, int) or isinstance(final_count, bool) or final_count < 0):
                invalid_counts.append(d)
            elif seen != final_count:
                incomplete.append(d)
        record_counts = {d: 0 for d in dates}
        count_ids = set()
        out_of_window = []
        for i, record in enumerate(records):
            if not isinstance(record, dict) or not record.get("date") or not record.get("game_id"):
                malformed_finals.append(f"record {i}: missing date or game id")
                continue
            d, gid = str(record["date"]), str(record["game_id"])
            if d not in record_counts:
                out_of_window.append(f"{d}/{gid}")
                continue
            if gid in count_ids:
                duplicate_finals.append(gid)
            count_ids.add(gid)
            record_counts[d] += 1
        count_mismatches = [d for d in dates if d not in missing_inventory
                            and isinstance(finals_by_date[d], int)
                            and record_counts[d] != finals_by_date[d]]
        if unchecked:
            issues.append(f"scoreboard dates not checked: {unchecked}")
        if missing_inventory:
            issues.append(f"scoreboard game inventory missing for dates: {missing_inventory}")
        if invalid_counts:
            issues.append(f"invalid scoreboard game counts for dates: {invalid_counts}")
        if incomplete:
            issues.append(f"dates with scheduled but unfinished games: {incomplete}")
        if count_mismatches:
            issues.append(f"final record counts do not match scoreboard totals: {count_mismatches}")
        if out_of_window:
            issues.append(f"finals outside requested dates: {out_of_window[:8]}")
        if malformed_finals:
            issues.append(f"malformed final records: {malformed_finals[:8]}")
        if duplicate_finals:
            issues.append(f"duplicate final game ids: {sorted(set(duplicate_finals))}")
        measured = f"{len(records)} finals over {len(dates)} checked dates"

    else:
        issues.append("scoreboard game inventory missing; records-only input cannot prove off-days or completeness")
        measured = f"{len(records)} finals over {len(dates)} requested dates"

    ok = not issues
    if ok:
        issues.append("all scheduled games through yesterday are final; off-days are valid")
    return {"gate": "freshness/finals", "ok": ok,
            "measured": measured,
            "detail": "; ".join(issues)}


def _normalise_final_record(record: dict, default_date: str | None = None) -> dict | None:
    """Return the minimal comparable shape used for season-record reconstruction."""
    if not isinstance(record, dict):
        return None
    gid = record.get("game_id") or record.get("gameId")
    home = record.get("home") or record.get("home_team") or record.get("homeTeamTricode")
    away = record.get("away") or record.get("away_team") or record.get("awayTeamTricode")
    home_pts = record.get("home_pts", record.get("homeTeamScore"))
    away_pts = record.get("away_pts", record.get("awayTeamScore"))
    date = record.get("date") or default_date
    if not gid or not home or not away or home_pts is None or away_pts is None:
        return None
    try:
        home_pts, away_pts = int(home_pts), int(away_pts)
    except (TypeError, ValueError):
        return None
    return {
        "game_id": str(gid), "date": str(date) if date else None,
        "home": str(home), "away": str(away),
        "home_pts": home_pts, "away_pts": away_pts,
        "source_url": (record.get("source_url") or record.get("source") or
                       record.get("list_url") or record.get("game_url")),
    }


def merge_final_records(*record_groups: list[dict]) -> tuple[list[dict], list[str]]:
    """Deduplicate official finals by game ID and surface conflicting duplicate rows."""
    by_id = {}
    conflicts = []
    identity = ("date", "home", "away", "home_pts", "away_pts")
    for group in record_groups:
        for raw in group or []:
            record = _normalise_final_record(raw)
            if record is None:
                continue
            gid = record["game_id"]
            prior = by_id.get(gid)
            if prior is not None:
                differing = [key for key in identity
                             if prior.get(key) is not None and record.get(key) is not None
                             and prior[key] != record[key]]
                if differing:
                    conflicts.append(f"{gid}: {', '.join(differing)} disagree")
                # Keep the newer group's values when equal, while retaining any source
                # metadata the current record lacks.
                by_id[gid] = {**prior, **{k: v for k, v in record.items() if v is not None}}
            else:
                by_id[gid] = record
    return [by_id[k] for k in sorted(by_id)], conflicts


def load_committed_final_records() -> list[dict]:
    """Load the existing official result history as the baseline for live standings.

    The refresh fetches only a rolling week of scoreboard data; comparing that partial
    slice directly with season-to-date standings is invalid. The committed history and
    dated result snapshots are the baseline, and the just-fetched finals are overlaid by
    ``gate_standings``. Duplicate IDs are removed before any W/L arithmetic.
    """
    paths = set(HISTORY.glob("games_*.json"))
    paths.update(RAW.rglob("results_*.json"))
    paths.update(p for p in RAW.rglob("finals_*.json") if p.name != "finals_all.json")
    records = []
    for path in sorted(paths):
        try:
            doc = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"cannot load committed result snapshot {path}: {exc}") from exc
        if not isinstance(doc, dict):
            raise RuntimeError(f"committed result snapshot is not an object: {path}")
        default_date = doc.get("date")
        for key in ("games", "records"):
            if key not in doc:
                continue
            rows = doc[key]
            if not isinstance(rows, list):
                raise RuntimeError(f"committed result snapshot {path} has non-list {key}")
            for i, row in enumerate(rows):
                normalised = _normalise_final_record(row, default_date)
                if normalised is not None:
                    records.append(normalised)
                elif key == "games" or not isinstance(doc.get("games"), list):
                    raise RuntimeError(f"committed result snapshot {path} has malformed {key}[{i}]")
    merged, conflicts = merge_final_records(records)
    if conflicts:
        raise RuntimeError("committed official result snapshots conflict: " + "; ".join(conflicts[:8]))
    return merged


def _fresh_retrieval_stamp(value) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        stamp = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            return False
        age = (dt.datetime.now(dt.timezone.utc) - stamp.astimezone(dt.timezone.utc)).total_seconds()
        return -300 <= age <= 24 * 60 * 60
    except (TypeError, ValueError):
        return False


def _gate_standings_snapshot(standings: dict) -> dict:
    """Validate a live standings snapshot when no historical finals baseline is supplied."""
    rows = standings.get("rows", []) if isinstance(standings, dict) else []
    issues = []
    if not isinstance(rows, list):
        rows = []
        issues.append("standings rows are not a list")
    seen = set()
    wins = losses = 0
    malformed = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            malformed.append(f"row {i} is not an object")
            continue
        tri, w, l = row.get("tri"), row.get("w"), row.get("l")
        if not isinstance(tri, str) or not tri:
            malformed.append(f"row {i} has no club abbreviation")
        elif tri in seen:
            malformed.append(f"{tri}: duplicate standings row")
        else:
            seen.add(tri)
        if (not isinstance(w, int) or isinstance(w, bool) or w < 0
                or not isinstance(l, int) or isinstance(l, bool) or l < 0):
            malformed.append(f"row {i} has invalid W/L values")
        else:
            wins += w
            losses += l
    if len(rows) != 30 or len(seen) != 30:
        issues.append(f"expected 30 unique team standings rows, got {len(seen)}")
    if malformed:
        issues.append(f"invalid standings rows: {malformed[:8]}")
    if wins != losses:
        issues.append(f"season wins ({wins}) do not equal losses ({losses})")
    retrieved = standings.get("fetched_at_utc") if isinstance(standings, dict) else None
    if not _fresh_retrieval_stamp(retrieved):
        issues.append("retrieval timestamp is missing, invalid, in the future, or older than 24h")
    if not issues:
        issues.append("fresh 30-club season record is internally balanced")
    ok = len(issues) == 1 and issues[0] == "fresh 30-club season record is internally balanced"
    return {"gate": "freshness/standings", "ok": ok,
            "measured": f"{len(rows)} clubs; {wins} wins / {losses} losses; retrieved {retrieved or 'unstamped'}",
            "detail": "; ".join(issues)}


def gate_standings(standings: dict, finals: dict, baseline_records: list[dict] | None = None,
                   require_all_30: bool = False) -> dict:
    """Rebuild season-to-date W/L from baseline + fresh finals and compare all rows.

    Calls without a baseline preserve the independent-snapshot validation contract used by
    older fixture callers. The scheduled live refresh always passes its committed baseline,
    so a missing baseline cannot silently downgrade the operational comparison.
    """
    if baseline_records is None:
        return _gate_standings_snapshot(standings)

    malformed_records = []
    if not isinstance(baseline_records, list):
        malformed_records.append("baseline is not a list")
        baseline_records = []
    fresh_records = finals.get("records", []) if isinstance(finals, dict) else []
    if not isinstance(fresh_records, list):
        malformed_records.append("fresh results are not a list")
        fresh_records = []
    for label, group in (("baseline", baseline_records), ("fresh", fresh_records)):
        for i, record in enumerate(group):
            normalised = _normalise_final_record(record)
            if normalised is None or normalised["date"] is None:
                malformed_records.append(f"{label} record {i}")
    records, conflicts = merge_final_records(baseline_records, fresh_records)
    w, l = {}, {}
    arithmetic_errors = []
    if not records:
        arithmetic_errors.append("no official final records available to rebuild standings")
    for r in records:
        if r["home_pts"] == r["away_pts"]:
            arithmetic_errors.append(f"{r['game_id']}: tied final score")
            continue
        hw = r["home_pts"] > r["away_pts"]
        win, lose = (r["home"], r["away"]) if hw else (r["away"], r["home"])
        w[win] = w.get(win, 0) + 1
        l[lose] = l.get(lose, 0) + 1

    bad = []
    seen = set()
    standings_rows = standings.get("rows", []) if isinstance(standings, dict) else []
    if not isinstance(standings_rows, list):
        standings_rows = []
        bad.append("standings rows are not a list")
    for i, row in enumerate(standings_rows):
        if not isinstance(row, dict):
            bad.append(f"standings row {i} is not an object")
            continue
        tri, row_wins, row_losses = row.get("tri"), row.get("w"), row.get("l")
        if not isinstance(tri, str) or not tri:
            bad.append(f"team {row.get('team', 'unknown')}: missing tricode")
            continue
        if tri in seen:
            bad.append(f"{tri}: duplicate standings row")
            continue
        seen.add(tri)
        if (not isinstance(row_wins, int) or isinstance(row_wins, bool) or row_wins < 0
                or not isinstance(row_losses, int) or isinstance(row_losses, bool) or row_losses < 0):
            bad.append(f"{tri}: invalid W/L values")
            continue
        if (w.get(tri, 0), l.get(tri, 0)) != (row_wins, row_losses):
            bad.append(tri)
    if require_all_30 and len(seen) != 30:
        bad.append(f"expected 30 unique team standings rows, got {len(seen)}")
    unknown_teams = sorted((set(w) | set(l)) - seen)
    if unknown_teams:
        bad.append(f"final-feed teams absent from standings: {unknown_teams}")
    if sum(w.values()) != len(records) or sum(l.values()) != len(records):
        arithmetic_errors.append("rebuilt wins/losses do not equal unique final count")
    if require_all_30 and not _fresh_retrieval_stamp(standings.get("fetched_at_utc")):
        bad.append("standings retrieval timestamp is missing, invalid, in the future, or older than 24h")

    ok = not bad and not conflicts and not arithmetic_errors and not malformed_records
    details = []
    if bad:
        details.append(f"rows that do not rebuild from finals: {bad}")
    if malformed_records:
        details.append(f"malformed baseline/fresh final records: {malformed_records[:8]}")
    if conflicts:
        details.append(f"conflicting duplicate finals: {conflicts[:8]}")
    if arithmetic_errors:
        details.append(f"final-feed arithmetic errors: {arithmetic_errors[:8]}")
    if not details:
        details.append("every season-to-date row rebuilds exactly from unique official finals")
    return {"gate": "freshness/standings", "ok": ok,
            "measured": f"{len(standings_rows)} rows vs {len(records)} unique season finals",
            "detail": "; ".join(details)}


def gate_injuries(inj: dict, _most_recent_game_date: str) -> dict:
    """Require report provenance stamps; recency against the game date is not enforced."""
    ok = bool(inj.get("pdf_url")) and bool(inj.get("retrieval_time_utc")) and bool(inj.get("revision_time_et"))
    return {"gate": "freshness/injuries", "ok": ok,
            "measured": f"revision {inj.get('revision_time_et')} retrieved {inj.get('retrieval_time_utc')}",
            "detail": ("report link and both stamps recorded; game-date recency not checked" if ok
                       else "a stamp is missing — fail-closed")}


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

    # Accept either key name: "covered_dates" (merged tree) or "checked_dates" (PR #80
    # fixtures). Both mean "this date was actually queried against the official API".
    covered = (slate.get("covered_dates") or slate.get("checked_dates") or []) \
        if isinstance(slate, dict) else []
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
            for page, sub in doc.items():
                if not isinstance(sub, dict) or "rows" not in sub:
                    continue
                # The NBA stats endpoint returns positional arrays; the official page URL
                # is therefore stored at the page-document level, not repeated per cell.
                if not sub.get("source_url"):
                    missing.append(f"team_stats.{page}.source_url")
    ok = not missing
    return {"gate": "provenance", "ok": ok,
            "measured": f"{len(docs)} documents scanned",
            "detail": f"rows without a source: {missing[:10]}" if missing else "every row carries a source URL"}


def run_gates(docs: dict, dates: list[str], today: str) -> list[dict]:
    """Evaluate only prior-day completion against the live rolling standings feed."""
    finals = docs["finals"]
    baseline = docs.get("baseline_finals", {}).get("records", [])
    completed_dates = [d for d in dates if d < today]
    most_recent_completed = max(completed_dates) if completed_dates else today
    return [
        gate_finals(completed_dates, finals),
        gate_standings(docs["standings"], finals, baseline, require_all_30=True),
        gate_injuries(docs["injuries"], most_recent_completed),
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
        "standings": fetch_standings(),
        "slate": fetch_slate(dates),
        # Include completed games from today in the season-to-date standings comparison,
        # but only require dates through yesterday to be complete.
        "finals": fetch_finals(prior_days + [today]),
        "baseline_finals": {"records": load_committed_final_records()},
        "team_stats": fetch_team_stats(),
        "injuries": fetch_newest_injury_release(),
    }
    gates = run_gates(docs, prior_days, today)
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
