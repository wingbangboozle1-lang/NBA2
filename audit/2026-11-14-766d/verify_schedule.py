"""Line-by-line check of the 27 published window games against the official capture.

Session arena/766d0269-nba2. Compares date, away, home, game id, venue and the printed ET
time with `nba2/v2/official.py::SLATE`. A field that the capture does not carry is UNVERIFIED,
never assumed equal.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))


def to_et(stamp: str) -> str:
    """'7:00 PM' -> '19:00' (24 h, ET). Pure conversion of the printed string."""
    return datetime.strptime(stamp, "%I:%M %p").strftime("%H:%M")


def parse(md: str):
    out = {}
    for line in md.splitlines():
        if not line.startswith("| 2026-11-"):
            continue
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        date, et, away, home, venue = c[0], c[1], c[2], c[3], c[4]
        gid = c[5]
        out[gid] = {"date": date, "time_et": to_et(et), "away": away, "home": home,
                    "venue": venue, "url": c[6]}
    return out


def main() -> int:
    from nba2.v2 import official as O

    cap = parse((HERE / "schedule_2026-11-14_to_11-17_766d.md").read_text())
    rows, bad = [], []
    for (date, time_et, away, home, gid, arena, city, tv, cup) in O.SLATE:
        c = cap.get(gid)
        if not c:
            rows.append({"game_id": gid, "matchup": f"{away} @ {home}",
                         "verdict": "UNVERIFIED", "detail": "game id absent from capture"})
            bad.append(f"{gid}: absent from capture")
            continue
        checks = {
            "date": (date, c["date"]),
            "time_et": (time_et, c["time_et"]),
            "away": (away, c["away"]),
            "home": (home, c["home"]),
            "arena": (arena, c["venue"]),
        }
        diff = [f"{k}: published {a!r} vs official {b!r}" for k, (a, b) in checks.items() if a != b]
        rows.append({"game_id": gid, "matchup": f"{away} @ {home}", "verdict": "MATCH" if not diff else "MISMATCH",
                     "detail": "; ".join(diff) or "all 6 fields identical",
                     "official_url": c["url"]})
        bad += [f"{gid} {d}" for d in diff]

    ids_only_captured = set(cap) - {r[4] for r in O.SLATE}
    out = {
        "captured_utc": "2026-11-14T19:45:00Z",
        "official_url": "https://www.nba.com/schedule?date=2026-11-14",
        "method": "platform page-fetch tool (direct sandbox egress to nba.com = HTTP 000)",
        "games_published": len(O.SLATE), "games_captured": len(cap),
        "match": sum(1 for r in rows if r["verdict"] == "MATCH"),
        "mismatch": sum(1 for r in rows if r["verdict"] == "MISMATCH"),
        "unverified": sum(1 for r in rows if r["verdict"] == "UNVERIFIED"),
        "captured_but_not_published": sorted(ids_only_captured),
        "differences": bad, "rows": rows,
    }
    (HERE / "schedule_diff_2026-11-14_766d.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=1))
    return 0 if not bad else 4


if __name__ == "__main__":
    sys.exit(main())
