"""Count and classify the official 01:30 PM ET injury release, and diff it against the
published 04:30 AM ET snapshot the site was built from.

Session arena/766d0269-nba2. Reads the committed capture (verbatim transcription of the PDF,
`injury_2026-11-14_0130PM_766d.md`) and `nba2/v2/official.py::INJURIES`, and reports:
  * how many player-status rows the later release carries, by status;
  * which teams had filed and which had not;
  * every row present in one release and not the other;
  * every player whose STATUS differs between the two releases.

No value is inferred. A player absent from one release is reported absent, never defaulted.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

STATUSES = ("Out", "Doubtful", "Questionable", "Probable", "Available")


def parse_capture(text: str):
    """Rows from the capture: (date, time, matchup, team, player, status, reason, carried)."""
    rows = []
    team_carry = ""
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) < 7:
            continue
        date, tm, mu, team, player, status, reason = c[0], c[1], c[2], c[3], c[4], c[5], c[6]
        if status not in STATUSES and status != "NOT YET SUBMITTED":
            continue
        if player in ("Player Name", "") and status != "NOT YET SUBMITTED":
            continue
        # '—' is the capture's marker for "the extraction did not print this cell".
        date = None if date in ("—", "") else date
        tm = None if tm in ("—", "") else tm
        mu = None if mu in ("—", "") else mu
        player = None if player in ("—", "") else player
        if team:
            team_carry = team
        rows.append({"date": date, "time": tm, "matchup": mu,
                     "team": team or team_carry, "player": player,
                     "status": status, "reason": None if reason in ("—", "") else reason,
                     "team_cell_present": bool(team)})
    return rows


def strip_carry(s: str) -> str:
    return re.sub(r"\s*\(carried[^)]*\)$", "", s).strip()


def main() -> int:
    from nba2.v2 import official as O

    cap = parse_capture((HERE / "injury_2026-11-14_0130PM_766d.md").read_text())
    player_rows = [r for r in cap if r["status"] in STATUSES]
    nys = [r for r in cap if r["status"] == "NOT YET SUBMITTED"]

    by_status = Counter(r["status"] for r in player_rows)
    filed_teams = {strip_carry(r["team"]) for r in player_rows}
    nys_teams = {strip_carry(r["team"]) for r in nys}

    # What the site publishes: the 04:30 AM release, transcribed into official.py.
    published = [{"matchup": m, "team": t, "player": p, "status": s, "reason": r}
                 for (_d, _tm, m, t, p, s, r, _a) in O.INJURIES]

    def key(row):
        return (row.get("team", ""), row.get("player", ""))

    pub_by_key = {}
    for r in published:
        pub_by_key.setdefault((strip_carry(r["team"]), r["player"]), []).append(r["status"])
    cap_by_key = {}
    for r in player_rows:
        cap_by_key.setdefault((strip_carry(r["team"]), r["player"]), []).append(r["status"])

    only_pub = sorted(k for k in pub_by_key if k not in cap_by_key)
    only_cap = sorted(k for k in cap_by_key if k not in pub_by_key)
    changed = sorted(k for k in pub_by_key if k in cap_by_key and pub_by_key[k] != cap_by_key[k])

    out = {
        "captured_utc": "2026-11-14T19:50Z",
        "official_url": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_01_30PM.pdf",
        "index_url": "https://official.nba.com/nba-injury-report-2026-27-season/",
        "document_header": "Injury Report: 11/14/26 01:30 PM",
        "method": "platform page-fetch tool; index page fetched the same session to confirm the URL",
        "player_status_rows_later_release": len(player_rows),
        "by_status": dict(by_status),
        "teams_with_a_filing": len(filed_teams),
        "teams_not_yet_submitted": len(nys_teams),
        "not_yet_submitted_club_slots": len(nys),
        "dates_covered": sorted({r["date"] for r in player_rows if r["date"]}),
        "published_snapshot_release": "11/14/26 04:30 AM ET",
        "published_player_rows": len(published),
        "players_only_in_published_snapshot": [list(k) for k in only_pub],
        "players_only_in_later_release": [list(k) for k in only_cap],
        "players_with_different_status": [{"team": k[0], "player": k[1],
                                          "published": pub_by_key[k], "later_release": cap_by_key[k]}
                                         for k in changed],
        "verdict": ("no status changes on shared rows" if not changed else
                    f"{len(changed)} status change(s) on shared rows"),
    }
    (HERE / "injury_diff_2026-11-14_766d.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
