#!/usr/bin/env python3
"""Pick gate for the 3-day window.

A game can receive a PICK only if ALL of these exist in data/verified/:
  * a strategy family with gate status PASSED in strategy_gates.json,
  * an originated line for that game in lines.json (model output, with timestamp and model version),
  * a timestamped market price in lines.json from a permitted source.
Nothing in this repository currently satisfies these, so every game is written as NO PICK
with the blockers that apply. No odds, lines, or probabilities are invented here.
Stdlib only. Run: python3 tools/generate_picks.py
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "verified"
sched = json.loads((DATA / "schedule_2026-11-13_to_16.json").read_text(encoding="utf-8"))
inj = json.loads((DATA / "injuries_2026-11-13_0515PM.json").read_text(encoding="utf-8"))
gates_path = DATA / "strategy_gates.json"
gates = json.loads(gates_path.read_text(encoding="utf-8"))["families"] if gates_path.exists() else []
lines_path = DATA / "lines.json"
lines = json.loads(lines_path.read_text(encoding="utf-8")).get("lines", []) if lines_path.exists() else []
line_by_game = {l["game_id"]: l for l in lines}
passed = [g for g in gates if g["gate_status"] == "PASSED"]
has_injury_snapshot = {r["matchup"] for r in inj["rows"]} | {r["matchup"] for r in inj["team_status_rows"]}

rows = []
for g in sched["rows"]:
    blockers = []
    line = line_by_game.get(g["game_id"])
    if not line:
        blockers.append("No originated line for this game (no model output in repository)")
    if not passed:
        blockers.append("No strategy family has passed validation gates (0 of %d evaluated as PASSED)" % len(gates))
    if not (line and line.get("price_source")):
        blockers.append("No timestamped market price from a permitted source")
    if g["date"] == "2026-11-13" and g["matchup"] in has_injury_snapshot:
        blockers.append("Rotation-minute impact of injuries unverified (no official minutes baseline)")
    elif g["date"] > "2026-11-13":
        blockers.append("Official injury report for this date not yet published in the snapshot used")
    status = "PICK" if not blockers else "NO PICK"
    row = {"game_id": g["game_id"], "date": g["date"], "tip_et": g["tip_et"], "matchup": g["matchup"],
           "status": status, "blockers": blockers, "schedule_source": g["source_url"]}
    if status == "PICK":
        row.update({"validated_strategy_id": line["strategy_id"], "line_source": line["line_source"],
                    "price_source": line["price_source"]})
    rows.append(row)

out = {"generated_from": ["data/verified/schedule_2026-11-13_to_16.json", "data/verified/injuries_2026-11-13_0515PM.json",
                          "data/verified/strategy_gates.json", "data/verified/lines.json (absent => no lines)"],
       "as_of": "2026-11-13", "picks_issued": sum(1 for r in rows if r["status"] == "PICK"),
       "games": len(rows), "rows": rows}
(DATA / "picks_gate_status.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
print("games:", len(rows), "picks issued:", out["picks_issued"])
