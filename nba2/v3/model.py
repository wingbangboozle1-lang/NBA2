"""The v3 model: two estimators, a pinned home-court advantage, luck z-scores,
possessions x PPP totals, and schedule flow.

Design rules, each one enforced in code rather than promised in prose:

* **Two estimators, never one blend as the headline.** ``E1`` is an efficiency view
  (net rating per 100 possessions) and ``E2`` is a scoring view (points for and
  against per game, Pythagorean form). They use different columns of the same
  official snapshot. Their **disagreement is the published headline**; the average
  is published underneath it and is never the number a reader sees first.
* **Home-court advantage is pinned, not fitted.** ``h`` is chosen so that a normal
  margin model with the measured league margin sd reproduces the **measured home
  win rate** from the official results history: h = sd x Phi^-1(p_home). No free
  parameter, no folklore.
* **Luck is a z-score, and it gates publication.** Pythagorean expected wins come
  from officially-sourced points for and against; the residual is standardised
  against the binomial sd of the club's own games. A strategy that leans on a club
  outside the noise band is refused, not downgraded.
* **Totals are possessions x points-per-possession**, not an average of two scoring
  averages: expected possessions come from the two clubs' official PACE columns and
  each side's points per possession is the mean of its own OffRtg and the opponent's
  DefRtg, per 100.
* **Nothing is imputed.** A missing input produces a blank cell with a flag id.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from . import official as O

ROOT = Path(__file__).resolve().parents[2]
HISTORY_DIR = ROOT / "data" / "raw" / "history"

# Pythagorean exponent (Basketball-Reference convention, 13.91). Stated, not fitted:
# the luck z-score is recomputed and published for 13.5 and 16.5 as a sensitivity row.
PYTHAG_EXP = 13.91
NOISE_BAND_Z = 2.0  # |z| above this is outside the noise band -> refuse to publish


# --------------------------------------------------------------------- statistics
def phi(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def phi_inv(p: float) -> float:
    """Acklam's rational approximation; |error| < 1.15e-9, plenty for this."""
    if not 0.0 < p < 1.0:
        raise ValueError("p must be in (0,1)")
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    pl, ph = 0.02425, 1 - 0.02425
    if p < pl:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p > ph:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
                ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
           (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


def mean(xs):
    return sum(xs) / len(xs) if xs else None


def sd(xs):
    if len(xs) < 2:
        return None
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def pearson(xs, ys):
    if len(xs) != len(ys) or len(xs) < 3:
        return None
    mx, my = mean(xs), mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return num / (dx * dy) if dx and dy else None


# ------------------------------------------------------------------ results history
def load_played_games() -> dict:
    """Every official final score committed in the repo, plus this session's 11/14 set.

    Deduped by official game id. Neutral-site games are kept but excluded from every
    home-court statistic, because a neutral floor has no home court.
    """
    games, files = {}, []
    for p in sorted(HISTORY_DIR.glob("games_*.json")):
        d = json.loads(p.read_text())
        files.append(p.name)
        for g in d.get("games", []):
            if g.get("away_pts") is None or g.get("home_pts") is None:
                continue
            games[g["game_id"]] = {
                "game_id": g["game_id"], "date": g["date"],
                "away": g["away"], "home": g["home"],
                "away_pts": g["away_pts"], "home_pts": g["home_pts"],
                "home_margin": g["home_pts"] - g["away_pts"],
                "total_pts": g["home_pts"] + g["away_pts"],
                "neutral": bool(g.get("neutral_site")),
                "source_url": g.get("source_url") or g.get("list_url"),
                "origin": p.name,
            }
    for r in O.RESULTS:
        games[r["game_id"]] = {
            "game_id": r["game_id"], "date": r["date"],
            "away": r["away"], "home": r["home"],
            "away_pts": r["away_pts"], "home_pts": r["home_pts"],
            "home_margin": r["home_margin"], "total_pts": r["total_pts"],
            "neutral": False, "source_url": r["source_url"],
            "origin": "nba2/v3/official.py RESULTS",
        }
    return {"files": files, "games": [games[k] for k in sorted(games)]}


def home_court(played: list[dict]) -> dict:
    """Measure the home-win rate and pin HCA to it."""
    real = [g for g in played if not g["neutral"]]
    n = len(real)
    hw = sum(1 for g in real if g["home_margin"] > 0)
    margins = [g["home_margin"] for g in real]
    p_home = hw / n if n else None
    s = sd(margins)
    h = s * phi_inv(p_home) if (p_home and s) else None
    return {
        "n_games": n,
        "home_wins": hw,
        "home_win_rate": round(p_home, 4) if p_home is not None else None,
        "neutral_excluded": len(played) - n,
        "margin_sd": round(s, 3) if s else None,
        "margin_mean": round(mean(margins), 3) if margins else None,
        "hca_points": round(h, 3) if h else None,
        "rule": "h = sd(home margin) x Phi^-1(measured home win rate)",
        "note": (
            "HCA is pinned, not fitted: with this h and this sd the model's home-win "
            "probability for two otherwise equal clubs equals the measured home-win rate "
            "exactly. It is a restatement of an official count, not an estimated edge."
        ),
        "src": "data/raw/history/games_*.json + nba2/v3/official.py RESULTS",
    }


# -------------------------------------------------------------------- two estimators
def estimator_efficiency(home: dict, away: dict, hca: float, poss: float) -> float:
    """E1 — net rating per 100 possessions, scaled by the game's expected possessions.

    Uses OffRtg and DefRtg only. Home margin = (net_home - net_away)/100 x poss + hca.
    """
    net_h = home["off_rtg"] - home["def_rtg"]
    net_a = away["off_rtg"] - away["def_rtg"]
    return (net_h - net_a) / 100.0 * poss + hca


def pythagorean(pts_for: float, pts_against: float, exp: float = PYTHAG_EXP) -> float:
    """Win probability against a league-average opponent, from points for/against."""
    return pts_for ** exp / (pts_for ** exp + pts_against ** exp)


def log5(p_h: float, p_a: float) -> float:
    """P(home beats away) on a neutral floor from two win-vs-average probabilities."""
    if p_h is None or p_a is None:
        return None
    den = p_h + p_a - 2 * p_h * p_a
    return (p_h - p_h * p_a) / den if den else 0.5


def estimator_scoring(home: dict, away: dict, hca: float, sigma: float) -> float:
    """E2 — Pythagorean / log5, i.e. the **ratio** view of the same scoring columns.

    E1 is difference-based and pace-adjusted (points per 100 possessions scaled by
    the game's expected possessions). E2 is ratio-based and pace-blind: each club's
    Pythagorean win probability against a league-average opponent is combined with
    log5, and the result is mapped back to a margin through the measured game sd.
    Two clubs with the same net rating but different scoring levels get different
    E2 numbers, which is exactly the disagreement we want to publish.
    """
    p_h = pythagorean(home["pts_for"], home["pts_against"])
    p_a = pythagorean(away["pts_for"], away["pts_against"])
    p_neutral = log5(p_h, p_a)
    if p_neutral is None:
        return hca
    return phi_inv(p_neutral) * sigma + hca


# ------------------------------------------------------------------------- luck
def luck_table(teams: dict = None) -> list[dict]:
    """Pythagorean expected wins, the win residual, and its z-score."""
    teams = teams or O.TEAMS
    rows = []
    for ab, t in teams.items():
        pf, pa = t["pts_for"], t["pts_against"]
        gp = t["gp"]
        exp_p = pf ** PYTHAG_EXP / (pf ** PYTHAG_EXP + pa ** PYTHAG_EXP)
        exp_w = exp_p * gp
        resid = t["w"] - exp_w
        z_sd = math.sqrt(gp * exp_p * (1 - exp_p))
        rows.append({
            "team": ab, "name": t["name"], "gp": gp, "w": t["w"], "l": t["l"],
            "pts_for": round(pf, 2), "pts_against": round(pa, 2),
            "pythag_win_pct": round(exp_p, 4),
            "expected_wins": round(exp_w, 2),
            "actual_wins": t["w"],
            "luck_wins": round(resid, 2),
            "luck_z": round(resid / z_sd, 3) if z_sd else None,
            "in_noise_band": abs(resid / z_sd) <= NOISE_BAND_Z if z_sd else None,
            "exponent": PYTHAG_EXP,
            "src": "team_adv", "src_rec": "standings",
        })
    # sensitivity: does the band membership survive a different Pythagorean exponent?
    for e in (13.5, 16.5):
        for r in rows:
            t = teams[r["team"]]
            p = t["pts_for"] ** e / (t["pts_for"] ** e + t["pts_against"] ** e)
            resid = t["w"] - p * t["gp"]
            zsd = math.sqrt(t["gp"] * p * (1 - p))
            r[f"luck_z_exp{e}"] = round(resid / zsd, 3) if zsd else None
    rows.sort(key=lambda r: (r["luck_z"] is None, -(r["luck_z"] or 0)))
    return rows


def outside_noise_band(luck_rows: list[dict]) -> set:
    return {r["team"] for r in luck_rows if r["in_noise_band"] is False}


# ------------------------------------------------------------------------- flow
def team_schedule(played: list[dict], slate: list[dict]) -> dict:
    """date -> list of (team, opponent, home?) from official results + this slate."""
    out: dict[str, list[tuple]] = {}
    for g in played:
        out.setdefault(g["date"], []).append((g["home"], g["away"], True))
        out.setdefault(g["date"], []).append((g["away"], g["home"], False))
    for g in slate:
        out.setdefault(g["date"], []).append((g["home"], g["away"], True))
        out.setdefault(g["date"], []).append((g["away"], g["home"], False))
    return out


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km. Pure geometry on two published coordinates."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0088 * math.asin(math.sqrt(a))


def travel_for(last_home_abbr: str | None, this_home_abbr: str) -> tuple:
    """(km, flag_id) from the previous game's arena to this game's arena.

    The arena NAME is official. The COORDINATES are third-party (Wikipedia/Wikidata), so
    the number is published carrying ``F-306`` - it is derived, not official, and the page
    says so. When either end is missing a coordinate the answer is ``(None, "F-306")``:
    a blank with a reason, never an estimate.
    """
    a = O.ARENA_COORDS.get(last_home_abbr) if last_home_abbr else None
    b = O.ARENA_COORDS.get(this_home_abbr)
    if not a or not b:
        return None, "F-306"
    return round(haversine_km(a[0], a[1], b[0], b[1]), 1), "F-306"


def flow_for_game(game: dict, played: list[dict], slate: list[dict]) -> dict:
    """Rest, back-to-back, 3-in-4 and travel distance.

    Rest is measured from official dates. Travel is great-circle km between the previous
    game's arena and this one, computed on the committed arena-coordinate table; the
    coordinates are third-party, so every distance carries flag ``F-306`` and is labelled
    derived on the page. A club with no previous game in the window has no distance.
    """
    sched = team_schedule(played, slate)
    by_date_host: dict[str, dict] = {}
    for g in played + slate:
        by_date_host.setdefault(g["date"], {})[g["home"]] = g["home"]
        by_date_host.setdefault(g["date"], {})[g["away"]] = g["home"]
    day = game["date"]
    res = {}
    for side in ("away", "home"):
        team = game[side]
        prior = []
        for d, rows in sched.items():
            if d >= day:
                continue
            for t, opp, _ in rows:
                if t == team:
                    prior.append(d)
        prior = sorted(set(prior))
        last = prior[-1] if prior else None
        days = (iso_days(day) - iso_days(last)) if last else None
        n4 = sum(1 for d in prior if iso_days(day) - iso_days(d) <= 3)
        last_host = by_date_host.get(last, {}).get(team) if last else None
        km, flag = travel_for(last_host, game["home"]) if last_host else (None, "F-306")
        res[side] = {
            "team": team,
            "last_game_date": last,
            "rest_days": days,
            "back_to_back": days == 1 if days is not None else None,
            "three_in_four": n4 >= 3,
            "games_last_4_days": n4,
            "previous_game_arena": O.ARENA_COORDS.get(last_host, (None, None, None, None))[2]
                                  if last_host else None,
            "travel_km": km,
            "travel_flag": flag,
        }
    res["rest_edge"] = (
        (res["home"]["rest_days"] or 0) - (res["away"]["rest_days"] or 0)
        if res["home"]["rest_days"] is not None and res["away"]["rest_days"] is not None
        else None
    )
    return res


def iso_days(s: str) -> int:
    import datetime as _dt
    y, m, d = (int(x) for x in s.split("-"))
    return (_dt.date(y, m, d) - _dt.date(1970, 1, 1)).days


# ------------------------------------------------------------------------- lines
def price_game(game: dict, teams: dict, hca: float, sigma: float) -> dict:
    """One game: possessions x PPP total, two margin estimators, disagreement first."""
    h = teams[game["home"]]
    a = teams[game["away"]]
    # expected possessions: the mean of the two official PACE columns (per 48 minutes)
    poss = (h["pace"] + a["pace"]) / 2.0
    # points per possession, each side = mean of own OffRtg and opponent DefRtg, /100
    ppp_h = ((h["off_rtg"] + a["def_rtg"]) / 2.0) / 100.0
    ppp_a = ((a["off_rtg"] + h["def_rtg"]) / 2.0) / 100.0
    home_pts = poss * ppp_h
    away_pts = poss * ppp_a
    total = home_pts + away_pts

    e1 = estimator_efficiency(h, a, hca, poss)
    e2 = estimator_scoring(h, a, hca, sigma)
    spread_home = -(e1 + e2) / 2.0  # home spread: negative => home favoured
    return {
        "game_id": game["game_id"], "date": game["date"], "matchup": game["matchup"],
        "away": game["away"], "home": game["home"],
        "time_et": game["time_et"], "arena": game["arena"],
        "city": game["city"], "state": game["state"],
        "possessions": round(poss, 2),
        "ppp_home": round(ppp_h, 4), "ppp_away": round(ppp_a, 4),
        "proj_home_pts": round(home_pts, 1), "proj_away_pts": round(away_pts, 1),
        "total": round(total, 1),
        "e1_margin": round(e1, 2), "e2_margin": round(e2, 2),
        "disagreement": round(abs(e1 - e2), 2),
        "consensus_margin": round((e1 + e2) / 2.0, 2),
        "spread_home": round(spread_home, 1),
        "p_home_e1": round(phi(e1 / sigma), 4),
        "p_home_e2": round(phi(e2 / sigma), 4),
        "p_home": round(phi(((e1 + e2) / 2.0) / sigma), 4),
        "hca_used": round(hca, 3), "sigma_used": round(sigma, 3),
        "src": "team_adv", "src_game": "schedule",
        "source_url": game["source_url"],
    }


# ------------------------------------------------------------------------- parlays
def measure_rho(played: list[dict]) -> dict:
    """Measured same-game spread/total correlation from official finals.

    r(home margin, total points). This is the rho used to price a spread+total
    same-game parlay; the naive product is printed beside it, never instead of it.
    """
    real = [g for g in played if not g["neutral"]]
    xs = [g["home_margin"] for g in real]
    ys = [g["total_pts"] for g in real]
    r = pearson(xs, ys)
    n = len(real)
    # Fisher z interval
    lo = hi = None
    if r is not None and n > 3:
        z = 0.5 * math.log((1 + r) / (1 - r))
        se = 1 / math.sqrt(n - 3)
        lo = math.tanh(z - 1.96 * se)
        hi = math.tanh(z + 1.96 * se)
    return {
        "n": n, "r": round(r, 4) if r is not None else None,
        "ci95": [round(lo, 4), round(hi, 4)] if lo is not None else None,
        "definition": "r(home margin, total points) over official finals, neutral-site games excluded",
        "src": "data/raw/history/games_*.json + nba2/v3/official.py RESULTS",
    }


def parlay_price(p1: float, p2: float, rho: float) -> dict:
    """Two legs, Gaussian copula at the measured rho; the naive product is printed too."""
    if rho is None:
        return {"p_joint": None, "p_naive": round(p1 * p2, 4), "rho_used": None,
                "flag": "F-309"}
    k1, k2 = phi_inv(p1), phi_inv(p2)
    # bivariate normal orthant probability by Gauss-Legendre over one dimension
    joint = _bvn(k1, k2, rho)
    naive = p1 * p2
    return {
        "p_joint": round(joint, 4), "p_naive": round(naive, 4),
        "rho_used": round(rho, 4),
        "naive_overstates_by": round(naive - joint, 4),
        "naive_error_pct": round(100.0 * (naive - joint) / joint, 2) if joint else None,
        "method": "Gaussian copula, 40-point Gauss-Legendre in the conditioning dimension",
    }


def _bvn(k1: float, k2: float, rho: float, n: int = 40) -> float:
    """P(X<=k1, Y<=k2) for standard bivariate normal with correlation rho."""
    # Gauss-Legendre nodes on [-1,1] via Newton on the Legendre polynomial.
    xs, ws = _gauss_legendre(n)
    total = 0.0
    for x, w in zip(xs, ws):
        u = 0.5 * (x + 1.0)          # map to [0,1]
        a = phi_inv(max(1e-12, min(1 - 1e-12, u * phi(k1))))
        arg = (k2 - rho * a) / math.sqrt(max(1e-12, 1 - rho * rho))
        total += w * 0.5 * phi(k1) * phi(arg)
    return max(0.0, min(1.0, total))


def _gauss_legendre(n: int):
    xs, ws = [], []
    for i in range(1, n + 1):
        x = math.cos(math.pi * (i - 0.25) / (n + 0.5))
        for _ in range(100):
            p0, p1 = 1.0, 0.0
            for j in range(1, n + 1):
                p2 = p1
                p1 = p0
                p0 = ((2 * j - 1) * x * p1 - (j - 1) * p2) / j
            dp = n * (x * p0 - p1) / (x * x - 1.0)
            dx = -p0 / dp
            x += dx
            if abs(dx) < 1e-15:
                break
        xs.append(x)
        ws.append(2.0 / ((1 - x * x) * dp * dp))
    return xs, ws


# ------------------------------------------------------------------------- rotation
def availability(game: dict, injuries: list[dict]) -> dict:
    """Rotation availability per side, straight from the official report.

    Counts are official; any production impact is blank, because the report states
    statuses and reasons and nothing else.
    """
    out = {}
    for side in ("away", "home"):
        ab = game[side]
        rows = [r for r in injuries
                if r["team_abbr"] == ab and r["game_date"] == game["date"]]
        if rows and rows[0]["not_submitted"] and len(rows) == 1:
            out[side] = {
                "team": ab, "filed": False, "n_out": None, "n_doubtful": None,
                "n_questionable": None, "n_probable": None, "n_available": None,
                "players_listed": 0, "minutes_at_risk_share": None,
                "flag": "not filed", "flag_id": "F-303" if len(rows) == 1 else None,
            }
            continue
        if not rows:
            out[side] = {
                "team": ab, "filed": False, "n_out": None, "n_doubtful": None,
                "n_questionable": None, "n_probable": None, "n_available": None,
                "players_listed": 0, "minutes_at_risk_share": None,
                "flag": "no row in any published report for this date",
                "flag_id": "future_injuries",
            }
            continue
        cnt = {}
        for r in rows:
            if r["status"]:
                cnt[r["status"]] = cnt.get(r["status"], 0) + 1
        out[side] = {
            "team": ab, "filed": True,
            "n_out": cnt.get("Out", 0), "n_doubtful": cnt.get("Doubtful", 0),
            "n_questionable": cnt.get("Questionable", 0),
            "n_probable": cnt.get("Probable", 0),
            "n_available": cnt.get("Available", 0),
            "players_listed": len(rows),
            "minutes_at_risk_share": None,
            "flag": "minutes impact blank: " + O.BLOCKED["player_minutes"][0],
            "flag_id": "F-307",
        }
    return out


# ------------------------------------------------------------------------- assembly
def build(verbose: bool = False) -> dict:
    hist = load_played_games()
    played = hist["games"]
    hc = home_court(played)
    sigma = hc["margin_sd"]
    hca = hc["hca_points"]
    luck = luck_table()
    band = outside_noise_band(luck)
    rho = measure_rho(played)

    lines = []
    for g in O.SLATE:
        row = price_game(g, O.TEAMS, hca, sigma)
        row["flow"] = flow_for_game(g, played, O.SLATE)
        row["availability"] = availability(g, O.INJURIES)
        # the luck gate: a strategy may not lean on a club outside the noise band
        row["luck_gate"] = {
            "home": O.TEAMS[g["home"]]["abbr"], "away": O.TEAMS[g["away"]]["abbr"],
            "home_outside": g["home"] in band, "away_outside": g["away"] in band,
            "blocked": (g["home"] in band) or (g["away"] in band),
            "band_z": NOISE_BAND_Z,
        }
        lines.append(row)

    return {
        "as_of_utc": O.AS_OF_UTC, "as_of_et": O.AS_OF_ET, "session": O.SESSION,
        "window": {"start": O.WINDOW[0], "end": O.WINDOW[1], "n_games": len(O.SLATE)},
        "history": {"n_games": len(played), "files": hist["files"],
                    "source": "data/raw/history + nba2/v3/official.py RESULTS"},
        "home_court": hc,
        "luck": luck, "luck_band_z": NOISE_BAND_Z, "outside_band": sorted(band),
        "rho": rho,
        "lines": lines,
        "sources": O.SOURCES, "blocked": O.BLOCKED, "flags": O.FLAGS,
        "crosschecks": O.crosschecks(),
    }


if __name__ == "__main__":
    out = build()
    hc = out["home_court"]
    print(f"{out['history']['n_games']} official finals -> "
          f"home {hc['home_wins']}/{hc['n_games']} = {hc['home_win_rate']}, "
          f"sd {hc['margin_sd']}, pinned HCA {hc['hca_points']} pts")
    print(f"rho(spread,total) = {out['rho']['r']} on n={out['rho']['n']}")
    for r in out["lines"][:5]:
        print(f"  {r['matchup']:9s} E1 {r['e1_margin']:+6.2f}  E2 {r['e2_margin']:+6.2f}  "
              f"disagree {r['disagreement']:5.2f}  total {r['total']:6.1f}")
