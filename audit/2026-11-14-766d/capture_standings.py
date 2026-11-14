"""Verify the published v2 team table against the official NBA.com standings page.

Session arena/766d0269-nba2. The sandbox has no direct egress to nba.com (measured:
HTTP 000 via curl), so the official page is captured out-of-band with the platform
page-fetch tool and pasted verbatim into
`standings_2026-11-14_766d.md` next to this script. This script parses that capture,
compares it field by field with `nba2/v2/official.py` (the table the site publishes),
and writes `standings_diff_2026-11-14_766d.json`.

Nothing is inferred: a team missing from the capture is UNVERIFIED, not a match.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

ROW = re.compile(r"\[\d+<br><br>!\[ Logo\]\([^)]*\)<br><br>([^\]]+)\]\(https://www\.nba\.com/team/(\d+)/")


def parse_capture(text: str) -> dict[str, tuple[int, int, str]]:
    """(wins, losses, nba_team_id) by full team name, from the standings markdown grid."""
    out = {}
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        m = ROW.search(line)
        if not m:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        nums = [c for c in cells[1:] if re.fullmatch(r"\d+", c)]
        if len(nums) < 2:
            continue
        name = m.group(1).strip()
        out.setdefault(name, (int(nums[0]), int(nums[1]), m.group(2)))
    return out


def main() -> int:
    from nba2.v2 import official as O

    cap_path = HERE / "standings_2026-11-14_766d.md"
    if not cap_path.exists():
        print("capture missing:", cap_path)
        return 3
    got = parse_capture(cap_path.read_text(encoding="utf-8"))
    print(f"parsed {len(got)} club rows from the official capture")

    by_name = dict(O.NAMES)  # tricode -> official name
    rows, mism, unver = [], [], []
    for tri, name in sorted(by_name.items()):
        # tricode is the loop key; name is the official full name
        w, l = O.TEAMS[tri][0], O.TEAMS[tri][1]
        if name not in got:
            unver.append(tri)
            rows.append({"tricode": tri, "team": name, "published_w": w, "published_l": l,
                         "official_w": None, "official_l": None, "verdict": "UNVERIFIED"})
            continue
        ow, ol, nid = got[name]
        ok = (ow, ol) == (w, l)
        rows.append({"tricode": tri, "team": name, "published_w": w, "published_l": l,
                     "official_w": ow, "official_l": ol, "nba_team_id": nid,
                     "verdict": "MATCH" if ok else "MISMATCH"})
        if not ok:
            mism.append(f"{tri}: published {w}-{l}, official {ow}-{ol}")

    summary = {
        "captured_utc": "2026-11-14T19:40:00Z",
        "official_url": "https://www.nba.com/standings",
        "method": "platform page-fetch tool (direct sandbox egress to nba.com = HTTP 000)",
        "clubs_in_capture": len(got),
        "clubs_compared": len(rows),
        "match": sum(1 for r in rows if r["verdict"] == "MATCH"),
        "mismatch": len(mism),
        "unverified": len(unver),
        "mismatches": mism,
        "unverified_tricodes": unver,
        "rows": rows,
    }
    (HERE / "standings_diff_2026-11-14_766d.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, indent=1))
    return 0 if not mism else 4


if __name__ == "__main__":
    sys.exit(main())
