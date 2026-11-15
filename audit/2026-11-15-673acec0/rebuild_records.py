"""Reconstruct every club record from the committed official finals and compare it with
the standings page fetched in this session (2026-11-15).

This is the check that decides whether the snapshot is right: the finals we hold must
reproduce the official W-L and the home/road splits exactly. If they do not, one of the
two documents was mis-read and nothing downstream may be published.
"""
from __future__ import annotations
import glob, json, collections

# standings read from https://www.nba.com/standings in this session (2026-11-15T11:41Z)
# tricode: (W, L, HOME_W, HOME_L, ROAD_W, ROAD_L)
STANDINGS = {
 "BOS": (10,2,5,0,5,2), "PHI": (10,3,5,2,5,1), "DET": (8,4,3,2,5,2), "MIA": (7,6,3,3,4,3),
 "ATL": (7,6,3,3,4,3), "CLE": (7,7,5,2,2,5), "NYK": (6,6,4,3,2,3), "TOR": (5,7,2,3,3,4),
 "ORL": (5,7,1,4,4,3), "IND": (5,8,2,4,3,3), "CHA": (4,8,3,4,1,4), "WAS": (4,9,2,3,2,6),
 "BKN": (3,9,1,3,2,6), "CHI": (3,9,1,4,2,5), "MIL": (1,12,1,6,0,6),
 "SAS": (11,2,5,2,6,0), "LAL": (11,2,5,1,6,1), "HOU": (10,3,7,1,3,2), "POR": (9,3,3,2,6,1),
 "MIN": (9,4,5,2,4,2), "MEM": (9,4,3,4,6,0), "DEN": (7,4,2,2,4,2), "GSW": (8,5,6,1,2,4),
 "OKC": (8,5,5,0,3,5), "DAL": (7,6,5,2,2,4), "PHX": (5,6,5,3,0,3), "NOP": (4,10,3,6,1,4),
 "LAC": (3,8,3,3,0,5), "SAC": (1,11,0,7,1,4), "UTA": (1,12,1,6,0,6),
}

games = []
for p in sorted(glob.glob('data/raw/history/games_*.json')):
    j = json.load(open(p))
    for g in j['games']:
        games.append((g['date'], g['game_id'], g['away'], g['home'],
                      g['away_pts'], g['home_pts']))
print(f"{len(games)} official finals committed under data/raw/history/")

W = collections.Counter(); L = collections.Counter()
HW = collections.Counter(); HL = collections.Counter()
RW = collections.Counter(); RL = collections.Counter()
PF = collections.Counter(); PA = collections.Counter()
for d, gid, aw, hm, ap, hp in games:
    for t, pts, opp in ((aw, ap, hp), (hm, hp, ap)):
        PF[t] += pts; PA[t] += opp
    if ap > hp:
        W[aw] += 1; L[hm] += 1
        if hm == 'HOME': pass
        RW[aw] += 1; HL[hm] += 1
    else:
        W[hm] += 1; L[aw] += 1
        HW[hm] += 1; RL[aw] += 1

rows = []; bad = 0
for t in sorted(STANDINGS):
    sw, sl, hw, hl, rw, rl = STANDINGS[t]
    got = (W[t], L[t], HW[t], HL[t], RW[t], RL[t])
    ok = got == (sw, sl, hw, hl, rw, rl)
    bad += 0 if ok else 1
    gp = W[t] + L[t]
    rows.append((t, f"{sw}-{sl}", f"{W[t]}-{L[t]}", f"{hw}-{hl}", f"{HW[t]}-{HL[t]}",
                 f"{rw}-{rl}", f"{RW[t]}-{RL[t]}", gp,
                 round(PF[t]/gp, 1) if gp else None, round(PA[t]/gp, 1) if gp else None,
                 'MATCH' if ok else 'MISMATCH'))
w = max(len(r[0]) for r in rows)
print(f"{'TEAM':<4} {'OFFICIAL':>9} {'REBUILT':>9} {'OFF HOME':>9} {'REB HOME':>9} "
      f"{'OFF ROAD':>9} {'REB ROAD':>9} {'GP':>3} {'PF/G':>6} {'PA/G':>6}  VERDICT")
for r in rows:
    print(f"{r[0]:<4} {r[1]:>9} {r[2]:>9} {r[3]:>9} {r[4]:>9} {r[5]:>9} {r[6]:>9} "
          f"{r[7]:>3} {str(r[8]):>6} {str(r[9]):>6}  {r[10]}")
tw = sum(W.values()); tl = sum(L.values())
print(f"\nleague identity: sum(W)={tw}  sum(L)={tl}  games={len(games)}  -> {'OK' if tw==tl==len(games) else 'BROKEN'}")
print(f"standings rows compared: {len(rows)}   mismatches: {bad}")

# cross-check the derived PF/G against the PTS column read off nba.com/stats/teams/traditional
SPOT = {"HOU": 116.2, "PHI": 111.2, "POR": 119.6, "MEM": 120.6, "MIN": 118.3,
        "DET": 115.7, "DEN": 114.6, "GSW": 116.7}
print("\nPF/G cross-check vs the official Teams Traditional PTS column (8 clubs read this session):")
for t, v in SPOT.items():
    gp = W[t] + L[t]
    got = round(PF[t]/gp, 1)
    print(f"  {t}: derived {got}  official {v}  delta {round(got-v,2)}  "
          f"{'OK' if abs(got-v) <= 0.15 else 'CHECK'}")

json.dump({t: {"w": W[t], "l": L[t], "home_w": HW[t], "home_l": HL[t], "road_w": RW[t],
               "road_l": RL[t], "pf": round(PF[t]/(W[t]+L[t]), 1), "pa": round(PA[t]/(W[t]+L[t]), 1)}
           for t in STANDINGS},
          open('audit/2026-11-15-673acec0/rebuilt_records.json', 'w'), indent=1)
