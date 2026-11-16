#!/usr/bin/env python3
"""Team-stat pages verification — session arena/3cd85a22-nba2 (brief item #22).

Re-read the three official NBA.com team-stat pages (traditional, opponent, advanced)
live on 2026-11-16 and compare the model-critical fields against the committed
`data/raw/refresh_2026-11-16/team_stats_2026-11-16.json` capture (09:30 ET). The live
values below are transcribed from the official pages read this session; the script
flags any mismatch, so a transcription slip would surface as a MISMATCH.

Run:  python3 verified/session-3cd85a22-live/verify_team_stats.py
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "verified", "session-3cd85a22-live", "team_stats_results.json")

def load(p):
    with open(os.path.join(ROOT, p)) as f:
        return json.load(f)

committed = load("data/raw/refresh_2026-11-16/team_stats_2026-11-16.json")
adv_c = {r["tri"]: r for r in committed["pages"]["advanced"]["rows"]}
opp_c = {r["tri"]: r for r in committed["pages"]["opponent"]["rows"]}
trad_c = {r["tri"]: r for r in committed["pages"]["traditional"]["rows"]}

# Live values transcribed from the official pages read 2026-11-16T18:23:30Z.
# advanced: tri -> (off_rtg, def_rtg, net_rtg, pace, poss)
live_adv = {
 "LAL":(122.1,114.0,8.0,100.64,1408), "SAS":(119.2,106.6,12.6,98.77,1395),
 "BOS":(118.9,105.1,13.9,96.53,1263), "HOU":(121.2,110.7,10.5,97.68,1367),
 "PHI":(112.3,110.3,2.0,100.21,1404), "MEM":(119.0,110.4,8.5,100.46,1318),
 "MIN":(116.0,104.5,11.5,101.27,1326), "OKC":(113.4,108.4,5.1,98.82,1384),
 "POR":(118.8,111.1,7.7,100.67,1208), "ATL":(112.8,111.1,1.7,103.69,1462),
 "DET":(114.1,109.2,4.9,99.48,1217), "GSW":(116.1,112.0,4.1,99.66,1307),
 "CLE":(116.9,115.4,1.6,99.72,1407), "DAL":(111.8,114.5,-2.7,100.18,1404),
 "DEN":(116.0,114.7,1.3,97.67,1087), "MIA":(114.7,116.2,-1.5,102.49,1345),
 "NYK":(113.7,108.2,5.5,95.66,1257), "IND":(110.9,112.9,-2.0,101.25,1415),
 "ORL":(109.7,113.4,-3.7,98.23,1185), "PHX":(114.3,118.5,-4.2,98.79,1183),
 "TOR":(113.6,112.2,1.4,99.55,1302), "CHA":(102.5,113.6,-11.1,96.65,1256),
 "LAC":(111.4,115.3,-3.9,100.05,1210), "NOP":(111.3,120.0,-8.6,101.83,1457),
 "WAS":(109.4,116.5,-7.1,99.73,1416), "BKN":(109.8,116.0,-6.2,99.47,1204),
 "CHI":(109.4,120.3,-10.9,103.81,1257), "MIL":(105.4,118.9,-13.6,100.68,1410),
 "SAC":(106.8,119.8,-13.0,101.08,1312), "UTA":(105.1,116.2,-11.1,100.22,1426),
}
# opponent: tri -> opp_pts (points allowed per game)
live_opp = {
 "LAL":114.9,"SAS":105.9,"BOS":102.4,"HOU":108.2,"PHI":110.4,"MEM":111.7,
 "MIN":106.8,"OKC":107.1,"POR":111.8,"ATL":116.1,"DET":110.3,"GSW":112.4,
 "CLE":115.9,"DAL":114.6,"DEN":112.8,"MIA":119.8,"NYK":104.0,"IND":114.5,
 "ORL":112.8,"PHX":117.3,"TOR":112.8,"CHA":109.8,"LAC":116.5,"NOP":124.9,
 "WAS":118.0,"BKN":116.4,"CHI":125.9,"MIL":119.7,"SAC":121.2,"UTA":118.0,
}
# traditional: tri -> pts
live_trad = {
 "LAL":122.8,"SAS":118.8,"BOS":115.5,"HOU":118.4,"PHI":112.6,"POR":119.6,
 "MEM":120.6,"MIN":118.3,"DET":115.7,"OKC":112.1,"DEN":114.6,"GSW":116.7,
 "ATL":117.8,"MIA":118.7,"NYK":109.9,"CLE":117.5,"DAL":112.1,"ORL":108.3,
 "PHX":112.7,"TOR":113.8,"IND":112.1,"LAC":112.3,"CHA":99.1,"NOP":115.9,
 "WAS":110.6,"BKN":110.2,"CHI":114.6,"SAC":107.8,"MIL":106.1,"UTA":107.1,
}

def cmp(tri, cval, lval, label, tol=0.01):
    if cval is None:
        return {"team": tri, "field": label, "result": "COMMITTED_BLANK", "live": lval}
    if abs(float(cval) - float(lval)) > tol:
        return {"team": tri, "field": label, "result": "MISMATCH", "committed": cval, "live": lval}
    return {"team": tri, "field": label, "result": "MATCH", "committed": cval, "live": lval}

advanced_checks, opponent_checks, traditional_checks = [], [], []
for tri in sorted(live_adv):
    a = live_adv[tri]
    c = adv_c[tri]
    for field, cval, lval in zip(("off_rtg","def_rtg","net_rtg","pace","poss"),
                                 (c["off_rtg"],c["def_rtg"],c["net_rtg"],c["pace"],c["poss"]), a):
        advanced_checks.append(cmp(tri, cval, lval, field))
    opponent_checks.append(cmp(tri, opp_c[tri]["opp_pts"], live_opp[tri], "opp_pts"))
    traditional_checks.append(cmp(tri, trad_c[tri]["pts"], live_trad[tri], "pts"))

def summary(checks):
    return {"n": len(checks), "match": sum(1 for x in checks if x["result"]=="MATCH"),
            "mismatch": [x for x in checks if x["result"]=="MISMATCH"]}

result = {
    "session": "arena/3cd85a22-nba2",
    "retrieved_utc": "2026-11-16T18:23:30Z",
    "sources": {
        "advanced": "https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame",
        "opponent": "https://www.nba.com/stats/teams/opponent?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame",
        "traditional": "https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame",
    },
    "committed_capture": "data/raw/refresh_2026-11-16/team_stats_2026-11-16.json (retrieved 2026-11-16T14:30:00Z / 09:30 ET)",
    "advanced": summary(advanced_checks),
    "opponent": summary(opponent_checks),
    "traditional": summary(traditional_checks),
}
with open(OUT, "w") as f:
    json.dump(result, f, indent=1)

print("=== ADVANCED (5 fields x 30) ===", summary(advanced_checks))
print("=== OPPONENT (opp_pts x 30) ===", summary(opponent_checks))
print("=== TRADITIONAL (pts x 30) ===", summary(traditional_checks))
for name, checks in (("advanced",advanced_checks),("opponent",opponent_checks),("traditional",traditional_checks)):
    for x in checks:
        if x["result"] != "MATCH":
            print("  ", name, x)
print("Wrote", OUT)
