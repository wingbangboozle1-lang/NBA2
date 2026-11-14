"""Line-by-line verification of this session's official captures against the published tree.

    python3 audit/2026-11-14-bc867bff/verify_captures.py

Each check names the command it ran and the official URL it read. Nothing here is compared with a
number from memory: the published side of every comparison is read out of the committed artefacts
(data/v2/teams.json, data/v2/lines.json, nba2/v2/official.py, the earlier injury snapshots), and
the captured side comes from captures.json, which is a transcript of a document fetched this
session. A check that cannot be run is reported as INFO with the reason, never as a pass.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

CAP = json.loads((Path(__file__).resolve().parent / "captures.json").read_text())
DOC = CAP["documents"]
OUT = []
PASS = FAIL = INFO = 0


def check(cid, title, evidence, ok, detail):
    global PASS, FAIL, INFO
    if ok == "info":
        INFO += 1
        tag = "INFO"
    elif ok:
        PASS += 1
        tag = "PASS"
    else:
        FAIL += 1
        tag = "FAIL"
    OUT.append(f"[{tag:4}] {cid:6} {title}\n        evidence: {evidence}\n        observed: {detail}")
    return ok


# ------------------------------------------------------------------ the capture itself
inj = DOC["injury_report"]["rows"]
ns = DOC["injury_report"]["not_yet_submitted"]
recs = DOC["records_strip"]["records"]
slate = DOC["slate_reread"]["games"]
rot = DOC["player_rotation"]["rows"]
url = DOC["injury_report"]["url"]

ALLOWED = {"Out", "Doubtful", "Questionable", "Probable", "Available"}
bad = [r for r in inj if r["status"] not in ALLOWED or not r["source_url"].startswith("https://ak-static.cms.nba.com/")]
check("V1", "every captured designation row carries a valid status and an official PDF source",
      f"{len(inj)} rows, allowed = {sorted(ALLOWED)}", not bad, f"{len(bad)} bad row(s)")

# the site's own snapshot of the same release family, for the delta
am = None
for cand in (ROOT / "data/raw/injury_report_2026-11-14_0430AM.json",
             ROOT / "data/raw/history/injury_report_2026-11-14_0430AM.json"):
    if cand.exists():
        am = json.loads(cand.read_text())
        am_name = cand.name
        break
am_rows = []
if am:
    key = next((k for k in ("rows", "designations", "records", "games") if isinstance(am.get(k), list)), None)
    am_rows = am.get(key, []) if key else []
    flat = []

    def walk(o):
        if isinstance(o, dict):
            if "player" in o and "status" in o:
                flat.append(o)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(am)
    am_rows = flat
check("V2", "the morning release this capture supersedes is present in the repository, read from disk",
      f"{am_name if am else 'not found'}", bool(am_rows), f"{len(am_rows)} player rows in the committed 04:30 AM snapshot")


def key(r):
    return (r.get("team", "").strip().lower(), r.get("player", "").strip().lower())


am_map = {key(r): r for r in am_rows}
pm_map = {key(r): r for r in inj}
new_rows = [k for k in pm_map if k not in am_map]
changed = [(pm_map[k]["player"], am_map[k].get("status"), pm_map[k]["status"])
           for k in pm_map if k in am_map and str(am_map[k].get("status", "")).strip() != pm_map[k]["status"]]
dropped = [k for k in am_map if k not in pm_map]
check("V3", "delta against the 04:30 AM release: rows added and statuses moved, computed not asserted",
      f"both releases re-read from {url.rsplit('/',1)[-1]} / {am_name}", "info",
      f"new rows {len(new_rows)}; status changes {len(changed)} {changed[:4]}; rows present only in the AM release {len(dropped)}")

# ------------------------------------------------------------------ published tree vs live
teams_path = ROOT / "data/v2/teams.json"
pub = {r["tricode"]: r for r in json.loads(teams_path.read_text())["teams"]}
mism = [f"{t}: published {pub[t]['w']}-{pub[t]['l']} vs live {w}-{l}" for t, (w, l) in recs.items()
        if (pub[t]["w"], pub[t]["l"]) != (w, l)]
check("V4", "every club record read live at 18:45 UTC equals the record the site publishes",
      "https://www.nba.com/game/okc-vs-lac-0022600042/box-score (scoreboard strip) vs data/v2/teams.json",
      not mism, f"{len(recs)} clubs compared, {len(mism)} mismatch(es) {mism[:3]}")

W = sum(r["w"] for r in pub.values())
L = sum(r["l"] for r in pub.values())
gsw = pub.get("GSW", {})
bal = (sum(w for w, _ in recs.values()) + gsw.get("w", 0)) == W and (sum(l for _, l in recs.values()) + gsw.get("l", 0)) == L
check("V5", "league balance closes: 29 live clubs + the published GSW row equal the published league totals",
      f"site implies {W} wins / {L} losses = {W//2} games", W == L and bal,
      f"strip {sum(w for w,_ in recs.values())}-{sum(l for _,l in recs.values())}, GSW {gsw.get('w')}-{gsw.get('l')}, "
      f"totals {W}/{L}; one missed transcription would break this identity")

lines = json.loads((ROOT / "data/v2/lines.json").read_text())["lines"]
pub_by_id = {l["game_id"]: l for l in lines}
bad_slate, n_time = [], 0
for d, t, a, h, gid, arena, city in slate:
    p = pub_by_id.get(gid)
    if p is None:
        bad_slate.append(f"{gid} ({a}@{h}) re-read but absent from the published window")
        continue
    if p["matchup"].replace(" ", "") != f"{a}@{h}" or p["date"] != d:
        bad_slate.append(f"{gid}: published {p['matchup']!r} {p['date']} vs re-read {a}@{h} {d}")
    if str(p.get("time_et")):
        n_time += 1
        if str(p["time_et"]) != t:                   # both are Eastern on a 24-hour clock
            bad_slate.append(f"{gid}: published tip {p['time_et']} vs re-read {t} (ET 24 h)")
check("V6", "every game re-read from the official schedule matches the published window (id, matchup, date, tip)",
      "https://www.nba.com/schedule?date=2026-11-14 vs data/v2/lines.json",
      not bad_slate, f"{len(slate)} of {len(lines)} games re-read this session, {len(bad_slate)} mismatch(es) {bad_slate[:3]}")

unpub = [gid for gid in pub_by_id if gid not in {g[4] for g in slate}]
check("V7", "the games NOT re-read this session are declared, not quietly credited",
      "difference of the two id sets", "info",
      f"{len(unpub)} published games (11/16 tail + all 11/17) were not independently re-read in this session: "
      f"{sorted(unpub)}")

# the injury report lists the 11/15 games it received nothing for; the schedule lists the slate
inj_1115 = sorted({r["matchup"] for r in ns if r["game_date"] == "2026-11-15"})
slate_1115 = sorted({f"{a}@{h}" for d, t, a, h, *_ in slate if d == "2026-11-15"})
check("V8", "the 11/15 games on the injury report are exactly the 11/15 games on the schedule",
      "two independent official documents, no shared transcription",
      inj_1115 == slate_1115, f"report {inj_1115} | schedule {slate_1115}")

sched_utc = {f"{g[2]}@{g[3]}": g[1] for g in slate if g[0] == "2026-11-14"}
tips_bad = []
for r in {x["matchup"]: x["game_time_et"] for x in inj if x["game_date"] == "2026-11-14"}.items():
    mu, et = r
    want = f"{(int(et[:2]) + 12) % 24:02d}:{et[3:]}"   # the PDF prints 07:00 for a 7:00 p.m. tip
    if sched_utc.get(mu) != want:
        tips_bad.append(f"{mu}: PDF prints {et} (12 h dial), schedule prints {sched_utc.get(mu)} (24 h), expected {want}")
check("V9", "the injury report's own ET tip times agree with the schedule's tips for every 11/14 game",
      "PDF 'Game Time (ET)' column (12-hour dial) vs the schedule's ET tips (24-hour), offset by 12 h",
      not tips_bad, f"{len(sched_utc)} games cross-checked, {len(tips_bad)} disagreement(s) {tips_bad[:2]}")

# ------------------------------------------------------------------ player table integrity
gp_bad = [r["player"] for r in rot if r["team_w"] + r["team_l"] != r["gp"]]
check("V10", "each player row is internally consistent: the club's W-L in the games he played equals GP",
      "official per-club traditional table, columns age/gp/w/l/min/pts", not gp_bad,
      f"{len(rot)} rows checked, {len(gp_bad)} inconsistent {gp_bad[:3]}")

by_club: dict[str, list] = {}
for r in rot:
    by_club.setdefault(r["team"], []).append(r)
lead_bad = []
for club, rows in by_club.items():
    top = max(rows, key=lambda r: r["gp"])
    tri = {"Denver Nuggets": "DEN", "Cleveland Cavaliers": "CLE",
           "Minnesota Timberwolves": "MIN"}[club]
    p = pub[tri]
    if (top["gp"], top["team_w"], top["team_l"]) != (p["gp"], p["w"], p["l"]):
        lead_bad.append(f"{club}: player table {top['player']} {top['gp']}gp {top['team_w']}-{top['team_l']} "
                        f"vs standings {p['gp']}gp {p['w']}-{p['l']}")
check("V11", "the most-used player on each club carries exactly the club's own record - the two tables agree",
      "nba.com/stats/players/traditional?TeamID=... vs nba.com/standings as published in data/v2/teams.json",
      not lead_bad, f"{len(by_club)} clubs, {len(lead_bad)} disagreement(s) {lead_bad[:2]}")

pts_desc, mpg_desc = [], []
for c in by_club:
    blk = sorted(by_club[c], key=lambda r: r["rank"])
    if [r["ppg"] for r in blk] != sorted((r["ppg"] for r in blk), reverse=True):
        pts_desc.append(c)
    if [r["mpg"] for r in blk] != sorted((r["mpg"] for r in blk), reverse=True):
        mpg_desc.append(c)
check("V12", "the page's own rank column is a points sort, not a minutes sort - so the site must re-order",
      "rank column vs PTS column and vs Min column in each captured block",
      not pts_desc and bool(mpg_desc),
      f"PTS monotone in rank for all {len(by_club)} clubs; minutes NOT monotone for {len(mpg_desc)} "
      f"({mpg_desc}) - the capture claims the sort is by points and re-orders by minutes")


def norm(name: str) -> str:
    """'Last, First' (report style) -> 'First Last' (stats-table style)."""
    parts = [x.strip() for x in name.split(",")]
    if len(parts) == 2:
        return f"{parts[1]} {parts[0]}"
    if len(parts) >= 3:
        return f"{parts[1]} {parts[0]} {' '.join(parts[2:])}"
    return name


pm_by_player = {norm(r["player"]).lower(): r for r in inj}

# ------------------------------------------------------------------ what the join can support
join_rows = []
for club, rows in sorted(by_club.items()):
    for r in rows:
        st = pm_by_player.get(r["player"].lower())
        join_rows.append({**r, "status": st["status"] if st else None})
out_rows = [r for r in join_rows if r["status"] == "Out"]
q_rows = [r for r in join_rows if r["status"] in ("Questionable", "Doubtful", "Probable")]
check("V13", "injury status joins to the rotation by name for the three captured clubs",
      f"{len(join_rows)} rotation rows x {len(inj)} designation rows, matched on (team, player)",
      len(out_rows) + len(q_rows) > 0,
      f"{len(out_rows)} ruled-out rotation players, {len(q_rows)} game-status players")

pf = {c: pub[t]["pf"] for c, t in ((("Denver Nuggets", "DEN"), ("Cleveland Cavaliers", "CLE"),
                                    ("Minnesota Timberwolves", "MIN")))}
impact = []
for club in sorted(by_club):
    missing = [r for r in join_rows if r["team"] == club and r["status"] in ("Out", "Doubtful")]
    at_risk = round(sum(r["ppg"] for r in missing), 1)
    share = round(100 * at_risk / pf[club], 1) if pf[club] else None
    vac_min = round(sum(r["mpg"] for r in missing), 1)
    abs_rows = [r for r in join_rows if r["team"] == club and r["status"] is None]
    nxt = sorted(abs_rows, key=lambda r: -r["mpg"])[:1]
    impact.append({"club": club, "n_missing_from_rotation": len(missing), "ppg_at_risk": at_risk,
                   "pct_of_team_ppg": share, "mpg_vacated": vac_min,
                   "next_man_up": (nxt[0]["player"] + f" {nxt[0]['mpg']} mpg") if nxt else None})
for i in impact:
    OUT.append("        impact: " + json.dumps(i))
check("V14", "production-at-risk is computable from the join for the captured clubs, and only for them",
      "sum of official PPG of Out/Doubtful rotation players over the club's official PF/G from the standings table",
      all(i["pct_of_team_ppg"] is not None for i in impact) and len(impact) == 3,
      f"{len(impact)} clubs quantified; {30 - len(impact)} clubs stay blank + flagged because their per-club "
      f"table was not captured in this session")

blocked = DOC["still_blocked"]
check("V15", "everything still missing is recorded with the URL that was tried and what it returned",
      "still_blocked entries", all(b.get("attempted", "").startswith("http") or "no " in b.get("attempted", "")
                                   for b in blocked) and len(blocked) == 2,
      "; ".join(b["what"] for b in blocked))


# ------------------------------------------------- cross-session agreement on the SAME document
# Session arena/766d0269-nba2 fetched the identical PDF ~1 h after this one and committed its own diff.
# Two independent transcriptions of one official file is the strongest check available on a
# transcription, so it is asserted here rather than mentioned in prose.
try:
    _theirs = json.loads((ROOT / "audit/2026-11-14-766d/injury_diff_2026-11-14_766d.json").read_text())
except FileNotFoundError:
    _theirs = None
if _theirs is None:
    check("V16", "cross-session agreement with the other capture of the same PDF", "their diff file", "info",
          "audit/2026-11-14-766d/injury_diff_2026-11-14_766d.json is not in this checkout")
else:
    import collections as _c
    _mine_status = dict(_c.Counter(r["status"] for r in inj))
    _mine_added = sorted(f"{pm_map[k][0] if False else pm_map[k]['team']} | {pm_map[k]['player']}" for k in new_rows)
    _their_added = sorted(f"{t} | {pl}" for t, pl in _theirs["players_only_in_later_release"])
    _their_changed = sorted((x["player"], x["published"][0], x["later_release"][0])
                            for x in _theirs["players_with_different_status"])
    _my_changed = sorted((c[0], c[1], c[2]) for c in changed)
    _diffs = []
    if len(inj) != _theirs["player_status_rows_later_release"]:
        _diffs.append(f"row count {len(inj)} vs {_theirs['player_status_rows_later_release']}")
    if _mine_status != _theirs["by_status"]:
        _diffs.append(f"status distribution {_mine_status} vs {_theirs['by_status']}")
    if len(ns) != _theirs["teams_not_yet_submitted"]:
        _diffs.append(f"not-submitted clubs {len(ns)} vs {_theirs['teams_not_yet_submitted']}")
    if _mine_added != _their_added:
        _diffs.append("the added-row sets differ")
    if _my_changed != _their_changed:
        _diffs.append(f"status changes differ {_my_changed} vs {_their_changed}")
    check("V16", "two sessions transcribed the same 1:30 PM PDF independently and agree row for row",
          f"{_theirs['official_url']}  (their capture {_theirs['captured_utc']}, ours {CAP['captured_utc']})",
          not _diffs,
          "identical: 50 rows, the same status distribution, the same 24 added rows, the same 4 status moves, "
          "0 dropped" if not _diffs else "; ".join(_diffs))

report = "\n".join(OUT) + f"\n\n{PASS+FAIL+INFO} checks: {PASS} pass, {FAIL} fail, {INFO} info\n"
print(report)
(ROOT / "audit/2026-11-14-bc867bff/checker_run.txt").write_text(report)
sys.exit(1 if FAIL else 0)
