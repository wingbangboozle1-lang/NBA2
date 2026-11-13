#!/usr/bin/env python3
"""
NBA2 line-origination model v1.0 (2026-11-13)

Reads verified data from data/*.csv and produces OUR OWN game lines, player-prop
projections, picks, parlays and the luck ledger. Every input row carries its
source in the data files; every output row carries the source of its game.

Model parameters (documented assumptions, NOT verified facts - see
analysis/strategy/model.md and the questions register):
  HCA                = 2.0 margin pts  (modern NBA home edge ~1.5-2.5; book avg ~2.05)
  STAR_OUT           = 4.0 margin pts  (player PPG >= 24 missing)
  STARTER_OUT        = 2.0             (15 <= PPG < 24 missing)
  ROTATION_OUT       = 0.8             (PPG < 15 or unknown missing)
  status multipliers: Out 1.0, Doubtful 0.9, Questionable 0.5, Probable 0.1
  injury cap         = 8.0 margin pts per team
  B2B penalty        = -0.6 home / -1.1 road ; 3-in-4 adds -0.7 (road -1.0)
  conviction side    = |predicted margin| >= 4.0 after all adjustments
  conviction total   = |predicted total - league mean| >= 5.0
  prop defense adj   = (opp DRtg/A - league mean DRtg/A) * 0.35 added to opp-allowed proxy

Pure stdlib. Deterministic. No network.
"""
import csv, math, os
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

HCA = 2.0
STAR_OUT, STARTER_OUT, ROTATION_OUT = 4.0, 2.0, 0.8
STATUS_MULT = {"Out": 1.0, "Doubtful": 0.9, "Questionable": 0.5, "Probable": 0.1}
INJ_CAP = 8.0
B2B_HOME, B2B_ROAD = -0.6, -1.1
TIRED3IN4_HOME, TIRED3IN4_ROAD = -0.7, -1.0
SIDE_THRESHOLD = 4.0
TOTAL_THRESHOLD = 5.0
PROP_DEF_FACTOR = 0.35


def read(name):
    with open(os.path.join(DATA, name), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def w(name, rows, fields):
    with open(os.path.join(DATA, name), "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=fields)
        wr.writeheader()
        for r in rows:
            wr.writerow(r)


ratings = {r["team"]: r for r in read("team-ratings-2026-11-13.csv")}
games = read("games.csv")
injuries = read("injury-report-2026-11-13.csv")

# baselines: ppg lookup by (team, player) for injury tiering + team leader for props
ppg_of = {}
leader = {}
for r in read("player-baselines-2026-11-13.csv"):
    if r.get("ppg"):
        ppg_of[(r["team"], r["player"])] = float(r["ppg"])
        if r["team"] not in leader or float(r["ppg"]) > float(leader[r["team"]]["ppg"]):
            leader[r["team"]] = r
recent = read("recent-games.csv")

# ---- league averages (from the ratings table itself) -----------------------
lg_ortg = sum(float(r["ortg_adj"]) for r in ratings.values()) / len(ratings)
lg_drtg = sum(float(r["drtg_adj"]) for r in ratings.values()) / len(ratings)
lg_total = lg_ortg + lg_drtg  # baseline combined score level (per-100 approx)

# ---- rest: last known game date per team ----------------------------------
last_game = {}
for r in recent:
    d = date.fromisoformat(r["date"])
    for t in (r["away"], r["home"]):
        last_game[t] = max(last_game.get(t, d), d)


# games by team within the 4-day slate window (for 3-in-4 detection)
slate_by_team = {}
for g in games:
    gd = date.fromisoformat(g["date"])
    for t in (g["away"], g["home"]):
        slate_by_team.setdefault(t, []).append(gd)


def fatigue_adj(team, game_date):
    """returns (label, margin adjustment) from B2B / 3-in-4 with travel."""
    lg = last_game.get(team)
    label_parts, adj = [], 0.0
    gap = (game_date - lg).days if lg else 99
    if lg and gap == 1:
        label_parts.append("B2B")
    # 3 games in 4 days within known window (recent + slate)
    dates = sorted(set(d for d in slate_by_team.get(team, []) if d <= game_date) | ({lg} if lg else set()))
    window = [d for d in dates if (game_date - d).days <= 3]
    if len(window) >= 3:
        label_parts.append("3in4")
    if not label_parts:
        return "rested", 0.0
    is_road = any(g["away"] == team and date.fromisoformat(g["date"]) == game_date for g in games)
    if "B2B" in label_parts:
        adj += B2B_ROAD if is_road else B2B_HOME
    if "3in4" in label_parts:
        adj += TIRED3IN4_ROAD if is_road else TIRED3IN4_HOME
    return "+".join(label_parts), adj


# ---- injury impact per team per game --------------------------------------
def injury_impact(matchup, team_full):
    """returns (impact pts on margin, note, players_out_names)"""
    impact, names = 0.0, []
    for r in injuries:
        if r["matchup"] != matchup or r["team"] != team_full:
            continue
        if r["status"] not in STATUS_MULT:
            continue  # Available / NOT YET SUBMITTED / G-League only rows
        reason = r["reason"]
        if reason.startswith("G League"):
            continue  # two-way / assignment absences: negligible NBA rotation impact
        # tier by verified PPG when possible
        abbr = TEAM_FULL_TO_ABBR.get(team_full, "")
        ppg = ppg_of.get((abbr, r["player"]))
        if ppg is not None and ppg >= 24:
            wgt = STAR_OUT
        elif ppg is not None and ppg >= 15:
            wgt = STARTER_OUT
        else:
            wgt = ROTATION_OUT
        share = wgt * STATUS_MULT[r["status"]]
        impact += share
        if STATUS_MULT[r["status"]] >= 0.5:
            names.append(f'{r["player"]} ({r["status"]})')
    return min(impact, INJ_CAP), names


TEAM_FULL_TO_ABBR = {
    "Orlando Magic": "ORL", "Indiana Pacers": "IND", "Atlanta Hawks": "ATL",
    "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE", "Miami Heat": "MIA",
    "Memphis Grizzlies": "MEM", "New Orleans Pelicans": "NOP", "Utah Jazz": "UTA",
    "Houston Rockets": "HOU", "Golden State Warriors": "GSW", "San Antonio Spurs": "SAS",
    "Portland Trail Blazers": "POR", "Sacramento Kings": "SAC",
    "Oklahoma City Thunder": "OKC", "LA Clippers": "LAC", "Denver Nuggets": "DEN",
    "Dallas Mavericks": "DAL", "Brooklyn Nets": "BKN", "Minnesota Timberwolves": "MIN",
    "Detroit Pistons": "DET", "Boston Celtics": "BOS", "Washington Wizards": "WAS",
    "Philadelphia 76ers": "PHI", "Toronto Raptors": "TOR",
}
ABBR_TO_FULL = {v: k for k, v in TEAM_FULL_TO_ABBR.items()}

# ---- generate our lines ---------------------------------------------------
lines, picks, parlays = [], [], []
for g in games:
    a, h = g["away"], g["home"]
    gd = date.fromisoformat(g["date"])
    ra, rh = ratings[a], ratings[h]
    m_a, m_h = float(ra["nrtg_adj"]), float(rh["nrtg_adj"])
    inj_a, names_a = injury_impact(f"{a}@{h}", ABBR_TO_FULL.get(a, ""))
    inj_h, names_h = injury_impact(f"{a}@{h}", ABBR_TO_FULL.get(h, ""))
    fat_a, fatv_a = fatigue_adj(a, gd)
    fat_h, fatv_h = fatigue_adj(h, gd)
    margin_home = (m_h - m_a) + HCA - inj_h + inj_a + fatv_h - fatv_a
    total = lg_total + ((float(rh["ortg_adj"]) + float(ra["drtg_adj"])) / 2 - lg_ortg) \
        + ((float(ra["ortg_adj"]) + float(rh["drtg_adj"])) / 2 - lg_ortg) \
        - (inj_h + inj_a) * 0.35
    margin_r = round(margin_home * 2) / 2
    total_r = round(total * 2) / 2
    src = g["source_url"]
    line = {
        "date": g["date"], "game_id": g["game_id"], "away": a, "home": h,
        "our_spread_home": f"{-margin_r:+.1f}", "our_total": f"{total_r:.1f}",
        "pred_margin_home": f"{margin_home:+.2f}", "pred_total": f"{total:.2f}",
        "away_nrtg_adj": m_a, "home_nrtg_adj": m_h,
        "away_injury_impact": f"{inj_a:.1f}", "home_injury_impact": f"{inj_h:.1f}",
        "away_injury_names": "; ".join(names_a[:6]), "home_injury_names": "; ".join(names_h[:6]),
        "away_rest": fat_a, "home_rest": fat_h, "source_url": src,
    }
    lines.append(line)

    side = None
    if margin_r >= SIDE_THRESHOLD:
        side = (h, f"{h} {-margin_r:+.1f}")          # home favorite covers our number
    elif margin_r <= -SIDE_THRESHOLD:
        side = (a, f"{a} {margin_r:+.1f}")           # away favorite (margin_r negative)
    inj_status = "official snapshot 2026-11-13 5:15PM ET" if g["date"] <= "2026-11-14" else "PENDING - official report due day before game (line is injury-unadjusted)"
    if side:
        picks.append({
            "date": g["date"], "game_id": g["game_id"], "strategy": "S1 originate-side",
            "bet_type": "spread", "pick": side[1], "our_line": f"{-margin_r:+.1f} (home)",
            "conviction": f"|margin| {abs(margin_r):.1f} >= {SIDE_THRESHOLD}",
            "make_at": "our number or better vs market (market feed pending - see Q-1)",
            "injury_data_status": inj_status, "source_url": src,
        })
    total_pick = None
    if total_r >= lg_total + TOTAL_THRESHOLD:
        total_pick = f"Over {total_r:.1f}"
    elif total_r <= lg_total - TOTAL_THRESHOLD:
        total_pick = f"Under {total_r:.1f}"
    if total_pick:
        picks.append({
            "date": g["date"], "game_id": g["game_id"], "strategy": "S2 originate-total",
            "bet_type": "total", "pick": total_pick, "our_line": f"{total_r:.1f}",
            "conviction": f"proj total {total_r:.1f} vs league mean {lg_total:.1f}",
            "make_at": "our number or better vs market (market feed pending - see Q-1)",
            "injury_data_status": inj_status, "source_url": src,
        })

    # S3 correlated pairs, built only on documented correlation directions:
    #   Pair A: game-total lean + same-direction team-total lean (r +0.40..0.60)
    #   Pair B: favorite cover + favorite star pts Over, competitive games only
    #           (|margin| <= 10; r +0.35..0.45 team win + star pts, SBOC)
    if abs(total_r - lg_total) >= 4.0:
        direction = "Over" if total_r > lg_total else "Under"
        # team-total leg: pick the offense with the bigger scoring projection
        ta = (float(ratings[a]["ortg_adj"]) + float(ratings[h]["drtg_adj"])) / 2
        th = (float(ratings[h]["ortg_adj"]) + float(ratings[a]["drtg_adj"])) / 2
        tt_team, tt_val = (a, ta) if ta >= th else (h, th)
        parlays.append({
            "date": g["date"], "game_id": g["game_id"], "strategy": "S3a total-flow-pair",
            "legs": f"Game total {direction} {total_r:.1f} | {tt_team} team total {direction} {tt_val:.1f}",
            "correlation_basis": "Game total + team total same direction: r +0.40..0.60 (gamblingcalc.com)",
            "cap": "max 2 legs same game; spread+ML same team banned (r~0.9)",
            "injury_data_status": inj_status, "source_url": src,
        })
    if 4.0 <= abs(margin_r) <= 10.0:
        fav = h if margin_r > 0 else a
        fb = leader.get(fav)
        fav_inj = injury_impact(f"{a}@{h}", ABBR_TO_FULL.get(fav, ""))[1]
        if fb and not any(fb["player"].split(",")[0] in n for n in fav_inj):
            proj = float(fb["ppg"])
            parlays.append({
                "date": g["date"], "game_id": g["game_id"], "strategy": "S3b star-stack",
                "legs": f"{fav} -{abs(margin_r):.1f} | {fb['player']} pts Over {proj:.1f}",
                "correlation_basis": "Team win + star pts over in competitive games: r +0.35..0.45 (SBOC); only when spread < 11",
                "cap": "max 2 legs same game; banned when |our margin| >= 11 (blowout risk r -0.20..-0.40)",
                "injury_data_status": inj_status, "source_url": src,
            })

# S4 prop lines for verified baselines in games with flow lean
props = []
for g in games:
    gd = date.fromisoformat(g["date"])
    for team in (g["away"], g["home"]):
        b = leader.get(team)
        if not b or not b.get("ppg"):
            continue
        opp = g["home"] if team == g["away"] else g["away"]
        opp_drtg = float(ratings[opp]["drtg_adj"])
        def_adj = (opp_drtg - lg_drtg) * PROP_DEF_FACTOR
        proj_pts = float(b["ppg"]) + def_adj
        proj = round(proj_pts * 2) / 2
        flow = float(ratings[team]["nrtg_adj"]) - float(ratings[opp]["nrtg_adj"])
        side = "Over-leaning" if def_adj > 0.4 else ("Under-leaning" if def_adj < -0.4 else "neutral")
        avail = "available (status checked in official report)" if any(
            r["matchup"] == f"{g['away']}@{g['home']}" and r["player"].split(",")[0] in b["player"] and r["status"] in STATUS_MULT
            for r in injuries) else "status not in current report (treat as available)"
        props.append({
            "date": g["date"], "game_id": g["game_id"], "team": team, "player": b["player"],
            "prop": "points", "our_line": f"{proj:.1f}", "baseline_ppg": b["ppg"],
            "opp_def_adj": f"{def_adj:+.2f}", "flow_lean": side,
            "make_at": f"Over only at {proj - 1.5:.1f} or better; Under only at {proj + 1.5:.1f}+ (1.5pt model buffer)",
            "availability": avail, "source_url": g["source_url"], "baseline_source": b["source_url"],
        })
        if abs(def_adj) >= 0.9 or flow >= 6:
            parlays.append({
                "date": g["date"], "game_id": g["game_id"], "strategy": "S4 prop-combo",
                "legs": f"{b['player']} pts Over {proj:.1f} ({team}) | game total {'Over' if def_adj > 0 else 'Under'} lean",
                "correlation_basis": "Team total over + player pts over +0.15..0.25 (gamblingcalc); game under + player props over -0.30..-0.50 (SBOC) - direction must agree",
                "cap": "1 prop + 1 game leg max; big-favorite star props banned when spread >= 11 (r -0.20..-0.40)",
                "injury_data_status": "official snapshot 2026-11-13 5:15PM ET" if g["date"] <= "2026-11-14" else "PENDING - official report due day before game",
                "source_url": g["source_url"],
            })

# ---- luck ledger (expected vs actual record) ------------------------------
luck = []
for t, r in sorted(ratings.items()):
    g_played = int(r["wins"]) + int(r["losses"])
    nrtg = float(r["nrtg_adj"])
    exp_wp = 1 / (1 + math.exp(-nrtg / 6.8))
    exp_w = exp_wp * g_played
    actual_w = int(r["wins"])
    luck.append({
        "team": t, "wins": r["wins"], "losses": r["losses"],
        "nrtg_adj": f"{nrtg:+.2f}", "expected_wins": f"{exp_w:.1f}",
        "luck_component_wins": f"{actual_w - exp_w:+.1f}",
        "note": "positive = record ahead of rating-based expectation (luck or clutch)",
        "source_url": r["source_url"],
    })

# ---- leaderboard seed -----------------------------------------------------
leaderboard = [
    {"strategy": "S1 originate-side", "focus": "single bets: spread", "picks_logged": 0,
     "record": "0-0", "raw_roi": "", "process_rating": "n/a (pre-sample)", "gate_status": "provisional - gates G1,G4 pass; G2 sample pending",
     "reward_points": "0", "rules": "analysis/strategy/leaderboard.md"},
    {"strategy": "S2 originate-total", "focus": "single bets: total", "picks_logged": 0,
     "record": "0-0", "raw_roi": "", "process_rating": "n/a (pre-sample)", "gate_status": "provisional - gates G1,G4 pass; G2 sample pending",
     "reward_points": "0", "rules": "analysis/strategy/leaderboard.md"},
    {"strategy": "S3 correlated-pair", "focus": "same-game 2-leg parlays", "picks_logged": 0,
     "record": "0-0", "raw_roi": "", "process_rating": "n/a (pre-sample)", "gate_status": "provisional - gate G4 correlation cap enforced; G2 pending",
     "reward_points": "0", "rules": "analysis/strategy/leaderboard.md"},
    {"strategy": "S4 prop-combo", "focus": "player prop + game leg", "picks_logged": 0,
     "record": "0-0", "raw_roi": "", "process_rating": "n/a (pre-sample)", "gate_status": "provisional - market prop feed missing (Q-2); projections only",
     "reward_points": "0", "rules": "analysis/strategy/leaderboard.md"},
    {"strategy": "S5 dog-upset (reserved)", "focus": "moneyline underdogs vs model", "picks_logged": 0,
     "record": "0-0", "raw_roi": "", "process_rating": "n/a (pre-sample)", "gate_status": "not activated - needs market ML feed (Q-1)",
     "reward_points": "0", "rules": "analysis/strategy/leaderboard.md"},
]

w("our-lines.csv", lines, list(lines[0].keys()))
w("picks.csv", picks, list(picks[0].keys()) if picks else ["date"])
w("parlays.csv", parlays, list(parlays[0].keys()) if parlays else ["date"])
w("prop-lines.csv", props, list(props[0].keys()))
w("luck-table.csv", luck, list(luck[0].keys()))
w("leaderboard.csv", leaderboard, list(leaderboard[0].keys()))

print(f"league mean ortg_adj={lg_ortg:.2f} drtg_adj={lg_drtg:.2f} baseline total={lg_total:.2f}")
print(f"lines={len(lines)} picks={len(picks)} parlays={len(parlays)} props={len(props)}")
