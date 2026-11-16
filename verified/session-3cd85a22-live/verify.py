#!/usr/bin/env python3
"""Independent live verification for session arena/3cd85a22-nba2.

Re-derives the published headline numbers from the committed official captures and
compares the committed artefacts against the fresh official captures taken this session
(fetched live from nba.com / official.nba.com on 2026-11-16). Nothing is inferred: a
value that cannot be confirmed is left blank and flagged.

Run:  python3 verified/session-3cd85a22-live/verify.py
"""
import json, glob, os, statistics, math
from statistics import NormalDist

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LIVE = os.path.join(ROOT, "verified", "session-3cd85a22-live")
OUT = os.path.join(LIVE, "verification_results.json")

def load(p):
    with open(os.path.join(ROOT, p)) as f:
        return json.load(f)

def norm_game(g):
    """Normalise a game record to the common shape used for re-derivation."""
    return {
        "game_id": g.get("game_id"),
        "date": g.get("date"),
        "away": g.get("away"),
        "home": g.get("home"),
        "away_pts": g.get("away_pts"),
        "home_pts": g.get("home_pts"),
        "neutral_site": bool(g.get("neutral_site", False)),
        "ot": bool(g.get("ot", g.get("ot_periods", 0) or False)),
    }

# ---------------------------------------------------------------- 1. build the 197-game pool
games = []
for f in sorted(glob.glob(os.path.join(ROOT, "data/raw/history/games_*.json"))):
    d = load("data/raw/history/" + os.path.basename(f))
    for g in d.get("games", []):
        games.append(norm_game(g))
# 11/14 finals (5)
d = load("data/raw/capture_2026-11-15/results_2026-11-14.json")
for g in d.get("records", []):
    games.append(norm_game(g))
# 11/15 finals (9)
d = load("data/raw/refresh_2026-11-15/results_2026-11-15.json")
for g in d.get("records", []):
    games.append(norm_game(g))

# de-dup by game_id, keep first
seen = {}
for g in games:
    if g["game_id"] and g["game_id"] not in seen:
        seen[g["game_id"]] = g
pool = list(seen.values())

# ---------------------------------------------------------------- 2. re-derive headline numbers
non_neutral = [g for g in pool if not g["neutral_site"]]
home_wins = sum(1 for g in non_neutral if g["home_pts"] > g["away_pts"])
n_home = len(non_neutral)
home_win_rate = home_wins / n_home if n_home else None
margins = [g["home_pts"] - g["away_pts"] for g in non_neutral]
margin_mean = statistics.mean(margins)
margin_sd = statistics.stdev(margins) if len(margins) > 1 else 0.0
hca = margin_sd * NormalDist().inv_cdf(home_win_rate) if home_win_rate else None
totals = [g["home_pts"] + g["away_pts"] for g in non_neutral]

def corr(xs, ys):
    n = len(xs)
    if n < 2:
        return None
    mx, my = statistics.mean(xs), statistics.mean(ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    return sxy / math.sqrt(sxx * syy) if sxx and syy else None

rho = corr(margins, totals)

# compare to the committed v4 model
v4 = load("data/v4/model.json")
v4hc = v4["home_court"]
v4rho = v4["rho"]

def close(a, b, tol=0.02):
    if a is None or b is None:
        return False
    return abs(a - b) <= tol

# ---------------------------------------------------------------- 3. standings comparison
committed_st = load("data/raw/refresh_2026-11-16/standings_2026-11-16.json")
live_st = load("verified/session-3cd85a22-live/live_standings_2026-11-16.json")
cmap = {r["tri"]: r for r in committed_st["rows"]}
lmap = {r["tri"]: r for r in live_st["rows"]}
standings_checks = []
for tri in sorted(set(cmap) | set(lmap)):
    c, l = cmap.get(tri), lmap.get(tri)
    if c is None:
        standings_checks.append({"team": tri, "result": "ONLY_IN_LIVE", "detail": "present in live, absent in committed"})
        continue
    if l is None:
        standings_checks.append({"team": tri, "result": "ONLY_IN_COMMITTED", "detail": "present in committed, absent in live"})
        continue
    diffs = []
    if (c["w"], c["l"]) != (l["w"], l["l"]):
        diffs.append(f"W-L {c['w']}-{c['l']} vs {l['w']}-{l['l']}")
    for k in ("home", "road", "neutral", "ot", "last10"):
        if c[k] != l[k]:
            diffs.append(f"{k} {c[k]} vs {l[k]}")
    standings_checks.append({
        "team": tri,
        "committed": f"{c['w']}-{c['l']} (home {c['home']}, road {c['road']})",
        "live": f"{l['w']}-{l['l']} (home {l['home']}, road {l['road']})",
        "result": "MATCH" if not diffs else "MISMATCH",
        "diffs": diffs,
    })
standings_match = sum(1 for c in standings_checks if c["result"] == "MATCH")

# ---------------------------------------------------------------- 4. slate comparison
committed_sl = load("data/raw/refresh_2026-11-16/slate_2026-11-16_to_11-19.json")
live_sl = load("verified/session-3cd85a22-live/live_slate_2026-11-16.json")
cgames = {g["game_id"]: g for g in committed_sl["games"]}
lgames = {g["game_id"]: g for g in live_sl["games"]}
slate_checks = []
for gid in sorted(set(cgames) | set(lgames)):
    c, l = cgames.get(gid), lgames.get(gid)
    if c is None or l is None:
        slate_checks.append({"game_id": gid, "result": "ONLY_IN_ONE_SOURCE"})
        continue
    diffs = []
    for k in ("date", "away", "home", "time_et", "arena"):
        if c.get(k) != l.get(k):
            diffs.append(f"{k}: {c.get(k)!r} vs {l.get(k)!r}")
    slate_checks.append({
        "game_id": gid, "matchup": c.get("matchup"),
        "result": "MATCH" if not diffs else "MISMATCH", "diffs": diffs,
    })
slate_match = sum(1 for c in slate_checks if c["result"] == "MATCH")

# ---------------------------------------------------------------- 5. injury release freshness diff
committed_inj = load("data/raw/refresh_2026-11-16/injury_transcript_20261116_0930AM.json")
live_inj = load("verified/session-3cd85a22-live/live_injury_report_2026-11-16_0100PM.json")

# normalise team full-name -> tri on both sides so the keys are comparable
name2tri = {}
for r in committed_st["rows"]:
    name2tri[r["name"]] = r["tri"]
def tri_of(team_name):
    return name2tri.get(team_name, team_name)

c_recs = {}
for r in committed_inj["records"]:
    # r = [date, time, matchup, team_full_name, player, status, reason, extra]
    if len(r) >= 5 and r[4]:
        c_recs[(r[2], tri_of(r[3]), r[4])] = r
l_recs = {}
for r in live_inj["rows"]:
    if r.get("player"):
        l_recs[(r["matchup"], r["team"], r["player"])] = r
injury_new = [k for k in l_recs if k not in c_recs]
injury_gone = [k for k in c_recs if k not in l_recs]
injury_changed = []
for k in sorted(set(l_recs) & set(c_recs)):
    cst = c_recs[k][5] if len(c_recs[k]) > 5 else None
    lst = l_recs[k].get("status")
    if cst != lst:
        injury_changed.append({"matchup": k[0], "team": k[1], "player": k[2], "committed_status": cst, "live_status": lst})

# ---------------------------------------------------------------- 6. assemble result
result = {
    "session": "arena/3cd85a22-nba2",
    "retrieved_utc": "2026-11-16T18:23:30Z",
    "sources": {
        "standings": "https://www.nba.com/standings",
        "schedule": "https://www.nba.com/schedule?date=2026-11-16",
        "injury_index": "https://official.nba.com/nba-injury-report-2026-27-season/",
        "injury_pdf": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-16_01_00PM.pdf",
    },
    "history_pool": {
        "n_games_total": len(pool),
        "n_non_neutral": n_home,
        "n_neutral_excluded": len(pool) - n_home,
    },
    "rederived": {
        "home_wins": home_wins,
        "home_win_rate": round(home_win_rate, 4) if home_win_rate else None,
        "margin_mean": round(margin_mean, 3),
        "margin_sd": round(margin_sd, 3),
        "hca_points": round(hca, 3) if hca is not None else None,
        "rho": round(rho, 4) if rho is not None else None,
        "n_rho": len(margins),
    },
    "v4_model_published": {
        "home_wins": v4hc["home_wins"],
        "home_win_rate": v4hc["home_win_rate"],
        "margin_sd": v4hc["margin_sd"],
        "hca_points": v4hc["hca_points"],
        "rho": v4rho["r"],
        "n_rho": v4rho["n"],
    },
    "headline_match": {
        "home_win_rate": close(home_win_rate, v4hc["home_win_rate"], 0.001),
        "margin_sd": close(margin_sd, v4hc["margin_sd"], 0.05),
        "hca_points": close(hca, v4hc["hca_points"], 0.02),
        "rho": close(rho, v4rho["r"], 0.005),
    },
    "standings": {"n": len(standings_checks), "match": standings_match, "checks": standings_checks},
    "slate": {"n": len(slate_checks), "match": slate_match, "checks": slate_checks},
    "injury": {
        "committed_release": committed_inj.get("report_stamp_et"),
        "committed_retrieved_utc": committed_inj.get("retrieved_at_utc"),
        "committed_n_records": len(committed_inj.get("records", [])),
        "live_release": live_inj["release"]["revision_et"],
        "live_retrieved_utc": live_inj["retrieved_utc"],
        "live_n_rows": len(live_inj["rows"]),
        "new_rows_in_live": [{"matchup": k[0], "team": k[1], "player": k[2]} for k in injury_new],
        "rows_gone_from_committed": [{"matchup": k[0], "team": k[1], "player": k[2]} for k in injury_gone],
        "status_changes": injury_changed,
    },
}

with open(OUT, "w") as f:
    json.dump(result, f, indent=1)

# console summary
print("=== HEADLINE RE-DERIVATION ===")
print(json.dumps(result["rederived"], indent=1))
print("V4 published:", json.dumps(result["v4_model_published"]))
print("Match flags:", json.dumps(result["headline_match"]))
print()
print(f"=== STANDINGS: {standings_match}/{len(standings_checks)} MATCH ===")
for c in standings_checks:
    if c["result"] != "MATCH":
        print("  ", c)
print(f"=== SLATE: {slate_match}/{len(slate_checks)} MATCH ===")
for c in slate_checks:
    if c["result"] != "MATCH":
        print("  ", c)
print("=== INJURY DIFF ===")
print("committed:", result["injury"]["committed_release"], "retrieved", result["injury"]["committed_retrieved_utc"], "n=", result["injury"]["committed_n_records"])
print("live:", result["injury"]["live_release"], "retrieved", result["injury"]["live_retrieved_utc"], "n=", result["injury"]["live_n_rows"])
print("new rows in live:", len(result["injury"]["new_rows_in_live"]))
print("status changes:", len(result["injury"]["status_changes"]))
for c in result["injury"]["status_changes"]:
    print("  ", c)
print("Wrote", OUT)
