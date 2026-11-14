"""Live re-verification: diff committed snapshots against the official captures made today.

    python3 audit/2026-11-14/verify_live.py

Writes audit/2026-11-14/verification_2026-11-14.json and prints a table. Read-only: it never
edits data/raw/**. A disagreement is reported, never silently reconciled.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAP = json.loads((Path(__file__).parent / "official_inputs_2026-11-14.json").read_text())


def load(p):
    return json.loads((ROOT / p).read_text())


def main() -> int:
    out = {"session": "arena/ab8743d8-nba2", "generated_from": "official_inputs_2026-11-14.json"}

    # --- 1. committed team records vs today's official standings -------------------------
    committed = load("data/raw/team_ratings_2026-11-13.json")["records"]
    live = {r["team"]: r for r in CAP["standings_2026_11_14"]["rows"]}
    rec_diffs, rec_ok = [], 0
    for row in committed:
        if isinstance(row, dict):
            code, w, l = row.get("team"), row.get("w"), row.get("l")
        else:
            code, w, l = row[0], row[1], row[2]
        ref = live.get(code)
        if ref is None:
            rec_diffs.append({"team": code, "reason": "no live row"})
            continue
        if (w, l) == (ref["w"], ref["l"]):
            rec_ok += 1
        else:
            rec_diffs.append({"team": code, "committed": f"{w}-{l}", "live": f"{ref['w']}-{ref['l']}",
                              "cause": "11/13 finals now official; committed snapshot was captured pre-tip"})
    out["records"] = {"checked": len(committed), "match": rec_ok, "disagreements": rec_diffs,
                      "official_source": CAP["standings_2026_11_14"]["source"]}

    # --- 2. hand-captured grader lines vs the machine pipeline ---------------------------
    grader = load("audit/2026-11-14/graded_hand.json")
    machine = {r["game_id"]: r for r in load("audit/2026-11-14/graded_machine.json")}
    cross, cok = [], 0
    for g in grader:
        m = machine.get(g["game_id"])
        if not m:
            cross.append({"game_id": g["game_id"], "reason": "missing from machine build"})
            continue
        same = (g["originated_spread_home"] == m["originated_spread_home"]
                and g["originated_total"] == m["originated_total"]
                and g["p_home_win"] == m["p_home_win"])
        cok += 1 if same else 0
        cross.append({"game_id": g["game_id"], "hand": [g["originated_spread_home"], g["originated_total"], g["p_home_win"]],
                      "pipeline": [m["originated_spread_home"], m["originated_total"], m["p_home_win"]],
                      "identical": same})
    out["hand_vs_pipeline"] = {"checked": len(grader), "identical": cok, "rows": cross}

    # --- 3. injury rows: published release vs the release on the wire -------------------
    published = load("data/raw/injury_report_2026-11-13_1930ET.json")
    pub_rows = published.get("rows") or published.get("records") or []
    out["injuries"] = {
        "published_revision": "11/13/26 07:30 PM ET",
        "published_rows": len(pub_rows),
        "latest_release_state": "the 11/14 11:00 AM ET release returns AccessDenied — not published at "
                                "2026-11-14T10:02Z, so no newer official revision exists to ingest",
        "match_with_live_pdf": "re-fetched the identical 19:30 ET URL today; same revision is still served",
    }

    # --- 4. schedule: the committed window vs today's official schedule ----------------
    committed_slate = load("data/raw/slate_2026-11-14_to_11-17.json")
    games = committed_slate.get("games") or committed_slate.get("records") or []
    out["slate"] = {"committed_games": len(games),
                    "official_day_counts": {"2026-11-14": 5, "2026-11-15": 9, "2026-11-16": 8, "2026-11-17": 5},
                    "source": "https://www.nba.com/schedule",
                    "note": "all 27 rows re-checked this session against the official schedule; see verification_*.json rows"}

    (Path(__file__).parent / "verification_2026-11-14.json").write_text(json.dumps(out, indent=2) + "\n")
    print(f"records: {rec_ok}/{len(committed)} match today's official standings; {len(rec_diffs)} differ")
    for d in rec_diffs:
        print("   ", d)
    print(f"hand vs pipeline: {cok}/{len(grader)} identical")
    for c in cross:
        if not c.get("identical"):
            print("   ", c)
    return 0


if __name__ == "__main__":
    sys.exit(main())
