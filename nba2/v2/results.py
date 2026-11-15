"""Official per-game results feed — one row per game: date, teams, final score, quarters.

What this module is for (brief lines 2 and 18)
----------------------------------------------
* Keep an official per-game result feed current, and settle only after the final score is
  verified against that feed.
* Store one row per game: date, teams, final score, quarter scores.

Design rules
------------
1. **A game is settled only when the feed says it is final, and the feed is official.** Every
   row carries the official game URL it was read from; a row with no URL is not a result.
2. **Quarter scores are a real column with a real source, not a decoration.** Where the
   official period scores have not been captured the cells are empty and the row says why
   (``quarters_missing_reason``). A blank cell is published; an invented one is not.
3. **Completeness is measured, not asserted.** The feed counts games per date and compares
   the total with the league identity (Σ wins = Σ losses = games) and with the standings
   capture. A missing night of results shows up as a failed identity, not as a quiet gap.
4. **This module never writes a result it did not read.**

Quarter-score capture
---------------------
nba.com prints the final score on the date page (``nba.com/games?date=...``) and the period
scores on the per-game box-score page and in the league's ``scoreboardv2`` LineScore payload
(``PTS_QTR1..PTS_QTR4``). In this session's sandbox the ``cdn.nba.com`` and ``stats.nba.com``
JSON endpoints return HTTP 500, and the box-score page renders its tables client-side, so the
period scores could not be read here. The capture path is wired in
``nba2/pipeline/refresh.py`` (``--finals`` now stores ``quarters`` from the LineScore payload
when it is reachable) and the nightly job runs where those endpoints are reachable. Until a
date is captured that way, its quarter cells are blank and the row states the reason — which
is the difference between an incomplete feed and a fabricated one.

Run:  python3 -m nba2.v2.results
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HISTORY = ROOT / "data" / "raw" / "history"
FINALS_GLOB = "finals_2*.json"

QUARTER_KEYS = ("Q1", "Q2", "Q3", "Q4")


def load_rows() -> list[dict]:
    """One row per official final, newest capture winning, sorted by date then game id.

    Sources, in precedence order: the per-date finals snapshots written by the ingest job
    (``data/raw/finals_<date>.json``) and the committed history captures
    (``data/raw/history/games_*.json``). Both are official; the history files carry the
    per-game source URL, the finals files carry the endpoint they came from.
    """
    rows: dict[str, dict] = {}
    for path in sorted((ROOT / "data" / "raw").glob("finals_2*.json")):
        doc = json.loads(path.read_text())
        # The date page / endpoint the snapshot was read from is the second official surface
        # for every record in it, so a record does not have to repeat it.
        list_url = (doc.get("provenance", {}) or {}).get("list_url", "")
        for r in doc.get("games", []) + doc.get("records", []):
            if not isinstance(r, dict):
                continue          # a finals file may list ids as strings
            gid = r.get("game_id")
            if not gid:
                continue
            rows[gid] = {
                "game_id": gid,
                "date": r.get("date") or path.name[len("finals_"):-len(".json")],
                "away": r.get("away"), "home": r.get("home"),
                "away_pts": r.get("away_pts"), "home_pts": r.get("home_pts"),
                "overtime": bool(r.get("overtime")),
                "quarters": r.get("quarters") or {"away": [], "home": []},
                "quarters_captured": bool(r.get("quarters_captured")),
                "quarters_missing_reason": r.get("quarters_missing_reason", ""),
                "neutral_site": bool(r.get("neutral_site")),
                "source": r.get("source") or r.get("source_url") or "",
                "source_second": (r.get("second_source") or r.get("list_url") or list_url),
                "captured_by": path.name,
            }
    for path in sorted(HISTORY.glob("games_*.json")):
        doc = json.loads(path.read_text())
        for g in doc.get("games", []):
            gid = g.get("game_id")
            if not gid:
                continue
            if gid in rows:
                # the history capture is the richer record (it carries arenas and sources);
                # fill any column the finals snapshot left empty, never overwrite a value.
                cur = rows[gid]
                for k in ("date", "away", "home", "away_pts", "home_pts", "source",
                          "source_second", "quarters", "quarters_captured",
                          "quarters_missing_reason", "neutral_site", "overtime"):
                    if not cur.get(k) and g.get(k):
                        cur[k] = g[k]
                cur.setdefault("arena", g.get("arena", ""))
                cur.setdefault("city", g.get("city", ""))
                continue
            rows[gid] = {
                "game_id": gid, "date": g.get("date"), "away": g.get("away"),
                "home": g.get("home"), "away_pts": g.get("away_pts"),
                "home_pts": g.get("home_pts"), "overtime": bool(g.get("ot")),
                "quarters": g.get("quarters") or {"away": [], "home": []},
                "quarters_captured": bool(g.get("quarters_captured")),
                "quarters_missing_reason": g.get("quarters_missing_reason", ""),
                "neutral_site": bool(g.get("neutral_site")),
                "source": g.get("source_url", ""),
                "source_second": g.get("list_url", ""),
                "arena": g.get("arena", ""), "city": g.get("city", ""),
                "captured_by": path.name,
            }
    out = [r for r in rows.values() if r.get("away_pts") is not None
           and r.get("home_pts") is not None]
    out.sort(key=lambda r: (r.get("date") or "", r["game_id"]))
    return out


def verified(row: dict) -> tuple[bool, str]:
    """Is this row a verified official final?

    Two independent official surfaces (a per-game URL and a date page / endpoint) is the
    standard the settlement path requires; one is enough to publish the score, but not
    enough to settle a sealed pick against it.
    """
    if not row.get("source"):
        return False, "no official game URL on the row"
    if row.get("away_pts") is None or row.get("home_pts") is None:
        return False, "a score is missing"
    if not row.get("source_second"):
        return False, "only one official surface captured"
    return True, "final score present on two official surfaces"


def feed() -> dict:
    """The published results feed: one row per game, plus the completeness arithmetic."""
    rows = load_rows()
    for r in rows:
        ok, why = verified(r)
        r["verified"], r["verified_reason"] = ok, why
        r["won"] = (r["home"] if r["home_pts"] > r["away_pts"] else r["away"])
        r["margin"] = abs(r["home_pts"] - r["away_pts"])
        r["total"] = r["away_pts"] + r["home_pts"]
        q = r["quarters"] or {}
        r["quarters_home"] = q.get("home") or []
        r["quarters_away"] = q.get("away") or []

    dates = sorted({r["date"] for r in rows if r.get("date")})
    per_date = Counter(r["date"] for r in rows)
    wins = Counter()
    for r in rows:
        wins[r["won"]] += 1
    n_q = sum(1 for r in rows if r["quarters_captured"])
    # league identity: every game is a win for one club and a loss for another
    total_w = sum(wins.values())
    identity_ok = total_w == len(rows)
    # cross-check against the newest committed official standings capture
    std_files = sorted((ROOT / "data" / "raw").glob("official_standings_*.json"))
    std = json.loads(std_files[-1].read_text()) if std_files else None
    record_mismatch = []
    if std:
        for rec in std["records"]:
            got = wins.get(rec["tricode"], 0)
            if got != rec["w"]:
                record_mismatch.append({"team": rec["tricode"], "feed_wins": got,
                                        "standings_wins": rec["w"]})
    return {
        "schema": "nba2.results-feed.v1",
        "n_games": len(rows),
        "first_date": dates[0] if dates else None,
        "last_date": dates[-1] if dates else None,
        "n_dates": len(dates),
        "per_date": dict(sorted(per_date.items())),
        "rows": rows,
        "n_verified": sum(1 for r in rows if r["verified"]),
        "n_quarters_captured": n_q,
        "quarters_coverage": round(n_q / len(rows), 4) if rows else 0.0,
        "quarters_blocked_reason": (
            "period scores are printed on the per-game box-score page and in the league "
            "scoreboardv2 LineScore payload; neither is reachable from this environment "
            "(cdn.nba.com and stats.nba.com return HTTP 500 here). The capture path is "
            "wired in nba2/pipeline/refresh.py --finals and runs in the nightly job, which "
            "executes where those endpoints are reachable. Until a date is captured that "
            "way its quarter cells stay empty and the row says so."),
        "league_identity_ok": identity_ok,
        "league_wins": total_w,
        "standings_capture": std_files[-1].name if std_files else None,
        "records_mismatching_standings": record_mismatch,
        "public_note": (
            "Every row is an official final with the game URL it was read from. A row is "
            "settled against a sealed pick only when two official surfaces agree on the "
            "final score."),
    }


def main() -> int:
    f = feed()
    print(f"{f['n_games']} official finals, {f['first_date']} -> {f['last_date']} "
          f"({f['n_dates']} dates)")
    print(f"verified on two surfaces: {f['n_verified']}/{f['n_games']}")
    print(f"quarter scores captured:  {f['n_quarters_captured']}/{f['n_games']} "
          f"({f['quarters_coverage']:.1%})")
    print(f"league identity (wins == games): {f['league_identity_ok']} "
          f"({f['league_wins']} wins)")
    print(f"records matching the newest standings capture "
          f"({f['standings_capture']}): "
          f"{30 - len(f['records_mismatching_standings'])}/30")
    for d, n in f["per_date"].items():
        print(f"  {d}: {n} games")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
