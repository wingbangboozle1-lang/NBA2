"""Minutes redistribution and rotation availability — brief line 11 and 16.

    "Model minutes redistribution explicitly: top-8 minutes shares plus the replacement
     shares when a player is out."
    "Capture per-player game logs (minutes, points, rebounds, assists, opponent) for at
     least the players who appear on an injury report."

What is measured and what is assumed
------------------------------------
MEASURED (official, one row per player per game, transcribed from the official box score
page listed on every row):

* the per-player game log itself — minutes, points, rebounds, assists, opponent;
* the minutes SHARE of each player in each captured game (player minutes / team minutes);
* the top-8 shares per team, averaged over the captured games.

ASSUMED (derived, never presented as official):

* who absorbs the minutes when a player is ruled out. A captured game tells us who played
  how much WITH the current lineup; it does not contain a counterfactual. So the
  redistribution rule is stated up front and printed next to every number it produces:
  the absent player's measured share is re-allocated to the available teammates in
  proportion to the shares they were already measured at. That is an assumption, not a
  measurement, and the output says so.

COVERAGE, stated rather than hidden: the official box score is per-game HTML and each page
has to be read and transcribed, so this build has complete logs for two games
(2026-11-13 UTA@HOU and 2026-11-11 ORL@UTA): three clubs, UTA with two observations. Every
cell for another club is blank with the reason, not estimated. The ingest path grows it:
each night the refresh job records the box-score URL of every game it settles, so the next
capture pass knows exactly which pages to read.

Run:  python3 -m nba2.v2.rotation
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "player_games.json"
OUT = ROOT / "data" / "v2" / "rotation.json"
TEAM_NAMES_CSV = ROOT / "data" / "arenas.csv"

REDISTRIBUTION_RULE = (
    "An absent player's measured minutes share is re-allocated to that club's available "
    "teammates in proportion to the shares they were measured at in the captured games. "
    "This is a stated modelling assumption (derived), not an official figure: no official "
    "source publishes who would have played the missing minutes."
)


def _secs(mm: str) -> int:
    m, s = mm.split(":")
    return int(m) * 60 + int(s)


def _mmss(n: int) -> str:
    return f"{n // 60}:{n % 60:02d}"


def load_logs() -> dict:
    return json.loads(RAW.read_text()) if RAW.exists() else {"rows": [], "games": {}}


def team_names() -> dict[str, str]:
    """tricode -> full name, from the repo's official-transcription map."""
    from .official import NAMES  # local import: official.py is the transcription layer
    return dict(NAMES)


def _norm(name: str) -> str:
    """'Furphy, Johnny' and 'Johnny Furphy' -> 'johnny furphy'."""
    n = name.strip().lower().replace(".", "")
    if "," in n:
        last, first = [p.strip() for p in n.split(",", 1)]
        return f"{first} {last}"
    return n


def per_team_shares(logs: dict) -> dict[str, dict]:
    """Per club: mean minutes share per player across captured games, plus per-game detail."""
    by_team: dict[str, dict[str, list]] = {}
    games_by_team: dict[str, set] = {}
    for r in logs.get("rows", []):
        if r["status"] != "played" or not r["min"]:
            continue
        by_team.setdefault(r["team"], {}).setdefault(r["player"], []).append(
            {"game_id": r["game_id"], "date": r["date"], "opponent": r["opponent"],
             "home": r["home"], "min": r["min"], "sec": _secs(r["min"]),
             "pts": r["pts"], "reb": r["reb"], "ast": r["ast"],
             "source": r["source"]})
        games_by_team.setdefault(r["team"], set()).add(r["game_id"])

    # team minutes per game = sum of the printed player minutes (checks to 240 in
    # regulation; printed here rather than assumed)
    team_min: dict[tuple[str, str], int] = {}
    for t, players in by_team.items():
        for p, rows in players.items():
            for r in rows:
                team_min[(t, r["game_id"])] = team_min.get((t, r["game_id"]), 0) + r["sec"]

    out: dict[str, dict] = {}
    for t, players in by_team.items():
        n_games = len(games_by_team[t])
        rows = []
        for p, rs in players.items():
            shares = [r["sec"] / team_min[(t, r["game_id"])] for r in rs]
            rows.append({
                "player": p,
                "player_id": next((r for r in logs["rows"] if r["player"] == p
                                   and r.get("player_id")), {}).get("player_id", ""),
                "games": len(rs),
                "mean_minutes": round(sum(r["sec"] for r in rs) / len(rs)),
                "mean_minutes_str": _mmss(int(round(sum(r["sec"] for r in rs) / len(rs)))),
                "mean_share": round(sum(shares) / len(shares), 4),
                "share_low": round(min(shares), 4) if len(shares) > 1 else None,
                "share_high": round(max(shares), 4) if len(shares) > 1 else None,
                "mean_pts": round(sum(r["pts"] for r in rs) / len(rs), 1),
                "mean_reb": round(sum(r["reb"] for r in rs) / len(rs), 1),
                "mean_ast": round(sum(r["ast"] for r in rs) / len(rs), 1),
                "logs": rs,
                "source": rs[0]["source"],
            })
        rows.sort(key=lambda r: -r["mean_share"])
        for i, r in enumerate(rows, 1):
            r["rank"] = i
        out[t] = {
            "team": t,
            "games_captured": n_games,
            "game_ids": sorted(games_by_team[t]),
            "players": rows,
            "top8": rows[:8],
            "top8_share": round(sum(r["mean_share"] for r in rows[:8]), 4),
            "players_used": len(rows),
        }
    return out


def redistribute(team: dict, out_players: list[str]) -> dict:
    """Re-allocate the minutes of `out_players` across the rest of the rotation."""
    names = {_norm(p): p for p in [r["player"] for r in team["players"]]}
    out_keys = {_norm(p) for p in out_players}
    missing = [p for p in out_players if _norm(p) not in names]
    freed = sum(r["mean_share"] for r in team["players"] if _norm(r["player"]) in out_keys)
    pool = [r for r in team["players"] if _norm(r["player"]) not in out_keys]
    base = sum(r["mean_share"] for r in pool)
    rows = []
    for r in pool:
        absorb = freed * (r["mean_share"] / base) if base else 0.0
        rows.append({
            "player": r["player"],
            "baseline_share": r["mean_share"],
            "absorbed_share": round(absorb, 4),
            "projected_share": round(r["mean_share"] + absorb, 4),
            "delta_share": round(absorb, 4),
            "baseline_minutes": r["mean_minutes_str"],
            "baseline_share_pct": round(r["mean_share"] * 100, 1),
            "projected_minutes": _mmss(int(round((r["mean_share"] + absorb) * 240 * 60))),
            "class": "derived",
        })
    return {
        "team": team["team"],
        "out": out_players,
        "out_not_in_captured_rotation": missing,
        "freed_share": round(freed, 4),
        "rule": REDISTRIBUTION_RULE,
        "rows": rows,
        "class": "derived",
    }


def rotation_availability(shares: dict) -> dict:
    """For every club on the official injury report: designations and minutes at risk."""
    from . import official as O

    names = team_names()
    inv = {v: k for k, v in names.items()}
    by_team: dict[str, list] = {}
    for (_, _, _, team_name, player, status, reason, attrib) in O.INJURIES:
        tri = inv.get(team_name, "")
        if not tri:
            continue
        by_team.setdefault(tri, []).append(
            {"player": player, "status": status, "reason": reason,
             "attribution": attrib, "source": O.SOURCES["injury_pdf"][1]})

    rows = []
    for tri in sorted(by_team):
        recs = by_team[tri]
        counted = {"Out": 0, "Doubtful": 0, "Questionable": 0, "Probable": 0,
                   "Available": 0}
        for r in recs:
            if r["status"] in counted:
                counted[r["status"]] += 1
        sh = shares.get(tri)
        at_risk = None
        why = ""
        if sh is None:
            why = ("no captured box score for this club, so its minutes shares are "
                   "unknown and no minutes-at-risk figure can be printed")
        else:
            known = {_norm(p["player"]) for p in sh["players"]}
            out_keys = {_norm(r["player"]) for r in recs
                        if r["status"] in ("Out", "Doubtful")}
            at_risk = round(sum(p["mean_share"] for p in sh["players"]
                                if _norm(p["player"]) in out_keys), 4)
            measured = sorted(out_keys & known)
            unmeasured = sorted(out_keys - known)
            if unmeasured:
                why = (f"{len(measured)} of the {len(out_keys)} ruled-out players have a "
                       f"measured minutes share; the other {len(unmeasured)} did not appear "
                       f"in a captured rotation, so their minutes are unknown and are NOT "
                       f"counted in the figure below")
            elif not out_keys:
                why = "no player ruled out on the latest official report"
        rows.append({
            "team": tri, "team_name": names.get(tri, ""),
            "n_designations": len(recs), **counted,
            "minutes_share_at_risk": at_risk,
            "minutes_at_risk_per_game": _mmss(int(round(at_risk * 240 * 60))) if at_risk is not None else None,
            "games_of_rotation_captured": sh["games_captured"] if sh else 0,
            "note": why,
            "source": O.SOURCES["injury_pdf"][1],
        })
    return {"rows": rows,
            "teams_on_report": len(rows),
            "teams_with_rotation_captured": sum(1 for r in rows if r["games_of_rotation_captured"])}


def coverage(logs: dict, shares: dict) -> dict:
    from . import official as O
    names = team_names()
    inv = {v: k for k, v in names.items()}
    injured = {}
    for (_, _, _, team_name, player, status, reason, _a) in O.INJURIES:
        injured.setdefault(inv.get(team_name, ""), []).append(player)
    covered_players, uncovered = [], []
    for tri, players in injured.items():
        sh = shares.get(tri)
        known = {_norm(p["player"]) for p in sh["players"]} if sh else set()
        for p in players:
            (covered_players if _norm(p) in known else uncovered).append((tri, p))
    return {
        "games_captured": logs.get("n_games", 0),
        "games_in_results_feed": 188,
        "player_rows": logs.get("n_rows", 0),
        "clubs_with_rotation": sorted(shares),
        "clubs_missing_rotation": sorted(set(names) - set(shares)),
        "injured_players_total": sum(len(v) for v in injured.values()),
        "injured_players_with_a_captured_log": len(covered_players),
        "injured_players_covered": [f"{t} {p}" for t, p in sorted(covered_players)],
        "injured_players_not_covered": len(uncovered),
        "why_partial": logs.get("coverage_note", ""),
    }


def build() -> dict:
    logs = load_logs()
    shares = per_team_shares(logs)
    # minutes-redistribution demo uses the club with the most designations on the official
    # report that also has a captured rotation: UTA (7 designations, 2 captured games).
    demo_team = "UTA"
    from . import official as O
    names = team_names()
    inv = {v: k for k, v in names.items()}
    uta_out = [p for (_d, _t, _m, tn, p, st, _r, _a) in O.INJURIES
               if inv.get(tn) == demo_team and st in ("Out", "Doubtful")]
    redis = redistribute(shares[demo_team], uta_out) if demo_team in shares else {}
    return {
        "schema": "nba2.rotation.v1",
        "shares": shares,
        "redistribution_example": redis,
        "rotation_availability": rotation_availability(shares),
        "coverage": coverage(logs, shares),
        "rule": REDISTRIBUTION_RULE,
    }


def main() -> int:
    b = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(b, indent=2) + "\n")
    cov = b["coverage"]
    print("PER-PLAYER GAME LOGS (official box score, line by line)")
    print(f"  games captured: {cov['games_captured']} of {cov['games_in_results_feed']} "
          f"official finals     player rows: {cov['player_rows']}")
    print(f"  clubs with a captured rotation: {', '.join(cov['clubs_with_rotation'])} "
          f"({len(cov['clubs_missing_rotation'])} clubs have none)")
    print(f"  injured players on the official report with a captured log: "
          f"{cov['injured_players_with_a_captured_log']}/{cov['injured_players_total']}")
    for t, s in b["shares"].items():
        print(f"\n  {t} — top-8 minutes shares over {s['games_captured']} captured game(s), "
              f"{s['players_used']} players used, top-8 = {s['top8_share']:.1%}")
        for r in s["top8"]:
            rng = (f"  (range {r['share_low']:.1%}-{r['share_high']:.1%})"
                   if r["share_low"] is not None else "")
            print(f"    {r['rank']}. {r['player']:<20} {r['mean_minutes_str']}  "
                  f"{r['mean_share']:.1%}{rng}   {r['mean_pts']:>4} pts  "
                  f"{r['mean_reb']:>4} reb  {r['mean_ast']:>3} ast")
    red = b["redistribution_example"]
    if red:
        print(f"\nMINUTES REDISTRIBUTION — {red['team']} with {red['out']} out "
              f"(freed {red['freed_share']:.1%} of the rotation)")
        for r in red["rows"]:
            print(f"    {r['player']:<20} {r['baseline_share']:.1%} -> "
                  f"{r['projected_share']:.1%}  ({r['baseline_minutes']} -> "
                  f"{r['projected_minutes']})")
        print("    rule: " + REDISTRIBUTION_RULE[:100] + "...")
    ra = b["rotation_availability"]
    print(f"\nROTATION AVAILABILITY — {ra['teams_on_report']} clubs on the official injury "
          f"report, {ra['teams_with_rotation_captured']} with a captured rotation")
    for r in ra["rows"]:
        risk = (f"{r['minutes_at_risk_per_game']} ({r['minutes_share_at_risk']:.1%})"
                if r["minutes_share_at_risk"] is not None else "unknown")
        print(f"    {r['team']}  out {r['Out']:>2}  q {r['Questionable']:>2}  "
              f"minutes at risk {risk}   {r['note'][:40]}")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
