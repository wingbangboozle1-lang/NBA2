"""Session-2 capture (arena/98b0eae9-nba2): the 2026-11-15 re-read.

Loads the five capture files written on 2026-11-15 from the official NBA pages:

* ``data/raw/capture_2026-11-15/results_2026-11-14.json``   — nba2.results-feed.v2 (5 finals + quarter scores)
* ``data/raw/capture_2026-11-15/injury_report_2026-11-15_0615AM.json`` — nba2.injury-transcript.v2 (101 rows)
* ``data/raw/capture_2026-11-15/standings_2026-11-15.json`` — nba2.standings-official.v2 (30 rows + splits)
* ``data/raw/capture_2026-11-15/team_stats_2026-11-15.json`` — nba2.team-stats-3page.v1 (30 rows + cross-checks)
* ``data/raw/capture_2026-11-15/gamelogs_2026-11-14_DEN_NOP.json`` — nba2.player-gamelog.v1 (19 rows)
* ``data/raw/capture_2026-11-15/arenas_2026-11-15.json``   — nba2.arena-coords.v1 (30 arenas, third-party coords)
* ``data/raw/capture_2026-11-15/slate_2026-11-15_to_11-18.json`` — nba2.slate.v2 (34 games)

Everything here is a **loader**: no value is invented. If a file is missing the functions
raise, they do not guess. Injury rows carry the report's own fields (date / time_et /
matchup / team / player / status / reason); the timestamps the brief asks for live on the
report header:

* **revision time**  = the release stamp printed on the PDF (06:15 AM ET, 2026-11-15)
* **retrieval time** = when this session's page-fetch retrieved it (2026-11-15, UTC)

Both are published side by side on the Injuries banner (SG-21).
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAP = ROOT / "data" / "raw" / "capture_2026-11-15"

RESULTS_FILE = CAP / "results_2026-11-14.json"
INJURY_FILE = CAP / "injury_report_2026-11-15_0615AM.json"
STANDINGS_FILE = CAP / "standings_2026-11-15.json"
TEAMSTATS_FILE = CAP / "team_stats_2026-11-15.json"
GAMELOG_FILE = CAP / "gamelogs_2026-11-14_DEN_NOP.json"
ARENAS_FILE = CAP / "arenas_2026-11-15.json"
SLATE_FILE = CAP / "slate_2026-11-15_to_11-18.json"


def _load(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"capture file missing: {path}")
    return json.loads(path.read_text())


# --------------------------------------------------------------------------- results feed
def results_rows() -> list[dict]:
    """The 5 official finals of 2026-11-14, each with quarter scores and game-book links.

    Quarter sums are re-verified against the finals at load time; a mismatch raises
    (fail-closed — a broken capture must never reach the page)."""
    rows = _load(RESULTS_FILE)["records"]
    for r in rows:
        aq = r["away_quarters"]
        hq = r["home_quarters"]
        if sum(aq) != r["away_pts"] or sum(hq) != r["home_pts"]:
            raise ValueError(f"quarter sum != final for {r['game_id']}")
    return rows


def results_meta() -> dict:
    d = _load(RESULTS_FILE)
    return {
        "retrieved_at_utc": d.get("retrieved_at_utc"),
        "retrieval_method": d.get("retrieval_method"),
        "source_page": d.get("source_page"),
        "note": d.get("note", ""),
    }


def settlement_stamp() -> dict:
    """SG-22: one visible, linkable settlement stamp for the settled game day."""
    rows = results_rows()
    meta = results_meta()
    games = len(rows)
    return {
        "settled_date": rows[0]["date"] if rows else None,
        "games_settled": games,
        "official_results_url": meta.get("source_page"),
        "retrieved_at_utc": meta.get("retrieved_at_utc"),
        "stamp_text": (f"{games} official finals of {rows[0]['date']} settled from the official "
                       f"results feed, read {meta.get('retrieved_at_utc')}" if rows else "no finals captured"),
    }


# --------------------------------------------------------------------------- official results feed, all game days
# arena/669bccab-nba2 (2026-11-17): the page reads every committed official per-game source for the
# window, not only the 2026-11-14 capture. results_rows() above is deliberately UNCHANGED: the models,
# the strategy lab, travel and live.py all consume it and must keep their 5-row 2026-11-14 input.
V5_RESULTS = ROOT / "data" / "v5" / "results_union.json"
V5_GAMEBOOKS = ROOT / "data" / "v5"
RECHECK_1115 = ROOT / "data" / "raw" / "results" / "results_2026-11-15_recheck_2026-11-17.json"
RESULTS_1116 = ROOT / "data" / "raw" / "results" / "results_2026-11-16.json"
FEED_WINDOW = ("2026-11-14", "2026-11-16")


def _nba_game_page(away: str, home: str, gid: str) -> str:
    return f"https://www.nba.com/game/{away.lower()}-vs-{home.lower()}-{gid}"


def _v5_ot(date: str, gid: str) -> dict:
    """Overtime period points for a v5 game, from its committed gamebook transcript (or empty)."""
    p = V5_GAMEBOOKS / f"gamebooks_{date}.json"
    if not p.exists():
        return {"away": [], "home": []}
    for g in json.loads(p.read_text()).get("games", []):
        if g.get("game_id") == gid:
            q = g.get("quarters") if isinstance(g.get("quarters"), dict) else {}
            ot = q.get("ot") or {}
            return {"away": list(ot.get("away") or []), "home": list(ot.get("home") or [])}
    return {"away": [], "home": []}


def _feed_row(r: dict, origin: str) -> dict:
    gid, away, home = r["game_id"], r["away"], r["home"]
    src = r.get("source_url") or _nba_game_page(away, home, gid)
    gamebook = r.get("gamebook_url")
    if gamebook is None and str(src).endswith(".pdf"):   # v5 rows keep the gamebook PDF in source_url
        gamebook, src = src, _nba_game_page(away, home, gid)
    ot = {"away": [], "home": []}
    if origin == "v5" and (r.get("ot_periods") or 0) > 0:
        ot = _v5_ot(r["date"], gid)
    return {
        "game_id": gid, "date": r["date"], "away": away, "home": home,
        "away_pts": r["away_pts"], "home_pts": r["home_pts"],
        "away_quarters": r.get("away_quarters"), "home_quarters": r.get("home_quarters"),
        "ot_quarters": ot, "ot_periods": r.get("ot_periods") or 0,
        "quarters_blank_reason": r.get("quarters_blank_reason"),
        "source_url": src, "gamebook_url": gamebook, "origin": origin,
    }


def feed_rows() -> list[dict]:
    """One row per official final in FEED_WINDOW, merged from every committed official source.

    Fail-closed: two sources that disagree on a final raise; a quarter row (plus any overtime
    periods) that does not sum to the final raises; a blank quarter row stays blank with its reason.
    """
    candidates: list[dict] = []
    for r in _load(RESULTS_FILE)["records"]:
        candidates.append(_feed_row(r, "capture-2026-11-14"))
    for r in _load(V5_RESULTS)["records"]:
        candidates.append(_feed_row(r, "v5"))
    for r in _load(RECHECK_1115)["records"]:
        candidates.append(_feed_row(r, "recheck-2026-11-17"))
    for r in _load(RESULTS_1116)["records"]:
        candidates.append(_feed_row(r, "results-2026-11-16"))
    by_id: dict[str, dict] = {}
    for c in candidates:
        if not (FEED_WINDOW[0] <= c["date"] <= FEED_WINDOW[1]):
            continue
        prev = by_id.get(c["game_id"])
        if prev is not None:
            if (prev["away_pts"], prev["home_pts"]) != (c["away_pts"], c["home_pts"]):
                raise ValueError(f"official sources disagree on {c['game_id']}: "
                                 f"{prev['origin']} {prev['away_pts']}-{prev['home_pts']} vs "
                                 f"{c['origin']} {c['away_pts']}-{c['home_pts']}")
            # keep the first source's row; a later source may only fill a blank quarter row
            for side in ("away", "home"):
                if prev[f"{side}_quarters"] is None and c[f"{side}_quarters"] is not None:
                    prev[f"{side}_quarters"] = c[f"{side}_quarters"]
                    prev[f"{side}_quarter_origin"] = c["origin"]
            continue
        by_id[c["game_id"]] = c
    rows = sorted(by_id.values(), key=lambda r: (r["date"], r["game_id"]))
    for r in rows:
        for side in ("away", "home"):
            q = r[f"{side}_quarters"]
            if q is None:
                continue
            total = sum(q) + sum(r["ot_quarters"][side])
            pts = r[f"{side}_pts"]
            if total != pts:
                raise ValueError(f"quarter sum != final for {r['game_id']} {side}: {total} != {pts}")
    return rows


def feed_stamp() -> dict:
    """One visible settlement stamp for the whole results feed (window, count, read times)."""
    rows = feed_rows()
    dates = sorted({r["date"] for r in rows})
    per_date = {d: sum(1 for r in rows if r["date"] == d) for d in dates}
    return {
        "settled_date": dates[-1] if dates else None,
        "window": list(FEED_WINDOW),
        "games_settled": len(rows),
        "per_date": per_date,
        "official_results_url": "https://www.nba.com/games",
        "retrieved_at_utc": ("2026-11-15T12:00Z (11/14 capture) · 2026-11-16 ~18:27-18:36Z (v5 gamebooks, 11/14-11/15) · "
                             "2026-11-17 (this session; 11/15 recheck and 11/16 games; per-call times not logged)"),
        "stamp_text": (f"{len(rows)} official finals settled, {FEED_WINDOW[0]} to {dates[-1] if dates else '-'}: "
                       + ", ".join(f"{d} {n}" for d, n in per_date.items())
                       + ". Each final is on an official NBA page; quarter rows sum to the final or are left blank."),
    }


# --------------------------------------------------------------------------- injuries
INJURY_COLS = ["date", "time_et", "matchup", "team", "player", "status", "reason"]


def injury_doc() -> dict:
    return _load(INJURY_FILE)


def injury_rows() -> list[dict]:
    """101 rows as dicts. The transcript stores each row as a list (columns in
    ``columns``); rows 8+ may carry an extra transcription/flag note which becomes
    ``flag_note``. ``team`` is the full club name exactly as printed on the PDF."""
    d = injury_doc()
    out = []
    for r in d["records"]:
        row = dict(zip(INJURY_COLS, r[:7]))
        if len(r) > 7:
            row["flag_note"] = r[7]
        out.append(row)
    return out


def injury_meta() -> dict:
    """The two timestamps the brief wants on the banner, plus provenance."""
    d = injury_doc()
    meta = dict(d.get("provenance", {}))
    meta["row_count"] = len(d["records"])
    meta["revision_time_et"] = d.get("revision_time_et") or d.get("report_stamp_et")
    meta["report_stamp_et"] = d.get("report_stamp_et")
    meta["retrieval_time_utc"] = d.get("retrieved_at_utc")
    meta["retrieval_method"] = d.get("retrieval_method")
    meta["pdf_url"] = meta.get("url")
    return meta


def injury_by_matchup() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for r in injury_rows():
        out.setdefault(r["matchup"], []).append(r)
    return out


def _tri(team_name: str) -> str:
    from . import official as O
    rev = {v: k for k, v in O.NAMES.items()}
    return rev.get(team_name, team_name)


def rotation_availability(matchup: str) -> dict:
    """One availability summary per slate game, straight from the newest release.

    Returns {"teams": {tri: {...counts, names...}}, "text": ...}. Rows for a club not on
    this game's matchup are never attached (the report is per-game). A club whose only
    row is ``NOT YET SUBMITTED`` shows that literally — never "0 injuries"."""
    rows = injury_by_matchup().get(matchup, [])
    teams: dict[str, dict] = {}
    for r in rows:
        tri = _tri(r.get("team") or "")
        reason = (r.get("reason") or "")
        st = (r.get("status") or "").strip()
        if "NOT YET SUBMITTED" in reason or (not r.get("player") and not st):
            teams.setdefault(tri, {"Out": 0, "Doubtful": 0, "Questionable": 0,
                                   "Probable": 0, "Available": 0, "names_out": [],
                                   "names_doubtful": [], "names_questionable": [],
                                   "not_submitted": True})
            teams[tri].setdefault("not_submitted", True)
            continue
        t = teams.setdefault(tri, {"Out": 0, "Doubtful": 0, "Questionable": 0,
                                   "Probable": 0, "Available": 0, "names_out": [],
                                   "names_doubtful": [], "names_questionable": [],
                                   "not_submitted": False})
        if st == "Out":
            t["Out"] += 1
            t["names_out"].append(r["player"])
        elif st == "Doubtful":
            t["Doubtful"] += 1
            t["names_doubtful"].append(r["player"])
        elif st == "Questionable":
            t["Questionable"] += 1
            t["names_questionable"].append(r["player"])
        elif st == "Probable":
            t["Probable"] += 1
        elif st == "Available":
            t["Available"] += 1
    parts = []
    for tri, t in teams.items():
        if t.get("not_submitted"):
            parts.append(f"{tri}: NOT YET SUBMITTED")
            continue
        bits = []
        if t["Out"]:
            bits.append(f"{t['Out']} OUT ({', '.join(t['names_out'][:4])}{'…' if len(t['names_out']) > 4 else ''})")
        if t["Doubtful"]:
            bits.append(f"{t['Doubtful']} DOUBTFUL ({', '.join(t['names_doubtful'])})")
        if t["Questionable"]:
            bits.append(f"{t['Questionable']} QUESTIONABLE ({', '.join(t['names_questionable'][:3])}{'…' if len(t['names_questionable']) > 3 else ''})")
        if not bits:
            bits.append("designations filed, none OUT/DOUBTFUL/QUESTIONABLE")
        parts.append(f"{tri}: " + "; ".join(bits))
    return {"teams": teams, "text": " | ".join(parts) if parts else "NOT YET SUBMITTED in the newest release"}


def delta_vs_prev(prev_rows: list[dict]) -> dict:
    """Diff the 06:15 AM 11/15 release against an earlier release row list.

    Matching key is (normalized player surname+given, team when both carry one).
    Returns added / removed / status_changed lists, each row flagged with its release."""

    def key(r):
        return (str(r.get("player", "")).strip().lower(), str(r.get("team_tri") or r.get("team") or "").strip().lower())

    new = {key(r): r for r in injury_rows()}
    old = {key(r): r for r in prev_rows}
    added = [r for k, r in new.items() if k not in old]
    removed = [r for k, r in old.items() if k not in new]
    changed = [{"player": r.get("player"), "team": r.get("team_tri") or r.get("team"),
                "from": old[k].get("status"), "to": r.get("status"),
                "reason": r.get("reason")}
               for k, r in new.items() if k in old and old[k].get("status") != r.get("status")]
    return {"added": added, "removed": removed, "status_changed": changed,
            "from_rows": len(prev_rows), "to_rows": len(new)}


# --------------------------------------------------------------------------- other captures
def standings_rows() -> list[dict]:
    d = _load(STANDINGS_FILE)
    cols = d["columns"]
    return [dict(zip(cols, r)) for r in d["records"]]


def team_stats_doc() -> dict:
    return _load(TEAMSTATS_FILE)


def gamelog_rows() -> list[dict]:
    d = _load(GAMELOG_FILE)
    for r in d["records"]:
        # capture-time gates re-run at load: minutes per team must sum to 240:00
        pass
    by_team: dict[str, int] = {}
    for r in d["records"]:
        by_team[r["team"]] = by_team.get(r["team"], 0) + r["min_sec"]
    for tri, secs in by_team.items():
        if secs != 240 * 60:
            raise ValueError(f"game log minutes for {tri} sum to {secs}, not 240:00")
    return d["records"]


def gamelog_meta() -> dict:
    d = _load(GAMELOG_FILE)
    return {"retrieved_at_utc": d.get("retrieved_at_utc"), "source_url": d.get("source_url"),
            "note": d.get("note", "")}


def arena_rows() -> list[dict]:
    return _load(ARENAS_FILE)["rows"]


def arena_by_team() -> dict[str, dict]:
    return {r["team"]: r for r in arena_rows()}


def slate_rows() -> list[dict]:
    return _load(SLATE_FILE)["games"]


def source_rows() -> list[dict]:
    """Flat list of every official source this session's captures touched — one link per
    table row on the site can point here or at the specific URL in each row."""
    out = []
    for r in results_rows():
        out.append({"what": f"final {r['game_id']}", "url": r["source_url"]})
    d = injury_doc()
    out.append({"what": "injury release 2026-11-15 06:15 AM ET", "url": d.get("pdf_url") or d.get("provenance", {}).get("url")})
    out.append({"what": "standings", "url": "https://www.nba.com/standings"})
    out.append({"what": "schedule", "url": "https://www.nba.com/schedule?date=2026-11-15"})
    out.append({"what": "team stats (advanced)", "url": "https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season"})
    out.append({"what": "team stats (traditional)", "url": "https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season"})
    out.append({"what": "team stats (opponent)", "url": "https://www.nba.com/stats/teams/opponent?Season=2026-27&SeasonType=Regular+Season"})
    return out
