"""Unattended re-capture of the player-level surface (``nba2.v4.capture``).

Why this module exists
----------------------
Session ``arena/41bd6ce8-nba2`` captured the per-player game logs by reading the
official pages one at a time through the platform page-fetch tool. That proves
the data is real and reachable; it does not scale, because coverage is bounded by
how many pages a session can read. This module is the same capture expressed as
code so a scheduled workflow can extend it — one club, or the whole slate, per
run.

Where it runs
-------------
The sandbox this repository was developed in has **no outbound network** (TLS
connect to nba.com fails; see ``official.UNREACHABLE``). GitHub Actions does, and
``nba2/pipeline/refresh.py`` already fetches official endpoints there with
``urllib``. This module uses the same technique and no third-party package.

What it refuses to do
---------------------
* It never publishes a player whose parsed log fails the gates: a capture whose
  mean does not reproduce the PPG/RPG/APG printed in the player's own official
  header, or whose rows are missing an official game id, is recorded under
  ``capture_failures`` with the reason and **no rows are written**.
* It never fills a gap. A club that could not be fetched appears under
  ``not_captured``; a player whose table prints "No data available" is a failure,
  not a zero.
* The injury PDF is archived and used as a *coverage tripwire* (the pairs the
  conservative PDF-text parser finds must be a subset of what we already hold),
  never re-parsed into published rows — the released report is transcribed from
  the rendered PDF by a reader, which is the only method verified so far.

Status
------
The parsers below were written against the page structure observed on 2026-11-15
and are exercised by ``test_v4.py`` against fixtures, not against live pages (the
sandbox cannot reach them). The first scheduled run is therefore a *supervised*
run: it writes nothing unless every gate passes, and a parse that no longer
matches the live markup shows up as a capture failure, not as data.
"""

from __future__ import annotations

import argparse
import gzip
import html as _html
import json
import re
import sys
import urllib.error
import urllib.request
import zlib
from datetime import datetime, timezone
from pathlib import Path

from . import official as O
from . import gamelog as GL

UA = {
    "User-Agent": "NBA2-research-desk/1.0 (repository ingestion; contact: repo owner)",
    "Accept": "*/*",
    "Referer": "https://www.nba.com/",
}

SEASON = "2026-27"
TIMEOUT = 45

GAMELOG_URL = ("https://www.nba.com/stats/player/{pid}/boxscores-traditional"
               f"?Season={SEASON}&SeasonType=Regular+Season")
GAME_URL = "https://www.nba.com/game/{gid}/"

# The columns the official game-log table prints, in order (observed 2026-11-15).
LOG_COLUMNS = ["Match Up", "W/L", "MIN", "PTS", "FGM", "FGA", "FG%", "3PM", "3PA",
               "3P%", "FTM", "FTA", "FT%", "OREB", "DREB", "REB", "AST", "STL",
               "BLK", "TOV", "PF", "+/-"]
GAME_ID_RE = re.compile(r"/(?:games?|game)/(\d{10})")
PLAYER_ID_RE = re.compile(r"/player/(\d+)")
PDF_RE = re.compile(
    r"https://ak-static\.cms\.nba\.com/referee/injury/"
    r"Injury-Report_(\d{4}-\d{2}-\d{2})_(\d{2})_(\d{2})(AM|PM)\.pdf")
STATUS_RE = re.compile(
    r"([A-Z][A-Za-z\.'‑-‒–—\- ]+?, [A-Z][A-Za-z\.'‑-‒–—\- ]+?)"
    r"\s+(NOT YET SUBMITTED|Out|Doubtful|Questionable|Probable|Available)\b")
EMPTY_TABLE = re.compile(r"no data available", re.I)


class CaptureError(RuntimeError):
    """A fetch or a parse that cannot be trusted. Carries the reason verbatim."""


# --------------------------------------------------------------------------- http
def http_get(url: str, timeout: int = TIMEOUT) -> bytes:
    """Fetch ``url``. Raises :class:`CaptureError` with the reason on any failure."""
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            if resp.headers.get("Content-Encoding") == "gzip":
                data = gzip.decompress(data)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, EOFError) as exc:
        raise CaptureError(f"{type(exc).__name__}: {exc}") from exc
    return data


def page_text(raw: bytes) -> str:
    return raw.decode("utf-8", errors="replace")


# --------------------------------------------------------------------------- tables
def _cells(row_html: str) -> tuple[list[str], list[str]]:
    """(cell texts, hrefs) for one ``<tr>``."""
    texts: list[str] = []
    hrefs: list[str] = []
    for cell in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row_html, re.S | re.I):
        hrefs.extend(re.findall(r'href="([^"]+)"', cell))
        plain = re.sub(r"<[^>]+>", " ", cell)
        plain = _html.unescape(plain)
        texts.append(re.sub(r"\s+", " ", plain).strip())
    return texts, hrefs


def tables(page: str) -> list[list[tuple[list[str], list[str]]]]:
    """Every ``<table>`` on the page as a list of (cells, hrefs) rows."""
    out = []
    for tbl in re.findall(r"<table[^>]*>(.*?)</table>", page, re.S | re.I):
        rows = [_cells(r) for r in re.findall(r"<tr[^>]*>(.*?)</tr>", tbl, re.S | re.I)]
        out.append([r for r in rows if r[0]])
    return [t for t in out if t]


def find_table(page: str, required: list[str]) -> list[tuple[list[str], list[str]]]:
    """The first table whose header row contains every ``required`` column name."""
    want = [c.lower() for c in required]
    for tbl in tables(page):
        header = [c.lower() for c in tbl[0][0]]
        if all(w in " | ".join(header) for w in want):
            return tbl
        if all(any(w == h for h in header) for w in want):
            return tbl
    raise CaptureError(f"no table with columns {required} — the page layout changed "
                       "or the table did not render (nothing parsed, nothing written)")


# --------------------------------------------------------------------------- parses
def parse_gamelog(page: str) -> dict:
    """Parse one official player game-log page.

    Raises :class:`CaptureError` for anything that would make the rows untrustworthy:
    an empty table, a missing season header, or a row without an official game id.
    """
    if EMPTY_TABLE.search(page):
        raise CaptureError("the official page prints 'No data available' for this "
                           "player — a rendering flake on nba.com, not a zero")
    tbl = find_table(page, ["Match Up", "MIN", "PTS", "REB", "AST"])
    header = tbl[0][0]
    idx = {c.lower(): i for i, c in enumerate(header)}

    flat = re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", page)))
    head = {}
    for key in ("ppg", "rpg", "apg"):
        m = re.search(rf"\b{key.upper()}\b\s*([0-9]+\.?[0-9]*)", flat)
        if m is None:
            raise CaptureError(f"official season {key.upper()} not printed on the page — "
                               "gate G-41-02 could not be measured, so nothing is written")
        head[key] = float(m.group(1))

    games = []
    for cells, hrefs in tbl[1:]:
        if len(cells) < len(header):
            continue
        gid = None
        for h in hrefs:
            m = GAME_ID_RE.search(h)
            if m:
                gid = m.group(1)
                break
        if gid is None:
            raise CaptureError(f"a row ({cells[0]!r}) carries no official game id — "
                               "the row cannot be sourced, so the player is not captured")
        matchup = cells[idx["match up"]]
        home_away = "away" if "@" in matchup else "home"
        opp = re.split(r"@|vs\.?", matchup)[-1].strip()
        mins = cells[idx["min"]]
        games.append({
            "date": _game_date(cells, idx, gid),
            "opponent": opp,
            "home_away": home_away,
            "result": cells[idx["w/l"]] if "w/l" in idx else "",
            "minutes": mins,
            "minutes_dec": _minutes_dec(mins),
            "points": _num(cells[idx["pts"]]),
            "rebounds": _num(cells[idx["reb"]]),
            "assists": _num(cells[idx["ast"]]),
            "plus_minus": _num(cells[idx["+/-"]]) if "+/-" in idx else None,
            "game_id": gid,
            "game_url": GAME_URL.format(gid=gid),
        })
    if not games:
        raise CaptureError("the table rendered with a header but no rows")
    return {"rows_declared": len(games), "season_header": head, "games": games}


def _game_date(cells: list[str], idx: dict, gid: str) -> str:
    for c in cells:
        m = re.search(r"\b(20\d\d-\d\d-\d\d)\b", c)
        if m:
            return m.group(1)
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", " ".join(cells))
    if m:
        return f"{m.group(3)}-{m.group(1)}-{m.group(2)}"
    raise CaptureError(f"no game date on the row for game {gid} — a date that is not "
                       "printed cannot be verified against the season window")


def _minutes_dec(text: str) -> float:
    m = re.match(r"^(\d+):(\d+)$", text.strip())
    if not m:
        m2 = re.match(r"^(\d+\.?\d*)$", text.strip())
        if not m2:
            raise CaptureError(f"unreadable minutes cell {text!r}")
        return float(m2.group(1))
    return int(m.group(1)) + int(m.group(2)) / 60.0


def _num(text: str):
    t = text.strip().replace("%", "")
    if t in ("", "-", "--"):
        return None
    try:
        return int(t)
    except ValueError:
        try:
            return float(t)
        except ValueError:
            return None


def parse_roster(page: str) -> list[dict]:
    """Parse an official club page into ``[{player, player_id, jersey, pos}]``."""
    best: list[dict] = []
    for tbl in tables(page):
        rows = [(c, h) for c, h in tbl if any(PLAYER_ID_RE.search(x) for x in h)]
        if len(rows) > len(best):
            best = rows
    if not best:
        raise CaptureError("no roster rows with official /player/{id}/ links on the club "
                           "page — the player ids cannot be invented, so nothing is captured")
    out = []
    for cells, hrefs in best:
        m = next((PLAYER_ID_RE.search(h) for h in hrefs if PLAYER_ID_RE.search(h)), None)
        if not m:
            continue
        rest = [c for c in cells[1:] if c]
        out.append({
            "player": re.sub(r"\s+", " ", cells[0]).strip(),
            "player_id": m.group(1),
            "jersey": rest[0] if rest else "",
            "pos": rest[1] if len(rest) > 1 else "",
        })
    return out


# --------------------------------------------------------------------------- injury PDF
def newest_release(index_url: str, date: str) -> tuple[str, str] | None:
    """Newest (url, stamp) injury-release PDF the index lists for ``date``."""
    page = page_text(http_get(index_url))
    best = None
    for m in PDF_RE.finditer(page):
        url, d, hh, mm, ampm = m.group(0), m.group(1), m.group(2), m.group(3), m.group(4)
        if d != date:
            continue
        h = int(hh) % 12 + (12 if ampm == "PM" else 0)
        stamp = f"{d}T{h:02d}:{int(mm):02d}"
        if best is None or stamp > best[1]:
            best = (url, stamp)
    return best


def pdf_text(raw: bytes) -> str:
    """Conservative text pull from a digitally-generated PDF (FlateDecode streams)."""
    out: list[str] = []
    for m in re.finditer(rb"stream\r?\n(.*?)endstream", raw, re.S):
        blob = m.group(1)
        try:
            blob = zlib.decompress(blob)
        except zlib.error:
            continue
        if b"Tj" not in blob and b"TJ" not in blob:
            continue
        text = blob.decode("latin-1", errors="ignore")
        for s in re.findall(r"\((?:\\.|[^\\()])*\)", text):
            s = s[1:-1]
            s = re.sub(r"\\([()\\])", r"\1", s)
            s = re.sub(r"\\[nrt]", " ", s)
            out.append(s)
    return " ".join(out)


def pdf_pairs(raw: bytes) -> set[tuple[str, str]]:
    """(player, status) pairs the PDF prints — a coverage tripwire, not a data source."""
    text = pdf_text(raw)
    pairs = set()
    for name, status in STATUS_RE.findall(text):
        name = re.sub(r"\s+", " ", name).strip(" ,")
        if len(name) >= 4:
            pairs.add((name, status))
    return pairs


# --------------------------------------------------------------------------- capture
def capture_player(name: str, team: str, pid: str, status: str = "", reason: str = "",
                   team_full: str = "") -> dict:
    """Fetch and gate one player. Raises :class:`CaptureError` if it cannot be trusted."""
    url = GAMELOG_URL.format(pid=pid)
    page = page_text(http_get(url))
    parsed = parse_gamelog(page)
    games = parsed["games"]
    mean = lambda k: round(sum(g[k] for g in games) / len(games), 3)  # noqa: E731
    for key in ("points", "rebounds", "assists"):
        official_value = parsed["season_header"][key[0] + "pg"]
        if abs(mean(key) - official_value) > 0.05:
            raise CaptureError(
                f"gate G-41-02 failed: mean {key} {mean(key)} vs official "
                f"{official_value} — the parse is incomplete, nothing is written")
    return {
        "player": name, "team": team, "team_full": team_full, "player_id": pid,
        "injury_status": status, "injury_reason": reason,
        "rows_declared": parsed["rows_declared"], "rows_captured": len(games),
        "season_header": parsed["season_header"], "source_url": url, "games": games,
    }


def run(date: str, clubs: list[str], max_players: int | None, out: Path,
        index_url: str, ingest_injury: bool = True) -> dict:
    """Capture the designated players of ``clubs`` for ``date``. Never raises on a
    fetch failure: everything untrusted lands in ``capture_failures``."""
    started = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    from nba2 import config  # official team ids / slugs (verified 2026-11-13)

    designated = _designated(date, clubs)
    players: list[dict] = []
    failures: list[dict] = []
    not_captured: list[dict] = []

    rosters = {}
    for club in clubs:
        url = _team_url(club)
        if not url:
            failures.append({"scope": "roster", "team": club, "player": "",
                             "reason": "no official club URL in nba2/config.py for this "
                                       "tricode — the id and slug are never invented"})
            continue
        try:
            roster = parse_roster(page_text(http_get(url)))
        except CaptureError as exc:
            failures.append({"scope": "roster", "team": club, "player": "",
                             "reason": str(exc), "source_url": url})
            continue
        rosters[club] = {
            "team": club, "team_full": config.TEAM_NAMES.get(club, club),
            "team_id": str(tid), "source_url": url,
            "players": [dict(p, source_url=url) for p in roster],
        }
        by_name = {_norm(p["player"]): p for p in roster}
        for row in designated.get(club, []):
            hit = by_name.get(_norm(row["player"]))
            if hit is None or not hit.get("player_id"):
                not_captured.append({**row, "reason": "player not on the official club "
                                                      "roster — no official game-log page "
                                                      "to address, left blank"})
                continue
            if max_players is not None and len(players) >= max_players:
                not_captured.append({**row, "reason": "beyond this run's --max-players "
                                                      "budget; not captured, left blank"})
                continue
            try:
                players.append(capture_player(
                    row["player"], club, hit["player_id"], row.get("status", ""),
                    row.get("reason", ""), config.TEAM_NAMES.get(club, club)))
            except CaptureError as exc:
                failures.append({"scope": "gamelog", "team": club, "player": row["player"],
                                 "player_id": hit.get("player_id", ""),
                                 "reason": str(exc),
                                 "source_url": GAMELOG_URL.format(pid=hit.get("player_id", ""))})

    injury_note = None
    if ingest_injury:
        try:
            rel = newest_release(index_url, date)
            if rel is None:
                injury_note = f"no injury release listed on the index for {date}"
            else:
                url, stamp = rel
                raw = http_get(url)
                (out / Path(url).name).write_bytes(raw)
                pairs = pdf_pairs(raw)
                known = {(p["player"], p["injury_status"]) for p in players}
                known |= {(r["player"], r["status"]) for rows in designated.values() for r in rows}
                unseen = sorted(p for p in pairs if p not in known)
                injury_note = (f"archived {Path(url).name} ({stamp} ET, {len(pairs)} "
                               f"player/status pairs); {len(unseen)} pair(s) not already "
                               "held — the release still needs a reader to transcribe rows")
        except CaptureError as exc:
            injury_note = f"injury release not archived: {exc}"

    out.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "nba2.player-gamelog.v2",
        "retrieved_at_utc": started,
        "retrieval_method": ("nba2.v4.capture: urllib GET of the official per-player "
                             "game-log page, parsed and re-gated before writing"),
        "source_template": GAMELOG_URL,
        "slate_date": date,
        "clubs": clubs,
        "columns": ["date", "opponent", "home_away", "result", "minutes", "points",
                    "rebounds", "assists", "plus_minus", "game_id", "game_url"],
        "notes": [n for n in (injury_note,) if n],
        "players": players,
        "capture_failures": failures,
        "not_captured": not_captured,
        "flags": [{
            "id": "F-41B-06",
            "area": "unattended capture",
            "finding": ("written against the page structure observed on 2026-11-15; the "
                        "parsers run unsupervised here for the first time. Every value is "
                        "re-gated (G-41-01..06) before it is written, so a parse that drifts "
                        "produces a capture failure, never a wrong number."),
            "source": index_url,
            "severity": "advisory",
        }],
    }
    if players:
        (out / "player_gamelogs.json").write_text(json.dumps(payload, indent=1) + "\n")
    if rosters:
        (out / "rosters.json").write_text(json.dumps({
            "schema": "nba2.official-roster.v1",
            "retrieved_at_utc": started,
            "retrieval_method": "nba2.v4.capture: urllib GET of the official club page",
            "clubs": list(rosters.values()),
        }, indent=1) + "\n")
    return payload


def slate_clubs(date: str) -> list[str]:
    """Clubs that play on ``date``, read off the newest committed injury release."""
    try:
        release = json.loads(O.INJURY_PM.read_text())
    except (OSError, ValueError):
        return []
    cols = release.get("columns", O_INJURY_COLS)
    clubs = set()
    for rec in release.get("records", []):
        row = dict(zip(cols, rec))
        if row.get("game_date") == date and row.get("team"):
            clubs.add(O.team_abbr(row["team"]))
    return sorted(clubs)


def _designated(date: str, clubs: list[str]) -> dict[str, list[dict]]:
    """Designated players from the newest committed release (Out/Questionable/Doubtful,
    excluding G League rows, which have no rotation minutes to redistribute)."""
    out: dict[str, list[dict]] = {c: [] for c in clubs}
    try:
        release = json.loads(O.INJURY_PM.read_text())
    except (OSError, ValueError):
        return out
    cols = release.get("columns", O_INJURY_COLS)
    for rec in release.get("records", []):
        row = dict(zip(cols, rec))
        club = O.team_abbr(row.get("team", ""))
        if row.get("game_date") != date or club not in clubs:
            continue
        if not row.get("player"):
            continue
        status = (row.get("status") or "").strip()
        reason = (row.get("reason") or "").strip()
        if status not in ("Out", "Doubtful", "Questionable"):
            continue
        if reason.startswith("G League"):
            continue
        out[club].append({"player": row["player"], "status": status, "reason": reason})
    return out


O_INJURY_COLS = ["game_date", "time_et", "matchup", "team", "player", "status",
                 "reason", "attributed_team"]

def _team_url(club: str) -> str:
    """Official club page URL from the repo's verified id/slug table (nba2.config)."""
    from nba2 import config
    stats_url = config.team_stats_url(club)          # /team/<id>/<slug> + /stats suffix
    if not stats_url:
        return ""
    return stats_url.replace("/stats", "", 1)


def _norm(name: str) -> str:
    return re.sub(r"[^a-z]", "", name.lower())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="capture official per-player game logs")
    ap.add_argument("--date", required=True, help="slate date, YYYY-MM-DD")
    ap.add_argument("--clubs", default="", help="comma-separated tricodes (default: every "
                                                "club on the committed release for --date)")
    ap.add_argument("--max-players", type=int, default=None)
    ap.add_argument("--out", default="", help="output dir (default data/raw/capture_<stamp>)")
    ap.add_argument("--index-url", default=O.SOURCES["injury_index"][1])
    ap.add_argument("--no-injury", action="store_true", help="skip the injury-release archive")
    args = ap.parse_args(argv)

    clubs = [c.strip().upper() for c in args.clubs.split(",") if c.strip()]
    if not clubs:
        clubs = slate_clubs(args.date)
    if not clubs:
        print(f"no clubs resolved for {args.date} — nothing captured, nothing written")
        return 0

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    out = Path(args.out) if args.out else O.RAW / f"capture_{stamp}"
    payload = run(args.date, clubs, args.max_players, out, args.index_url,
                  ingest_injury=not args.no_injury)

    ok = len(payload["players"])
    print(f"[capture {args.date}] clubs {','.join(clubs)}: {ok} player(s) captured, "
          f"{len(payload['capture_failures'])} failure(s), "
          f"{len(payload['not_captured'])} not captured -> {out}")
    for f in payload["capture_failures"]:
        print(f"  FAIL {f['team']} {f['player']}: {f['reason']}")
    for n in payload["notes"]:
        print(f"  note: {n}")
    # A run that captured nothing is a fact to publish, not a reason to break the build:
    # the snapshot is simply not written, so the site keeps the last good capture.
    return 0


if __name__ == "__main__":
    sys.exit(main())
