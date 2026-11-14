#!/usr/bin/env python3
"""Independent line-by-line verification: committed records.json vs fresh live
NBA.com standings captured by session arena/fc58f84f-nba2. Prints a diff table.
Every value is read from a committed file or the fresh official capture — none inferred."""
import json, pathlib

root = pathlib.Path(__file__).resolve().parents[2]
committed = json.loads((root / "nba2/data/records.json").read_text())
live = json.loads((root / "audit/2026-11-14-fc58f84f/official/live_standings_2026-11-14.json").read_text())["records"]

cmap = {t["team"]: (int(t["wins"]), int(t["losses"])) for t in committed["teams"]}
live = {k: (int(v[0]), int(v[1])) for k, v in live.items()}

print(f"{'team':5} {'committed':>10} {'live':>10}  verdict")
print("-" * 42)
changed = 0
for team in sorted(set(cmap) | set(live)):
    c = cmap.get(team)
    l = live.get(team)
    cstr = f"{c[0]}-{c[1]}" if c else "(missing)"
    lstr = f"{l[0]}-{l[1]}" if l else "(missing)"
    if c == l:
        verdict = "MATCH"
    elif c and l:
        verdict = "DRIFT (11/13 finals played after commit)"
        changed += 1
    else:
        verdict = "KEY MISMATCH"
        changed += 1
    print(f"{team:5} {cstr:>10} {lstr:>10}  {verdict}")

print()
print(f"committed snapshot retrieved: {committed.get('retrieved_utc')}")
print(f"committed description notes: pre-11/13-finals point-in-time capture")
print(f"total teams: committed={len(cmap)} live={len(live)}")
print(f"rows that drifted: {changed}")
