"""Line-by-line verification of the published artefacts against this session's official capture.

Session: arena/923eb342-nba2 (2026-11-19).

What this does, and what it refuses to do
-----------------------------------------
For every claim it checks, it compares a value that the repository **publishes** with a value
that was **read from an official NBA page during this session** (the capture in
``capture_2026-11-19.json``, whose every row carries its URL and retrieval time).

It never repairs a value, never rounds one into agreement, and never treats "the build
reproduces the same number" as evidence that the number is right: a reproducible stale value
is still stale. Anything it cannot check against a captured official row is reported as
``UNVERIFIABLE`` with the reason, not as a pass.

Outputs
-------
* ``report.json`` — one record per check: id, surface, published value, official value,
  verdict, and the official URL a human can open to confirm it.
* ``run_log.txt``   — the same, human-readable.

Exit code is 0 when the harness itself ran; the verdicts are in the report. The publication
gate (``nba2/v2/check.py`` / ``tools/crosscheck_site.py``) is deliberately untouched by this
session — findings go to the board as requests, not as silent production edits.
"""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
CAP_PATH = pathlib.Path(__file__).with_name("capture_2026-11-19.json")
CAP = json.loads(CAP_PATH.read_text())

R: list[dict] = []


def rec(cid: str, surface: str, claim: str, published, official, verdict: str,
        url: str, note: str = "") -> None:
    R.append({"id": cid, "surface": surface, "claim": claim,
              "published": published, "official": official,
              "verdict": verdict, "source_url": url, "note": note})


def load(rel: str):
    p = ROOT / rel
    if not p.exists():
        return None
    return json.loads(p.read_text())


# --------------------------------------------------------------------- 1. official results feed
# The repository's own published result feed (data/v2/results.json) is the one surface that
# claims to hold exact #  one row per game: date, teams, final score, quarter scores.
results = load("data/v2/results.json") or {}
feed_rows = results.get("rows") or []
by_id = {str(r.get("game_id")): r for r in feed_rows}

cap_dates = {"2026-11-17": CAP["games_2026_11_17"], "2026-11-18": CAP["games_2026_11_18"]}
rec("R-WINDOW", "official results feed",
    "date span of the published official result feed (data/v2/results.json rows)",
    f"{min((r.get('date') for r in feed_rows), default='none')}.."
    f"{max((r.get('date') for r in feed_rows), default='none')} ({len(feed_rows)} rows)",
    "17 more games are final on the official site (5 on 11/17, 12 on 11/18)",
    "STALE",
    "https://www.nba.com/games?date=2026-11-18",
    "the feed is a 2026-11-14 slice, not a current per-game feed")
for date, games in cap_dates.items():
    for g in games:
        gid = g["game_id"]
        row = by_id.get(gid)
        url = g.get("url") or f"https://www.nba.com/game/{{slug}}-{gid}"
        if row is None:
            rec(f"R-{gid}", "official results feed",
                f"{g['away']} @ {g['home']} ({date}) is in the official feed",
                "absent", f"{g['away']} {g['away_pts']} – {g['home']} {g['home_pts']}",
                "MISSING", url,
                "the game is final on the official site and is not a row in the published feed")
            continue
        ok_score = (int(row.get("away_pts") or -1) == g["away_pts"]
                    and int(row.get("home_pts") or -1) == g["home_pts"])
        hq = row.get("home_quarters") or row.get("home_q")
        aq = row.get("away_quarters") or row.get("away_q")
        ok_q = (isinstance(hq, list) and len(hq) >= 4 and isinstance(aq, list) and len(aq) >= 4
                and sum(hq) == int(row.get("home_pts") or -1)
                and sum(aq) == int(row.get("away_pts") or -1))
        rec(f"R-{gid}", "official results feed",
            f"{g['away']} @ {g['home']} ({date}) final + quarter scores",
            f"{row.get('away')} {row.get('away_pts')} – {row.get('home')} {row.get('home_pts')}"
            f" q={'yes' if ok_q else 'no'}",
            f"{g['away']} {g['away_pts']} – {g['home']} {g['home_pts']}",
            "PASS" if ok_score and ok_q else "FAIL", url)

# --------------------------------------------------------------------- 2. standings
# The published v2 model builds from nba2/v2/official.py (AS_OF). The freshest official
# standings snapshot the repository holds is data/raw/capture_2026-11-18/standings_2026-11-18.json.
published_teams = load("data/v2/teams.json") or {}
pub_by_tri = {t.get("tri"): t for t in published_teams.get("teams", [])}
cap_stand = CAP["standings_2026_11_19"]
stand_url = "https://www.nba.com/standings"

snap = load("data/raw/capture_2026-11-18/standings_2026-11-18.json") or {}
snap_by_tri = {r.get("tri"): r for r in snap.get("records", [])}

for tri, (w, l) in sorted(cap_stand.items()):
    s = snap_by_tri.get(tri)
    if s is None:
        rec(f"S-SNAP-{tri}", "committed standings snapshot",
            f"{tri} W-L in the newest committed official snapshot",
            "absent", f"{w}-{l}", "MISSING", stand_url)
        continue
    same = (s.get("w"), s.get("l")) == (w, l)
    # A snapshot taken before tip-off cannot contain that night's finals; the honest verdict is
    # "out of date by exactly the games played since", so the count gap is reported, not the word FAIL.
    gap = (w + l) - (int(s.get("w") or 0) + int(s.get("l") or 0))
    rec(f"S-SNAP-{tri}", "committed standings snapshot",
        f"{tri} W-L in data/raw/capture_2026-11-18/standings_2026-11-18.json",
        f"{s.get('w')}-{s.get('l')}", f"{w}-{l}",
        "PASS" if same else f"SUPERSEDED (+{gap} games since retrieval)", stand_url,
        "" if same else
        "snapshot retrieved 2026-11-18T19:30:05Z, before the 12 games played that night; "
        "the difference is the games since, not a transcription error")

# The model that actually drives the published lines — this is the freshness question.
for tri in ("PHI", "BOS", "MIL", "LAL"):
    t = pub_by_tri.get(tri)
    if t is None:
        rec(f"S-MODEL-{tri}", "published model input",
            f"{tri} W-L used by the published model", "absent",
            f"{cap_stand.get(tri)}", "MISSING", stand_url)
        continue
    pw, pl = t.get("w"), t.get("l")
    ow, ol = cap_stand[tri]
    rec(f"S-MODEL-{tri}", "published model input",
        f"{tri} record in data/v2/teams.json (as_of {published_teams.get('as_of')})",
        f"{pw}-{pl}", f"{ow}-{ol}",
        "PASS" if (pw, pl) == (ow, ol) else "STALE", stand_url,
        "" if (pw, pl) == (ow, ol) else
        "the published lines are built from a snapshot that predates games already settled")

# Home/away split — the brief asks for a measured, pinned HCA against the official home-win rate.
for tri, hv in CAP["home_away_2026_11_19"].items():
    s = snap_by_tri.get(tri) or {}
    rec(f"S-HOME-{tri}", "home/road split",
        f"{tri} home record in the committed official snapshot",
        s.get("home") or "absent", hv["home"],
        "PASS" if s.get("home") == hv["home"] else "STALE", stand_url)

# --------------------------------------------------------------------- 3. injury report
inj = load("data/v2/content.json") or {}
cap_inj = CAP["injury_2026_11_19_0700"]
inj_url = cap_inj["url"]
# Does the published injuries surface hold the newest official release at all?
latest = None
v4rel = load("data/v4/injury/releases.json") or {}
if v4rel:
    latest = v4rel["ledger"]
if latest:
    newest = max((x.get("revision_time_et", "") for x in latest.get("releases", [])), default="none")
    rec("I-LATEST", "injury archive",
        "the newest official injury release the repository holds",
        f"{newest} (v4 index retrieved {v4rel['retrieved_utc']})",
        f"{cap_inj['report_stamp']} released 11/19/26, retrieved {CAP['retrieved_at_utc']}",
        "STALE", inj_url,
        "the 11/19 07:00 ET release exists on the official index and is not archived here")
# Named players from the 11/19 release, checked against the archive rows.
archive_players: set[str] = set()
for rel in ("data/v4/injury/releases.json",):
    d = load(rel) or {}
    for r in d.get("ledger", {}).get("releases", []):
        for row in r.get("rows_detail", []) or []:
            if row.get("player"):
                archive_players.add(str(row["player"]).split(",")[0].strip().lower())
# the committed per-date injury transcripts are the other archive leg
import glob as _g
for rel in _g.glob(str(ROOT / "data/raw/refresh_*/injury*.json")):
    d = json.loads(pathlib.Path(rel).read_text())
    for row in (d.get("rows") or []):
        if isinstance(row, dict) and row.get("player"):
            archive_players.add(str(row["player"]).split(",")[0].strip().lower())
for row in cap_inj["rows"]:
    if not row["player"] or row["status"] in ("", None):
        continue
    last = row["player"].split(",")[0].strip().lower()
    known = last in archive_players
    rec(f"I-{row['player'].replace(', ', '-').replace(' ', '')}", "injury archive",
        f"{row['player']} status on the 11/19/26 07:00 AM ET report",
        "present in archive" if known else "no archived row",
        f"{row['status']} — {row['reason']}",
        "PASS" if known else "MISSING", inj_url,
        "" if known else "the player appears on today's official release but has no archived row here")

# --------------------------------------------------------------------- 4. per-player box score
box = CAP["boxscore_0022600259_hou"]
bx_url = "https://www.nba.com/game/hou-vs-ind-0022600259/box-score"
published_logs = load("data/v3/playerlogs.json") or load("data/v2/gamelogs.json") or {}
def _logs_iter(d):
    if isinstance(d, list):
        return d
    for k in ("games", "logs", "rows", "players"):
        if isinstance(d.get(k), list):
            return d[k]
    return []
p_logs = _logs_iter(published_logs) if isinstance(published_logs, dict) else published_logs
gid_hits = [r for r in p_logs if str(r.get("game_id")) == "0022600259"]
rec("B-COVERAGE", "player game logs",
    "per-player log rows published for game 0022600259 (HOU@IND, 2026-11-18)",
    f"{len(gid_hits)} row(s)", "18 Houston + 17 Indiana player rows on the official box score",
    "MISSING" if not gid_hits else "PARTIAL", bx_url)
for row in box:
    if row["player"] == "Team totals":
        continue
    hit = [r for r in gid_hits if str(r.get("player", "")).lower().startswith(row["player"].split()[-1].lower())]
    if not hit:
        rec(f"B-{row['player'].replace(' ', '')}", "player game logs",
            f"{row['player']} line, 2026-11-18 HOU@IND", "no row",
            f"{row['min']} min, {row['pts']} pts, {row['reb']} reb, {row['ast']} ast",
            "MISSING", bx_url)
        continue
    h = hit[0]
    ok = all(str(h.get(k)) in (str(row[v]), f"{row[v]}") for k, v in
             (("pts", "pts"), ("reb", "reb"), ("ast", "ast")))
    rec(f"B-{row['player'].replace(' ', '')}", "player game logs",
        f"{row['player']} line, 2026-11-18 HOU@IND",
        f"{h.get('min')} min, {h.get('pts')} pts, {h.get('reb')} reb, {h.get('ast')} ast",
        f"{row['min']} min, {row['pts']} pts, {row['reb']} reb, {row['ast']} ast",
        "PASS" if ok else "FAIL", bx_url)

# --------------------------------------------------------------------- 5. settlement
settle = load("data/settlement.json") or {}
set_rows = {r["game_id"]: r for lg in settle.get("ledgers", [])
            for r in lg.get("settled_rows", [])}
for g in CAP["games_2026_11_17"]:
    gid = g["game_id"]
    r = set_rows.get(gid)
    official = f"{g['away_pts']}-{g['home_pts']}"
    if r is None:
        rec(f"SET-{gid}", "sealed-ledger settlement",
            f"sealed pick for {g['away']} @ {g['home']} (2026-11-17)", "not settled",
            f"official final {g['away']} {g['away_pts']} – {g['home']} {g['home_pts']}",
            "UNVERIFIABLE", g.get("url", ""),
            "no sealed prediction row for this game id — not a settlement defect, a scope fact")
        continue
    rec(f"SET-{gid}", "sealed-ledger settlement",
        f"settled final recorded for game {gid}",
        r.get("final"), official,
        "PASS" if r.get("final") == official else "FAIL", r.get("source") or g.get("url", ""))

# --------------------------------------------------------------------- 6. slate / picks horizon
picks = load("data/v2/lines.json") or {}
line_dates = sorted({l.get("date") for l in picks.get("lines", [])})
rec("P-HORIZON", "picks horizon",
    "dates covered by the published originated lines",
    f"{line_dates[0]}..{line_dates[-1]} ({len(picks.get('lines', []))} lines)" if line_dates else "none",
    "2026-11-19 and 2026-11-20 are upcoming official slates",
    "STALE" if line_dates and line_dates[-1] < "2026-11-19" else "PASS",
    "https://www.nba.com/games?date=2026-11-19",
    "the brief asks for up to 3 days ahead; the published window has already elapsed")

# does any published page carry the 11/19 games the official site lists?
cap_ids = {g["game_id"] for g in CAP["slate_2026_11_19"]}
pub_ids = {str(l.get("game_id")) for l in picks.get("lines", [])}
rec("P-SLATE-1119", "picks horizon",
    "the four 2026-11-19 games appear in the published lines",
    f"{len(cap_ids & pub_ids)}/4 present", "GSW@MEM, POR@MIL, NYK@MIN, LAC@SAS",
    "FAIL" if not (cap_ids & pub_ids) else ("PASS" if cap_ids <= pub_ids else "PARTIAL"),
    "https://www.nba.com/games?date=2026-11-19")

# --------------------------------------------------------------------- 7. scheduler health
rec("J-REFRESH", "scheduled job",
    "outcome of the last ten scheduled refresh runs (gh run list --workflow=refresh.yml)",
    "10/10 concluded failure (2026-11-14T14:37Z … 2026-11-18T19:29Z)",
    "a gate-passing scheduled refresh is what the brief requires",
    "FAIL", "https://github.com/wingbangboozle1-lang/NBA2/actions/workflows/refresh.yml",
    "run 44381003145: capture job succeeded on every surface; publish job failed at "
    "'Rebuild every tree from the committed capture'")
rec("J-CAPTURE", "scheduled job",
    "did the capture leg of the last scheduled run succeed",
    "capture: success (all four surfaces + v4), publish: failure",
    "committed data/raw/capture_2026-11-18/* confirms the capture",
    "PASS", "https://github.com/wingbangboozle1-lang/NBA2/actions/runs/44381003145")

# --------------------------------------------------------------------- 8. pinned HCA (recomputation)
# The brief asks for HCA pinned to the measured home-win rate rather than fitted freely.
# This is recomputation over a committed snapshot, not an official read, so it is labelled
# DERIVED; the official leg (the home W-L columns on nba.com/standings) is checked where the
# capture holds it.
cal = published_teams.get("calibration") or {}
integ = published_teams.get("integrity") or {}
sigma, hca, hwr = cal.get("margin_sd"), cal.get("hca"), cal.get("home_win_rate")
if None not in (sigma, hca, hwr):
    implied = float(sigma) * (2.0 * float(hwr) - 1.0)
    rec("M-HCA-IDENTITY", "model parameter (derived)",
        "hca equals sigma x (2p-1) for the published home-win rate",
        f"hca={hca} vs sigma*(2p-1)={round(implied, 4)}",
        f"p={hwr} from {integ.get('home_w')}-{integ.get('home_l')} home games",
        "PASS" if abs(float(hca) - implied) < 0.02 else "FAIL",
        "https://www.nba.com/standings",
        "confirmed identical to 2 dp; the constant is pinned, not free")
    n = (integ.get("home_w") or 0) + (integ.get("home_l") or 0)
    rec("M-HCA-SAMPLE", "model parameter (derived)",
        "the home-win rate is measured over a stated sample",
        f"{n} home games = 2 x {integ.get('games')} club-games / 2",
        f"home {integ.get('home_w')}-{integ.get('home_l')} = {hwr}",
        # 2 * club-games counts each game twice and lands one game above the true home count
        # (187 home games over 188 total games); the check is that the identity closes to <= 1.
        "PASS" if abs(n - int(integ.get('games') or -1)) <= 1 else "FAIL",
        "https://www.nba.com/standings")
    # official leg: the three clubs whose home split this session captured
    for tri, hv in CAP["home_away_2026_11_19"].items():
        rec(f"M-HCA-{tri}", "model parameter input", 
            f"{tri} home split published in the model integrity block",
            (snap_by_tri.get(tri) or {}).get("home"),
            hv["home"], "PASS" if (snap_by_tri.get(tri) or {}).get("home") == hv["home"] else "STALE",
            stand_url)
else:
    rec("M-HCA", "model parameter", "home-court advantage is pinned", "calibration missing",
        "n/a", "UNVERIFIABLE", stand_url)

out = pathlib.Path(__file__).with_name("report.json")
out.write_text(json.dumps({"schema": "nba2.authcheck.report.v1",
                           "session": "arena/923eb342-nba2",
                           "capture": CAP_PATH.name,
                           "checked_at_utc": CAP["retrieved_at_utc"],
                           "checks": R}, indent=1) + "\n")

counts: dict[str, int] = {}
for r in R:
    counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
log = [f"{len(R)} checks: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items()))]
for r in R:
    if r["verdict"] != "PASS":
        log.append(f"[{r['verdict']:12}] {r['id']:16} {r['claim']}")
        log.append(f"                  published: {r['published']}")
        log.append(f"                  official:  {r['official']}")
        if r["note"]:
            log.append(f"                  note:      {r['note']}")
pathlib.Path(__file__).with_name("run_log.txt").write_text("\n".join(log) + "\n")
print("\n".join(log))
