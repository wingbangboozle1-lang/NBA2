"""Derived tables from the v5 transcripts: result feed, minutes shares, replacement shares,
and the join to the official injury report.

Nothing here estimates. A share is a division of two numbers the official gamebook printed.
A replacement share is a difference between two measured shares. Where the window does not
contain both a game the player played and a game he missed, the row is blank with a reason.
"""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict

from . import transcript as T

INJURY_DIR = T.DATA / "raw" / "refresh_2026-11-16"
# 1eeb6a21: the 2026-11-17 capture directory is read alongside 11/16 so the newest report
# stamp (11/17 11:00 AM ET) wins the join; the superseded-file skip is preserved.
INJURY_DIRS = [INJURY_DIR, T.DATA / "raw" / "refresh_2026-11-17"]
INJURY_TRANSCRIPTS = sorted(
    p for d in INJURY_DIRS for p in d.glob("injury_transcript_*.json")
    if "superseded" not in p.name)

INJURY_INDEX_URL = "https://official.nba.com/nba-injury-report-2026-27-season/"


SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}


def norm(name: str) -> str:
    """Fold accents, punctuation, case and generational suffixes.

    'Doncic' matches 'Dončić' and 'P.J. Washington Jr.' matches 'P.J. Washington'. The
    suffix fold is a documented convention, not a guess about identity: every name it
    changes is listed in ``folded_names()`` so a reviewer can undo it. Spellings that
    differ beyond a suffix (the 11/14 book prints 'Marcus Sassar', the 11/15 book prints
    'Marcus Sasser') are NOT folded — they are flagged instead.
    """
    s = unicodedata.normalize("NFKD", name or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace(".", "").replace("'", "").replace("-", " ")
    parts = [p for p in s.split() if p not in SUFFIXES]
    return " ".join(parts)


def folded_names(rows: list[dict]) -> list[dict]:
    """Every player whose name changes under the suffix fold, with both spellings."""
    seen: dict[str, set[str]] = {}
    for r in rows:
        seen.setdefault(norm(r["player"]), set()).add(r["player"])
    return [{"key": k, "spellings": sorted(v)} for k, v in sorted(seen.items())
            if len(v) > 1]


def suspect_spelling_pairs(rows: list[dict]) -> list[dict]:
    """Distinct names inside one club that differ only by one character run.

    The official gamebooks disagree on the spelling of at least one player between dates.
    Folding them would be an inference, so they are reported and excluded from the
    replacement table, where a same-player split would fabricate an in/out pair.
    """
    out = []
    for tri in sorted({r["team"] for r in rows}):
        names = sorted({r["player"] for r in rows if r["team"] == tri})
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                na, nb = norm(a), norm(b)
                if na == nb or not na or not nb:
                    continue
                if _edit_like(na, nb):
                    out.append({"team": tri, "name_a": a, "name_b": b,
                                "reason": "same club, near-identical spelling; the two "
                                          "official gamebooks disagree, so the pair is "
                                          "flagged and excluded from the replacement table "
                                          "rather than merged by inference"})
    return out


def _edit_like(a: str, b: str) -> bool:
    """One substitution, insertion or deletion between two already-normalised names."""
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        diff = [i for i in range(len(a)) if a[i] != b[i]]
        return len(diff) == 1
    long, short = (a, b) if len(a) > len(b) else (b, a)
    for i in range(len(long)):
        if long[:i] + long[i + 1:] == short:
            return True
    return False


def result_rows(games: list[dict]) -> list[dict]:
    """One row per game: date, teams, final, quarter scores."""
    out = []
    for g in sorted(games, key=lambda x: (x["date"], x["matchup"])):
        qa = g["quarters"].get("away")
        qh = g["quarters"].get("home")
        ota = g["quarters"].get("ot", {}).get("away") or []
        oth = g["quarters"].get("ot", {}).get("home") or []
        out.append({
            "date": g["date"],
            "game_id": g["game_id"],
            "matchup": g["matchup"],
            "away": g["away"],
            "home": g["home"],
            "away_pts": g["final"]["away"],
            "home_pts": g["final"]["home"],
            "away_quarters": qa,
            "home_quarters": qh,
            "ot_periods": len(ota) or len(oth),
            "ot_quarters": {"away": ota, "home": oth} if (ota or oth) else None,
            "quarter_check": _quarter_check(g),
            "quarters_blank_reason": g.get("quarters_blank_reason"),
            "source_url": g["source_url"],
            "source_class": "official",
            "retrieved_window_utc": g["retrieved_window_utc"],
        })
    return out


def _quarter_check(g: dict) -> str:
    parts = []
    for side, club in (("away", g["away"]), ("home", g["home"])):
        q = g["quarters"].get(side)
        ot = g["quarters"].get("ot", {}).get(side) or []
        if not q:
            parts.append(f"{club}: blank by policy")
            continue
        s = sum(q) + sum(ot)
        ok = "sums to the final" if s == g["final"][side] else f"MISMATCH {s} vs {g['final'][side]}"
        parts.append(f"{club} {'+'.join(str(x) for x in q + ot)} = {s} {ok}")
    return "; ".join(parts)


def minutes_shares(rows: list[dict]) -> list[dict]:
    """Top-8 minutes shares for every club-game in the union."""
    out = []
    by_key = T.team_games(rows)
    for (tri, gid), players in sorted(by_key.items()):
        total = sum(p["min_sec"] or 0 for p in players)
        if not total:
            continue
        played = [p for p in players if p["min_sec"]]
        top = played[:8]
        rec = {
            "date": players[0]["date"],
            "game_id": gid,
            "matchup": players[0]["matchup"],
            "team": tri,
            "opp": players[0]["opp"],
            "team_minutes_s": total,
            "n_played": len(played),
            "top8": [{"player": p["player"], "min": p["min"],
                      "share": round((p["min_sec"] or 0) / total, 4),
                      "pts": p["pts"], "reb": p["reb"], "ast": p["ast"]} for p in top],
            "top8_share": round(sum((p["min_sec"] or 0) for p in top) / total, 4),
            "dnp": [{"player": p["player"], "status": p["status"]}
                    for p in players if not p["min_sec"]],
            "dnp_captured": any(not p["min_sec"] for p in players),
            "source_url": players[0]["source_url"],
        }
        out.append(rec)
    return out


def replacement_shares(rows: list[dict]) -> list[dict]:
    """For each club, players who both played and missed a game inside the window.

    Two measurement rules, both forced by what the official documents print:

    * **Absence is only measurable in the 11/14 and 11/15 gamebooks.** They print the whole
      active list, DNP and DND rows included, so a player not in the book was not active.
      The 11/13 capture records only the players who appeared, so it can contribute a
      'played' game but never an 'out' game.
    * **DNP/DND rows are not absences.** A player printed with 'DNP - Coach's Decision' was
      active and available; he is out only when he is missing from the book entirely.
    """
    by_team: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_team[r["team"]].append(r)

    suspects: set[tuple[str, str]] = set()
    for s in suspect_spelling_pairs(rows):
        suspects.add((s["team"], norm(s["name_a"])))
        suspects.add((s["team"], norm(s["name_b"])))

    out = []
    for tri, rr in sorted(by_team.items()):
        all_games = sorted({r["game_id"] for r in rr})
        book_games = sorted({r["game_id"] for r in rr
                             if r["transcript"].startswith("gamebooks_")})
        if not book_games:
            continue
        roster_by_game: dict[str, set[str]] = {}
        shares_by_game: dict[str, dict[str, float]] = {}
        mins_by_game: dict[str, dict[str, int]] = {}
        for gid in all_games:
            club = [r for r in rr if r["game_id"] == gid]
            total = sum(r["min_sec"] or 0 for r in club) or 1
            roster_by_game[gid] = {norm(r["player"]) for r in club}
            shares_by_game[gid] = {norm(r["player"]): (r["min_sec"] or 0) / total
                                   for r in club}
            mins_by_game[gid] = {norm(r["player"]): (r["min_sec"] or 0) for r in club}
        display: dict[str, str] = {}
        for r in rr:
            display.setdefault(norm(r["player"]), r["player"])
        everyone = sorted(set().union(*roster_by_game.values()))
        for key in everyone:
            if (tri, key) in suspects:
                continue
            played = [g for g in all_games if mins_by_game[g].get(key, 0) > 0]
            missed = [g for g in book_games if key not in roster_by_game[g]]
            if not played or not missed:
                continue
            share_in = sum(shares_by_game[g][key] for g in played) / len(played)
            deltas = []
            for other in everyone:
                if other == key or (tri, other) in suspects:
                    continue
                in_share = sum(shares_by_game[g].get(other, 0.0) for g in played) / len(played)
                out_share = sum(shares_by_game[g].get(other, 0.0) for g in missed) / len(missed)
                mins_in = sum(mins_by_game[g].get(other, 0) for g in played) / len(played)
                mins_out = sum(mins_by_game[g].get(other, 0) for g in missed) / len(missed)
                deltas.append((out_share - in_share, mins_out - mins_in, display.get(other, other),
                               in_share, out_share, mins_in, mins_out))
            deltas.sort(reverse=True)
            rec = {
                "team": tri,
                "player": display.get(key, key),
                "n_games_in_window": len(all_games),
                "games_played": len(played),
                "games_out": len(missed),
                "avg_min_share_when_playing": round(share_in, 4),
                "avg_min_when_playing_s": round(
                    sum(mins_by_game[g][key] for g in played) / len(played)),
                "replacements": [
                    {"player": d[2], "share_delta": round(d[0], 4),
                     "minutes_delta": round(d[1]),
                     "share_with": round(d[3], 4), "share_without": round(d[4], 4),
                     "minutes_with": round(d[5]), "minutes_without": round(d[6])}
                    for d in deltas if d[0] > 0][:5],
                "top_replacement": deltas[0][2] if deltas else None,
                "top_replacement_minutes_delta": round(deltas[0][1]) if deltas else None,
                "window_note": (f"{len(played)} game(s) played and {len(missed)} game(s) out "
                                f"of {len(all_games)} captured for this club; a "
                                f"measurement over that window, not a fitted effect"),
                "source_urls": sorted({
                    r["source_url"] for r in rr
                    if r["game_id"] in set(played) | set(missed)}),
            }
            out.append(rec)
    out.sort(key=lambda r: (r["team"], -r["avg_min_share_when_playing"]))
    return out


def injury_rows() -> list[dict]:
    """The official 11/16 injury report flattened to tricode + 'First Last'."""
    rows = []
    for path in INJURY_TRANSCRIPTS:
        if not path.exists():
            continue
        doc = T._load(path)
        cols = doc["columns"]
        for rec in doc["records"]:
            d = dict(zip(cols, rec))
            rows.append({
                "report_stamp_et": doc["report_stamp_et"],
                "revision_time_et": doc["revision_time_et"],
                "retrieved_at_utc": doc["retrieved_at_utc"],
                "date": d.get("date"),
                "matchup": d.get("matchup"),
                "team_name": d.get("team"),
                "team": T.TEAM_NAME.get(d.get("team")),
                "player": _first_last(d.get("player")),
                "status": (d.get("status") or "").strip(),
                "reason": d.get("reason"),
                "source_url": doc["provenance"]["url"] if isinstance(doc.get("provenance"), dict) else None,
                "transcript": path.name,
            })
    return rows


def _first_last(name: str) -> str:
    if not name:
        return ""
    if "," in name:
        last, first = name.split(",", 1)
        return f"{first.strip()} {last.strip()}"
    return name.strip()


def injury_join(rows: list[dict]) -> dict:
    """Join the newest injury report to the union of player logs."""
    inj = injury_rows()
    if not inj:
        return {"matched": [], "unmatched": [], "n_report_rows": 0, "stamp": None}
    # Newest by the official revision stamp, not by filename: another session may add a
    # later filing at any time (the 09:30 AM release was superseded mid-session).
    def _rank(stamp: str) -> tuple:
        m = re.match(r"(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}) ([AP])M", stamp or "")
        if not m:
            return (0,)
        y, mo, d, hh, mm, ap = m.groups()
        h = int(hh) % 12 + (12 if ap == "P" else 0)
        return (int(y), int(mo), int(d), h, int(mm))
    newest = max(inj, key=lambda r: _rank(r["report_stamp_et"]))["report_stamp_et"]
    report = [r for r in inj if r["report_stamp_et"] == newest]

    by_team_player: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in rows:
        by_team_player[(r["team"], norm(r["player"]))].append(r)

    # Every name the window's gamebooks print for a club, whether or not he played.
    on_active_list: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        if r["transcript"].startswith("gamebooks_"):
            on_active_list[r["team"]].add(norm(r["player"]))

    matched, unmatched = [], []
    for r in report:
        key = (r["team"], norm(r["player"]))
        logs = by_team_player.get(key)
        if not logs:
            unmatched.append({**r, "reason_not_matched": _why_missing(r, rows, on_active_list)})
            continue
        logs = sorted(logs, key=lambda x: x["date"], reverse=True)
        last = logs[0]
        matched.append({
            **r,
            "n_logs": len(logs),
            "last_game_date": last["date"],
            "last_matchup": last["matchup"],
            "last_min": last["min"],
            "last_pts": last["pts"],
            "last_reb": last["reb"],
            "last_ast": last["ast"],
            "last_played": last["played"],
            "last_source_url": last["source_url"],
            "logs": [{"date": l["date"], "matchup": l["matchup"], "min": l["min"],
                      "pts": l["pts"], "reb": l["reb"], "ast": l["ast"],
                      "source_url": l["source_url"]} for l in logs],
        })
    played_match = [m for m in matched if m["last_played"]]
    return {
        "stamp": newest,
        "report_rows": len(report),
        "n_report_rows": len(report),
        "matched": matched,
        "unmatched": unmatched,
        "n_matched": len(matched),
        "n_matched_played": len(played_match),
        "n_unmatched": len(unmatched),
        "n_unmatched_out_all_window": sum(
            1 for u in unmatched if "absent from the active list" in u["reason_not_matched"]),
        "n_unmatched_active_no_minutes": sum(
            1 for u in unmatched if "never appeared" in u["reason_not_matched"]),
        "coverage": round(len(matched) / len(report), 4) if report else 0.0,
        "coverage_played": round(len(played_match) / len(report), 4) if report else 0.0,
        "index_url": INJURY_INDEX_URL,
    }


def _why_missing(rec: dict, rows: list[dict], on_active_list: dict[str, set[str]]) -> str:
    tri = rec["team"]
    if not tri:
        return "the team name on the report is not one of the 30 official clubs"
    games_ = sorted({(r["date"], r["game_id"]) for r in rows if r["team"] == tri})
    if not games_:
        return "no game has been captured for this club in the window"
    if norm(rec["player"]) in on_active_list.get(tri, set()):
        return ("on the club's active list in the window but never appeared (DNP/DND row), "
                "so there is no minutes log to join")
    return (f"absent from the active list in all {len(games_)} of this club's captured "
            f"game(s) ({', '.join(d for d, _ in games_)}) - i.e. out for every game we "
            f"hold, which is what an injured player's report row would predict")


def build() -> dict:
    rows = T.player_rows()
    gs = T.games()
    return {
        "results": result_rows(gs),
        "minutes": minutes_shares(rows),
        "replacement": replacement_shares(rows),
        "injury": injury_join(rows),
        "rows": rows,
        "n_rows": len(rows),
        "n_games": len({(r["date"], r["game_id"]) for r in rows}),
        "n_clubs": len({r["team"] for r in rows}),
        "dates": sorted({r["date"] for r in rows}),
    }
