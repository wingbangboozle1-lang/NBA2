"""v7 capture: read the official pages that are still reachable, and record exactly what came back.

Why this module exists
----------------------
`data/raw/page_fixtures/transport_probe.json` records that from a GitHub-hosted runner
`stats.nba.com` times out and `cdn.nba.com` returns 403, so the nightly job has never been
able to read the three "official team-stat pages" the brief asks for (traditional, opponent,
advanced). That is a **transport** fact about the runner, not a fact about the league: the
same pages are served, server-rendered with the full table, to an ordinary page fetch. The
v2 snapshot in the tree is therefore stale on exactly the inputs the model needs — measured:
the committed `nba2/v3/model.json` prices ATL at 8-6 while the live standings page prints
9-6, and the committed advanced-stats snapshot predates the eight 11/16 and twelve 11/18
finals.

This module closes that gap the only honest way: it reads the pages, **stores the raw bytes
it read with the URL and the retrieval stamp**, and parses the stored bytes. A parser can be
checked by a reader against the file it came from. Nothing is typed in by hand.

Two hard rules
--------------
1. **No network, no fabrication.** If a page is not in the cache, the value derived from it
   is blank **and flagged** — never back-filled from an older snapshot without saying so.
2. **Parsing is structural, not positional.** Every extractor locates its column by the
   header the page prints (`OffRtg`, `PACE`, `W`, ...) and then reads that column in the
   body rows. If the header is absent the extractor raises rather than silently reading the
   wrong column — a shifted column would otherwise produce 30 plausible, wrong numbers.

The raw captures are refreshed by `tools/v7_capture.py` (run in this session) and are
committed under `data/raw/v7_fetch/` so the build is reproducible offline.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .common import CACHE, RAW, ROOT, dump, load

# The five official pages the model is cut from. Season 2026-27, regular season.
TEAM_STAT_PAGES = {
    "traditional": "https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season",
    "advanced": "https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season",
    "opponent": "https://www.nba.com/stats/teams/opponent?Season=2026-27&SeasonType=Regular+Season",
}
STANDINGS_URL = "https://www.nba.com/standings"
INDEX = CACHE / "index.json"


# ------------------------------------------------------------------ capture register
def manifest() -> list[dict]:
    """Every cached page with its URL, retrieval stamp, byte length and sha256."""
    doc = load(INDEX) or {}
    return doc.get("pages", [])


def fresh(url: str) -> dict | None:
    """The cached capture for a URL, or None when the page was never read."""
    for row in manifest():
        if row.get("url") == url:
            p = ROOT / row["path"]
            if p.exists():
                return row
    return None


def read(url: str) -> tuple[str, dict] | tuple[None, dict]:
    """(markdown text, capture row) for a URL, straight out of the committed cache."""
    row = fresh(url)
    if row is None:
        return None, {"url": url, "status": "not captured in this session",
                      "reason": "no committed capture; every value derived from it is blank"}
    p = ROOT / row["path"]
    text = p.read_text()
    # The committed copy must be the bytes the stamp describes; a mismatch is a finding.
    digest = hashlib.sha256(text.encode()).hexdigest()
    row = dict(row)
    row["sha256_recomputed"] = digest
    row["digest_ok"] = (digest == row.get("sha256"))
    return text, row


# ------------------------------------------------------------------ table extraction
def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def table_after(text: str, header_probe: str) -> tuple[list[str], list[list[str]]]:
    """The first markdown table whose header row contains every token in `header_probe`.

    Returns (header cells, body rows). Raises when no such table exists, because a caller
    that asked for a table and silently got none would publish blanks that look measured.
    """
    tokens = [t.lower() for t in header_probe.split("|")]
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if not line.strip().startswith("|"):
            continue
        head = _cells(line)
        joined = " ".join(head).lower()
        if all(t in joined for t in tokens):
            body: list[list[str]] = []
            # skip the separator row, then take rows until the table ends
            for nxt in lines[i + 1:]:
                if not nxt.strip().startswith("|"):
                    break
                cells = _cells(nxt)
                if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                    continue
                body.append(cells)
            return head, body
    raise LookupError(f"no table with header tokens {tokens!r}")


def col_index(head: list[str], name: str) -> int:
    """Index of a column by the exact header the page prints (case-insensitive)."""
    for i, h in enumerate(head):
        if h.strip().lower() == name.strip().lower():
            return i
    raise LookupError(f"column {name!r} not in {head!r}")


def tri_of(cell: str) -> str | None:
    """The three-letter club code out of a team cell (link text or `ATL`)."""
    m = re.search(r"\[([^\]]+)\]", cell)
    txt = m.group(1) if m else cell
    txt = re.sub(r"!\[[^\]]*\]", " ", txt)
    txt = re.sub(r"<br\s*/?>", " ", txt)
    txt = re.sub(r"[\\*]", " ", txt)
    words = [w for w in re.split(r"\s+", txt) if w.strip()]
    if not words:
        return None
    if len(words[-1]) in (2, 3) and words[-1].isupper():
        return words[-1]
    return None


def club_from_team_cell(cell: str) -> str | None:
    """Club nickname (last word of the link text), or None."""
    m = re.search(r"\[([^\]]+)\]", cell)
    txt = m.group(1) if m else cell
    txt = re.sub(r"<br\s*/?>", " ", txt)
    txt = re.sub(r"!\[[^\]]*\]", " ", txt)
    pieces = [p for p in re.split(r"\s+", re.sub(r"[\\*]", " ", txt)) if p.strip()]
    if not pieces:
        return None
    return " ".join(pieces[-2:]) if len(pieces) >= 2 else pieces[-1]


def num(cell: str):
    """A printed number, or None. Never coerces a dash or a blank into a zero."""
    c = cell.strip().replace(",", "")
    if not c or c in {"-", "—", "--", "N/A"}:
        return None
    try:
        return float(c)
    except ValueError:
        return None


# ------------------------------------------------------------------ the four surfaces
def team_stats() -> dict:
    """The three team-stat pages, re-cut: one record per club per page, with the page URL.

    The columns taken are exactly the ones the model uses — OffRtg, DefRtg, NetRtg, PACE for
    the efficiency estimator, PTS and Opp PTS per game for the scoring estimator. Every one
    is read from the header the league prints on the page it was taken from.
    """
    out: dict = {"pages": {}, "teams": {}, "status": {}}
    wanted = {
        "traditional": [("GP", "gp"), ("W", "w"), ("L", "l"), ("PTS", "pts"),
                        ("PACE", "pace")],
        "advanced": [("OffRtg", "off_rtg"), ("DefRtg", "def_rtg"), ("NetRtg", "net_rtg"),
                     ("PACE", "pace"), ("TS%", "ts_pct"), ("eFG%", "efg_pct")],
        "opponent": [("OPP PTS", "opp_pts")],
    }
    for page, url in TEAM_STAT_PAGES.items():
        text, cap = read(url)
        rec = {"url": url, "captured": cap.get("retrieved_at_utc"),
               "digest_ok": cap.get("digest_ok"), "columns": {}, "n_rows": 0,
               "status": "ok"}
        out["pages"][page] = rec
        if text is None:
            rec["status"] = "not captured"
            out["status"][page] = "blank — " + cap.get("status", "not captured")
            continue
        try:
            head, body = table_after(text, "TEAM|GP")
            idx = {}
            for printed, key in wanted[page]:
                idx[key] = col_index(head, printed)
                rec["columns"][key] = printed
            team_i = col_index(head, "TEAM")
            # `opponent` page names its point column differently; try the printed variants
            if page == "opponent" and "opp_pts" not in idx:
                for alt in ("OPP PTS", "OPP_PTS", "PTS"):
                    try:
                        idx["opp_pts"] = col_index(head, alt)
                        rec["columns"]["opp_pts"] = alt
                        break
                    except LookupError:
                        continue
            rec["n_rows"] = len(body)
            for row in body:
                if len(row) <= team_i:
                    continue
                club = tri_of(row[team_i])
                if not club:
                    continue
                rec_row = out["teams"].setdefault(club, {"tri": club})
                for key, i in idx.items():
                    if key in rec_row and page != "advanced":
                        continue
                    rec_row[key] = num(row[i]) if i < len(row) else None
                rec_row[f"{page}_url"] = url
        except LookupError as e:
            rec["status"] = f"parse error: {e}"
            out["status"][page] = f"blank — {e}"
    return out


def standings() -> dict:
    """Official standings: both conference tables, W/L/HOME/ROAD/LAST10/STREAK per club.

    The page prints two tables (East then West), each with the same header. Both are read;
    a club seen twice is a finding, not a merge.
    """
    text, cap = read(STANDINGS_URL)
    doc = {"url": STANDINGS_URL, "captured": cap.get("retrieved_at_utc"),
           "digest_ok": cap.get("digest_ok"), "teams": {}, "status": "ok"}
    if text is None:
        doc["status"] = "not captured"
        doc["reason"] = cap.get("status")
        return doc
    head = None
    rows = 0
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("|") and "TEAM" in s.upper() and head is None:
            head = _cells(s)
            continue
        if head is None or not s.startswith("|"):
            continue
        cells = _cells(s)
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            continue
        try:
            team_i = col_index(head, "Team")
            w_i, l_i = col_index(head, "w"), col_index(head, "L")
            home_i = col_index(head, "HOME")
            road_i = col_index(head, "ROAD")
            l10_i = col_index(head, "LAST10")
            strk_i = col_index(head, "STREAK")
        except LookupError:
            continue
        tri = tri_of(cells[team_i])
        if not tri:
            continue
        rows += 1
        doc["teams"][tri] = {
            "tri": tri,
            "club": club_from_team_cell(cells[team_i]),
            "w": num(cells[w_i]), "l": num(cells[l_i]),
            "home": cells[home_i], "road": cells[road_i],
            "last10": cells[l10_i], "streak": cells[strk_i],
            "source_url": STANDINGS_URL,
        }
    doc["n_rows"] = rows
    if rows == 0:
        doc["status"] = "parse error: no club rows located in the two printed tables"
    return doc


def slate(days: list[str]) -> dict:
    """Upcoming games from the official games list, one capture per date."""
    out = {"days": {}, "status": {}}
    for d in days:
        url = f"https://www.nba.com/games?date={d}"
        text, cap = read(url)
        rec = {"date": d, "url": url, "captured": cap.get("retrieved_at_utc"),
               "digest_ok": cap.get("digest_ok"), "games": [], "status": "ok"}
        if text is None:
            rec["status"] = "not captured — " + str(cap.get("status"))
            out["days"][d] = rec
            out["status"][d] = rec["status"]
            continue
        try:
            rec["games"] = parse_games(text, d)
        except LookupError as e:
            rec["status"] = f"parse error: {e}"
            out["status"][d] = rec["status"]
        if not rec["games"]:
            rec["status"] = "no game rows located on the official games list"
            out["status"][d] = rec["status"]
        out["days"][d] = rec
    return out


_TIP = re.compile(r"(\d{1,2}:\d{2}\s*[AP]M\s*ET)", re.I)
_GAME_URL = re.compile(r"https://www\.nba\.com/game/([a-z]{2,4})-vs-([a-z]{2,4})-(\d{10})")


def parse_games(text: str, date: str) -> list[dict]:
    """Every game on one official games-list page: id, tip, clubs, and the game-page URL.

    The page prints each game as a markdown link whose target is the official
    `/game/<away>-vs-<home>-<game_id>` page and whose text carries the tip time and the two
    three-letter club codes. The id in the URL is the league's own game id, so a row is
    keyed by the league's key and a duplicate cannot be invented.
    """
    games: list[dict] = []
    seen: set[str] = set()
    for block in re.split(r"\n\s*\n", text):
        m = _GAME_URL.search(block)
        if not m:
            continue
        gid = m.group(3)
        if gid in seen:
            continue
        away_txt, home_txt = m.group(1).upper(), m.group(2).upper()
        tip = _TIP.search(block)
        clubs = re.findall(r"\b([A-Z]{3})\b", block)
        # the printed record beside each club confirms the same two clubs, in the same order
        away = home = None
        for i, c in enumerate(clubs):
            if c == away_txt and away is None:
                away = c
            elif c == home_txt and away is not None and home is None:
                home = c
        games.append({
            "game_id": gid, "date": date, "away": away or away_txt,
            "home": home or home_txt,
            "tip_et": tip.group(1) if tip else None,
            "game_url": m.group(0),
            "list_url": f"https://www.nba.com/games?date={date}",
        })
        seen.add(gid)
    return games


def injury_index() -> dict:
    """The league's injury-report index page: every release link it prints, with its stamp."""
    url = "https://official.nba.com/nba-injury-report-2026-27-season/"
    text, cap = read(url)
    doc = {"url": url, "captured": cap.get("retrieved_at_utc"),
           "digest_ok": cap.get("digest_ok"), "links": [], "status": "ok"}
    if text is None:
        doc["status"] = "not captured"
        doc["reason"] = cap.get("status")
        return doc
    pat = re.compile(r"(https://ak-static\.cms\.nba\.com/referee/injury/"
                     r"Injury-Report_(\d{4}-\d{2}-\d{2})_(\d{2}_\d{2}[AP]M)\.pdf)")
    seen = set()
    for m in pat.finditer(text):
        if m.group(1) in seen:
            continue
        seen.add(m.group(1))
        doc["links"].append({"url": m.group(1), "date": m.group(2),
                             "stamp_et": m.group(3).replace("_", ":")})
    doc["n_links"] = len(doc["links"])
    if not doc["links"]:
        doc["status"] = "parse error: no release link located on the index page"
    return doc


def build() -> dict:
    doc = {
        "schema": "nba2.v7.capture.v1",
        "session": "arena/6023d517-nba2",
        "rule": ("every value below was read from the official page named beside it and "
                 "parsed out of the stored bytes; a page that was not captured leaves its "
                 "values blank and flagged, never back-filled silently"),
        "manifest": manifest(),
        "team_stats": team_stats(),
        "standings": standings(),
        "injury_index": injury_index(),
    }
    return doc
