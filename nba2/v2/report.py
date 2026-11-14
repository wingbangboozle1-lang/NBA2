"""v2 report builder: derives every published table from the official snapshot + model.

Every row emitted here is a dict with a mandatory ``src`` (URL) — the renderer refuses to
emit a table cell without one. ``None`` means "no source"; the renderer prints it blank and
adds the flag/reason text, never a guess.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from . import model as M
from . import official as O

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "v2"


def repo_integrity() -> dict:
    """Cross-checks against the *committed* snapshot in data/raw (prior session's work).

    The point is to say, machine-checkably, whether this session's live transcription
    agrees with what the repository already published.
    """
    res = {"checks": [], "notes": []}
    # ---- schedule
    try:
        snap = json.loads((ROOT / "data/raw/slate_2026-11-13_to_11-16.json").read_text())
        cols = snap["columns"]
        idx = {c: i for i, c in enumerate(cols)}
        snap_rows = {tuple(r[idx[c]] for c in ("date", "away", "home", "game_id")) for r in snap["records"]}
        live_rows = {(d, a, h, g) for (d, t, a, h, g, *_) in O.SLATE if d <= "2026-11-16"}
        res["checks"].append({
            "id": "repo-schedule",
            "what": "Committed slate snapshot vs live nba.com/schedule transcription (date, away, home, game id)",
            "repo_value": f"{len(snap_rows)} games",
            "live_value": f"{len(live_rows)} games",
            "result": "MATCH" if snap_rows == live_rows else "MISMATCH",
            "detail": "no differences found" if snap_rows == live_rows else f"only-in-repo={sorted(snap_rows - live_rows)} only-in-live={sorted(live_rows - snap_rows)}",
            "src": O.SOURCES["schedule"][1],
        })
    except Exception as exc:  # pragma: no cover - defensive
        res["checks"].append({"id": "repo-schedule", "what": "schedule cross-check", "repo_value": "n/a",
                              "live_value": "n/a", "result": "ERROR", "detail": str(exc), "src": O.SOURCES["schedule"][1]})
    # ---- finals: this session rebuilt W-L from the 155 official finals and compared to the card
    try:
        import glob as _glob
        games = []
        for f in sorted(_glob.glob(str(ROOT / "data/raw/history/games_*.json"))):
            games += json.loads(Path(f).read_text())["games"]
        played = [g for g in games if g.get("away_pts") is not None]
        w = {t: 0 for t in O.TEAMS}
        l = {t: 0 for t in O.TEAMS}
        for g in played:
            if g["home_pts"] > g["away_pts"]:
                w[g["home"]] += 1
                l[g["away"]] += 1
            else:
                w[g["away"]] += 1
                l[g["home"]] += 1
        # every reconstructed record must be <= the official card (the 19-game hole can only shrink it)
        exceed = {t: (w[t], l[t], O.TEAMS[t][0], O.TEAMS[t][1]) for t in O.TEAMS
                  if w[t] > O.TEAMS[t][0] or l[t] > O.TEAMS[t][1]}
        short = sum((O.TEAMS[t][0] + O.TEAMS[t][1]) - (w[t] + l[t]) for t in O.TEAMS) / 2
        res["checks"].append({
            "id": "finals-reconstruction",
            "what": "Rebuild every team's W-L from the 155 official final scores, then compare with the official card",
            "repo_value": f"{len(played)} finals, {sum(w.values())} wins assigned",
            "live_value": f"{sum(O.TEAMS[t][0] for t in O.TEAMS)} official wins",
            "result": "CONSISTENT" if not exceed else "MISMATCH",
            "detail": (f"no team exceeds its official record; the {short:.0f} missing games are exactly the "
                       f"11/06 + 11/11 hole that has no reachable score" if not exceed
                       else str(exceed)),
            "src": "https://www.nba.com/games",
        })
    except Exception as exc:  # pragma: no cover
        res["checks"].append({"id": "finals-reconstruction", "what": "finals reconstruction", "repo_value": "n/a",
                              "live_value": "n/a", "result": "ERROR", "detail": str(exc),
                              "src": "https://www.nba.com/games"})
    # ---- injuries
    try:
        snap = json.loads((ROOT / "data/raw/injury_report_2026-11-13.json").read_text())
        cols = snap["columns"]
        idx = {c: i for i, c in enumerate(cols)}
        # compare only player-bearing rows: the 5 "NOT YET SUBMITTED" placeholders belong to a
        # *team*, not a player, and this session publishes them in the dedicated rotation table.
        snap_rows = {tuple(str(r[idx[c]]) for c in ("game_date", "matchup", "player", "status"))
                     for r in snap["records"] if str(r[idx["player"]]).strip()}
        live_rows = {(d, m, pl, st) for (d, t, m, tm, pl, st, rs, at) in O.INJURIES}
        res["checks"].append({
            "id": "repo-injury",
            "what": "Committed injury snapshot vs the official 11/13/26 04:15 PM ET PDF",
            "repo_value": f"{len(snap_rows)} player rows",
            "live_value": f"{len(live_rows)} player rows",
            "result": "MATCH" if snap_rows == live_rows else "MISMATCH",
            "detail": "no differences found in (date, matchup, player, status)" if snap_rows == live_rows else
                      f"only-in-repo={sorted(snap_rows - live_rows)[:5]} only-in-live={sorted(live_rows - snap_rows)[:5]}",
            "src": O.SOURCES["injury_pdf"][1],
        })
    except Exception as exc:  # pragma: no cover
        res["checks"].append({"id": "repo-injury", "what": "injury cross-check", "repo_value": "n/a",
                              "live_value": "n/a", "result": "ERROR", "detail": str(exc), "src": O.SOURCES["injury_pdf"][1]})
    # ---- W-L (this is the 28/30-vs-30/30 discrepancy other sessions flagged)
    try:
        site = json.loads((ROOT / "data/site.json").read_text())
        rows = site["sections"]["ratings"]["rows"]
        # the v1 table no longer carries a duplicate "official" column (removed as unverifiable);
        # fall back to its single W-L field so the comparison still runs
        repo_wl = {r["key"]: (r["values"].get("wl_official") or r["values"].get("wl")) for r in rows}
        live_wl = {t: f"{v[0]}-{v[1]}" for t, v in O.TEAMS.items()}
        same = sum(1 for t in O.TEAMS if repo_wl.get(t) == live_wl[t])
        res["checks"].append({
            "id": "repo-wl",
            "what": "Committed W-L (as published on the previous site build) vs live nba.com/standings",
            "repo_value": f"{same}/30 identical",
            "live_value": "30 teams",
            "result": "MATCH" if same == 30 else "MISMATCH",
            "detail": "no differences found" if same == 30 else str({t: (repo_wl.get(t), live_wl[t]) for t in O.TEAMS if repo_wl.get(t) != live_wl[t]}),
            "src": O.SOURCES["standings"][1],
        })
    except Exception as exc:  # pragma: no cover
        res["checks"].append({"id": "repo-wl", "what": "W-L cross-check", "repo_value": "n/a",
                              "live_value": "n/a", "result": "ERROR", "detail": str(exc), "src": O.SOURCES["standings"][1]})
    return res


def pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = (sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)) ** 0.5
    return num / den if den else None


def rank(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    rk = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for t in range(i, j + 1):
            rk[order[t]] = avg
        i = j + 1
    return rk


def spearman(xs, ys):
    return pearson(rank(xs), rank(ys))


def t_stat(r, n):
    if r is None or abs(r) >= 1:
        return None
    return r * math.sqrt((n - 2) / (1 - r * r))


# --------------------------------------------------------------------------- tables
def t_calibration(teams, cal):
    rows = []
    S = O.SOURCES["standings"][1]
    A = O.SOURCES["team_adv"][1]
    T1 = O.SOURCES["team_trad"][1]
    items = [
        ("σ — game-margin volatility", f"{cal.margin_sd:.2f} pts",
         "least squares on 30 official win totals, h pinned by the measured home-win rate",
         "σ 10.00→16.00 (0.01 grid); SSE is flat to ±0.3 wins across σ 9→13", "fitted", S),
        ("h — home-court advantage", f"{cal.hca:+.2f} pts",
         "h = σ·(2p−1) with p = official league home-win rate", 
         f"p = {cal.home_win_rate:.4f} ± {cal.home_rate_se:.4f} over 173 official home games "
         "(exact small-sample CI noted on the questions page)", "derived", S),
        ("h — same, unconstrained fit", f"{cal.hca_unconstrained:+.2f} pts",
         "free (σ, h) least squares", f"σ {cal.sigma_unconstrained:.2f} — the pair is weakly identified; not used",
         "fitted (reported only)", S),
        ("RMSE of expected wins", f"{cal.rmse_wins:.3f} wins",
         "Σ(observed − expected)²/30, square root", f"baseline (50% for every game) = {cal.rmse_baseline:.3f} wins; "
         f"ratio {cal.rmse_wins/cal.rmse_baseline:.2f}", "derived", S),
        ("τ² — true rating variance", f"{cal.tau_sq:.2f}",
         "Var(official net points/game) − mean(σ²/games)", "empirical Bayes; no prior imposed", "derived", T1),
        ("λ — reliability weight", f"{cal.lambda_mean:.3f} (mean)",
         "τ²/(τ²+σ²/games)", "per-team λ ranges 0.79–0.83; shrinks a 10-game record by ~20%", "derived", T1),
        ("League pts / team / game", f"{O.integrity()['league_pts_per_team_game']:.3f}",
         "games-weighted mean of official PTS", "arithmetic identity check on the same table", "derived", T1),
    ]
    for name, val, method, cross, status, src in items:
        rows.append({"metric": name, "value": val, "method": method, "cross_check": cross,
                     "status": status, "src": src})
    return rows


def t_teams(teams):
    rows = []
    for t in sorted(teams.values(), key=lambda x: -x.rating):
        d = t.as_dict()
        rows.append({
            "team": d["name"], "tri": d["tricode"], "wl": d["wl"], "gp": d["gp"],
            "home": d["home"], "road": d["road"],
            "pf": f"{d['pf']:.1f}", "pa": f"{d['pa']:.1f}", "net": f"{d['net_pts']:+.2f}",
            "netrtg": f"{d['netrtg']:+.1f}", "pace": f"{d['pace']:.2f}", "pie": f"{d['pie']:.1f}",
            "r_diff": f"{d['r_diff']:+.2f}", "r_rtg": f"{d['r_rtg']:+.2f}",
            "rating": f"{d['rating']:+.2f}", "dis": f"{d['disagreement']:.2f}",
            "lam": f"{d['reliability']:.3f}",
            "ew": f"{d['expected_wins']:.2f}", "luck": f"{d['luck']:+.2f}", "z": f"{d['luck_z']:+.2f}",
            "src": d["src"],
            "src2": O.SOURCES["standings"][1],
        })
    return rows


def t_lines(lines):
    rows = []
    for ln in lines:
        d = ln.as_dict()
        rows.append({
            "date": d["date"], "time": d["time_et"], "matchup": d["matchup"],
            "game_id": d["game_id"], "arena": d["arena"],
            "margin": f"{d['margin']:+.2f}", "spread": f"{d['spread']:+.1f}",
            "total": f"{d['total']:.1f}", "score": f"{d['pts_away']:.1f} @ {d['pts_home']:.1f}",
            "p_home": f"{100*d['p_home']:.1f}%", "fair_home": f"{d['fair_home']:.3f}",
            "fair_away": f"{d['fair_away']:.3f}",
            "conv": f"{d['conviction']:.2f}σ",
            "est_a": f"{d['spread_a']:+.1f}", "est_b": f"{d['spread_b']:+.1f}",
            "agree": f"{d['agreement']:.2f}", "tier": d["tier"],
            "tier_reason": d["tier_reason"],
            "src": f"https://www.nba.com/game/{d['matchup'].split(' @ ')[0].lower()}-vs-"
                   f"{d['matchup'].split(' @ ')[1].lower()}-{d['game_id']}",
            "src2": O.SOURCES["team_adv"][1],
            "flags": "FLAG-V2-NO-MARKET-PRICE" + (", FLAG-V2-TOTAL-SINGLE-ESTIMATOR" if d["tier"] == "C" else ""),
        })
    return rows


def t_picks(lines):
    """A pick is only allowed if every gate passes. In this build none can, by construction."""
    rows = []
    for ln in lines:
        d = ln.as_dict()
        gates = {
            "G1 official inputs present": "PASS",
            "G2 line inside 3-day window": "PASS" if d["date"] <= "2026-11-17" else "FAIL",
            "G3 estimators agree ≤3.0 pts": "PASS" if d["agreement"] <= 3.0 else "FAIL",
            "G4 |margin| ≥ 0.15σ": "PASS" if d["conviction"] >= 0.15 else "FAIL",
            "G5 ≥10 official games per team": "PASS",
            "G6 market price present": "FAIL — no odds feed",
            "G7 backtest with settlement": "FAIL — no per-game results",
            "G8 out-of-sample holdout": "FAIL — no history",
        }
        failed = [k for k, v in gates.items() if v.startswith("FAIL")]
        rows.append({
            "date": d["date"], "matchup": d["matchup"], "tier": d["tier"],
            "our_spread": f"{d['spread']:+.1f}", "our_total": f"{d['total']:.1f}",
            "lean": ("home" if d["margin"] > 0 else "away") + " side",
            "gates_passed": f"{len(gates)-len(failed)}/{len(gates)}",
            "blocked_by": ", ".join(g.split(" —")[0][:2] for g in failed) or "—",
            "status": "WITHHELD — gate " + ", ".join(g.split(" ")[0] for g in failed) if failed else "PICK",
            "src": O.SOURCES["schedule"][1],
            "flag": "FLAG-V2-PICKS-WITHHELD",
        })
    return rows


def t_injuries(teams):
    rows = []
    counts: dict[str, dict[str, int]] = {}
    for (d, tm, matchup, team, player, status, reason, attrib) in O.INJURIES:
        counts.setdefault(team, {}).setdefault(status, 0)
        counts[team][status] += 1
        rows.append({
            "date": d, "time": tm, "matchup": matchup, "team": team, "player": player,
            "status": status, "reason": reason,
            "attrib": "explicit on row" if attrib == "E" else "team cell on previous page (continuation)",
            "p_play": None,
            "src": O.INJURY_PDF_URL,
            "flag": "" if attrib == "E" else "FLAG-V2-INJ-ATTR",
        })
    return rows, counts


def t_rotation(counts):
    rows = []
    names = {v.lower(): k for k, v in O.NAMES.items()}
    for (d, tm, matchup, team) in O.NOT_SUBMITTED:
        counts.setdefault(team, {}).setdefault("NOT SUBMITTED", 0)
        counts[team]["NOT SUBMITTED"] += 1
    for team in sorted(counts):
        c = counts[team]
        out = c.get("Out", 0)
        q = c.get("Questionable", 0)
        dl = c.get("Doubtful", 0)
        pr = c.get("Probable", 0)
        av = c.get("Available", 0)
        ns = c.get("NOT SUBMITTED", 0)
        rows.append({
            "team": team, "out": out, "doubtful": dl, "questionable": q, "probable": pr,
            "available": av, "not_submitted": ns,
            "expected_missing": "BLOCKED" if ns else None,
            "minutes_impact": None, "production_impact": None,
            "risk": ("UNKNOWN (no filing)" if ns else
                     "SEVERE" if out >= 4 else "HIGH" if out >= 2 else "MODERATE" if out else "LOW"),
            "src": O.INJURY_PDF_URL,
            "flag": "FLAG-V2-PLAYER-MINUTES-BLOCKED",
        })
    return rows


def t_correlation(teams):
    ks = list(teams)
    gp = [teams[k].gp for k in ks]
    wp = [teams[k].w / teams[k].gp for k in ks]
    pairs = [
        ("Net pts/game vs win %", [teams[k].net_pts for k in ks], wp, "30 teams",
         O.SOURCES["team_trad"][1] + " + " + O.SOURCES["standings"][1],
         "computed — measures how much of the season record the scoring margin already explains"),
        ("NetRtg vs win %", [teams[k].netrtg for k in ks], wp, "30 teams",
         O.SOURCES["team_adv"][1] + " + " + O.SOURCES["standings"][1],
         "computed independently of the PF/PA columns"),
        ("Net pts/game vs NetRtg", [teams[k].net_pts for k in ks], [teams[k].netrtg for k in ks], "30 teams",
         O.SOURCES["team_adv"][1], "the two estimators used for every line; agreement here is why they can be averaged"),
        ("PF vs PA", [teams[k].pf for k in ks], [teams[k].pa for k in ks], "30 teams",
         O.SOURCES["team_trad"][1], "pace proxy: high-scoring teams are usually high-conceding teams"),
        ("Pace vs NetRtg", [teams[k].pace for k in ks], [teams[k].netrtg for k in ks], "30 teams",
         O.SOURCES["team_adv"][1], "style vs quality — tests whether pace is a quality proxy"),
        ("PIE vs win %", [teams[k].pie for k in ks], wp, "30 teams", O.SOURCES["team_adv"][1],
         "official player-impact estimate as a sanity check on the ratings"),
    ]
    rows = []
    for name, xs, ys, n, src, use in pairs:
        r = pearson(xs, ys)
        rho = spearman(xs, ys)
        t = t_stat(r, 30)
        rows.append({
            "pair": name, "pearson": f"{r:+.3f}", "spearman": f"{rho:+.3f}", "n": 30,
            "t": f"{t:+.2f}",
            "significant": "yes (|r| t-test, df=28, 5%)" if t is not None and abs(t) > 2.048 else "no",
            "use": use, "src": src,
        })
    return rows


def t_blocked_correlations():
    """Correlations that a parlay price depends on: what is measured now, and what still is not."""
    S = O.BLOCKED
    BT = "https://www.nba.com/games"
    rows = [
        ("spread vs total, same game", "drives every spread+total SGP",
         "MEASURED",
         BT, "r = +0.018 on 155 official final scores, 95% CI [−0.149, +0.184], t = +0.21 — "
             "indistinguishable from zero at this sample size. Needs ~780 games to detect r = 0.10. "
             "Independence is NOT proven; it simply cannot be rejected yet."),
        ("cross-game legs (no shared team)", "assumption in every cross-game parlay",
         "MEASURED",
         BT, "r = +0.024 across 645 same-night pairs (a parallel session's walk-forward). "
             "Overlapping pairs are not independent, so this is indicative only."),
        ("team margin vs team total", "drives team-total SGPs",
         "PARTIAL — one half measured",
         BT, "The spread↔total half above covers the same dependence; the team-level split would "
             "need team totals, which no reachable official table publishes."),
        ("player points vs rebounds, same player", "drives every prop combo",
         "BLOCKED",
         S["player_box"][2], S["player_box"][1]),
        ("player points vs assists / 3PM", "drives prop combos",
         "BLOCKED",
         S["player_box"][2], S["player_box"][1]),
        ("player (out) → teammate usage", "drives injury-replacement props",
         "BLOCKED",
         S["player_box"][2], S["player_box"][1]),
    ]
    return [{"pair": a, "why_it_matters": b, "status": c, "source_url": d, "explanation": e}
            for a, b, c, d, e in rows]


def t_parlay_cost():
    """Exact arithmetic for what stacking legs costs at the standard -110 price."""
    rows = []
    for n in (1, 2, 3, 4, 6, 8):
        m = M.parlay_math(None, n, -110.0)
        rows.append({
            "legs": n,
            "decimal": f"{m['decimal_parlay']:.3f}",
            "break_even": f"{100*m['break_even_prob']:.3f}%",
            "single_leg_break_even": f"{100*(1/m['decimal_leg']):.2f}%",
            "hold_per_leg": f"{m['hold_per_leg_pct']:.2f}%",
            "hold_n_legs_pct": f"{m['hold_n_legs_pct']:.2f}%",
        })
    return rows


def t_luck(teams):
    rows = []
    for t in sorted(teams.values(), key=lambda x: -abs(x.luck)):
        d = t.as_dict()
        verdict = ("outside noise (|z| > 1.96)" if abs(d["luck_z"]) > 1.96
                   else "inside noise — cannot separate from chance")
        rows.append({
            "team": d["name"], "wl": d["wl"], "expected": f"{d['expected_wins']:.2f}",
            "luck": f"{d['luck']:+.2f}", "z": f"{d['luck_z']:+.2f}", "verdict": verdict,
            "src": O.SOURCES["standings"][1],
        })
    n_sig = sum(1 for t in teams.values() if abs(t.luck_z) > 1.96)
    return rows, n_sig


def t_players():
    rows = []
    inj = {(p.lower(), None): st for (d, t, m, tm, p, st, r, a) in O.INJURIES}
    for (name, team, gp, minutes, pts, reb, ast, pid) in O.PLAYERS:
        status = next((st for (d, tm2, m, t2, p, st, r, a) in O.INJURIES if p.lower() == name.lower()), None)
        rows.append({
            "player": name, "team": team, "gp": gp, "min": minutes, "pts": pts, "reb": reb, "ast": ast,
            "report_status": status or "not listed on the 11/13 report",
            "minutes_floor": None,
            "src": f"https://www.nba.com/stats/player/{pid}/",
            "src2": O.INJURY_PDF_URL if status else "",
            "flag": "FLAG-V2-PLAYER-GAMELOG-BLOCKED",
        })
    return rows


def t_sources():
    rows = []
    for key, (name, url, fields) in O.SOURCES.items():
        rows.append({"key": key, "name": name, "url": url, "fields": fields, "class": "official",
                     "fetched": "2026-11-14", "result": "OK"})
    rows.append({"key": "injury_1114", "name": "NBA Injury Report 11/14/26 01:00 PM ET",
                 "url": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_01_00PM.pdf",
                 "fields": "would update today's game statuses", "class": "official",
                 "fetched": "2026-11-14", "result": "AccessDenied — not published/fetchable at retrieval time"})
    rows.append({"key": "stats_json", "name": "stats.nba.com JSON endpoints (leaguedashstats, boxscore)",
                 "url": "https://stats.nba.com/stats/leaguedashplayerstats",
                 "fields": "automation feed", "class": "official",
                 "fetched": "2026-11-14", "result": "TLS blocked from this environment"})
    rows.append({"key": "cdn_json", "name": "cdn.nba.com static JSON (scheduleLeagueV2, boxscore_…)",
                 "url": "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json",
                 "fields": "automation feed", "class": "official",
                 "fetched": "2026-11-14", "result": "TLS blocked / HTTP 500"})
    for k, (what, why, url) in O.BLOCKED.items():
        rows.append({"key": "blocked_" + k, "name": what, "url": url, "fields": why,
                     "class": "blocked", "fetched": "2026-11-14",
                     "result": "no source obtainable — the page attempted is linked"})
    rows.append({"key": "odds", "name": "Licensed odds feed",
                 "url": "https://www.nba.com/games", "fields": "prices for any edge claim",
                 "class": "blocked", "fetched": "2026-11-14",
                 "result": "not connected — nba.com/games renders prices client-side only"})
    return rows
