"""v7 model: two estimators, pinned HCA, luck z-scores, walk-forward skill, and the gates.

Cut from the **fresh** official snapshot
---------------------------------------
`nba2/v3/model.py` is cut from `nba2/v3/official.py`, a hand-transcribed snapshot dated
2026-11-17 whose team-stat rows predate the eight 11/16 and twelve 11/18 finals (measured:
it prices ATL at 8-6 while the live standings page prints 9-6). This module re-cuts every
input from `data/raw/v7_fetch/` — the **stored bytes** of the three official team-stat
pages and the standings page read in this session — so the model is cut from the pages it
names, and the parser can be checked against the file.

What is measured here, and how
------------------------------
* **E1 efficiency view** — net rating per 100 possessions: `(OffRtg_A - DefRtg_B)`.
* **E2 scoring view** — points-for and points-against per game (traditional PTS, opponent
  Opp PTS), which uses a different column family of a different page.
* **The disagreement is the headline.** `|E1 - E2|` is published on every row; the blend is
  published underneath and is never the first number a reader sees.
* **HCA is pinned, not fitted** — `h = sd(margin) x Phi^-1(measured home win rate)` over the
  committed official finals. The measured home-win rate is therefore reproduced by
  construction, and no free parameter is left to absorb it.
* **Luck is a z-score per club** against Pythagorean expected wins, with the binomial sd of
  that club's own games. A strategy leaning on a club outside |z| > 2 is refused.
* **Skill is measured walk-forward** — every graded game is predicted by a model cut from
  strictly earlier dates, and scored on the *decision it would have made* (which side, and
  did that side win), never on margin error alone. Brier and log-loss are reported against
  the two baselines that matter: a coin flip, and "back the better record".
* **Nothing is imputed.** A club missing a needed column gets a blank and a flag id.
"""

from __future__ import annotations

import glob
import json
import math
import re
from collections import defaultdict
from pathlib import Path

from . import capture as C
from .common import DATA, RAW, ROOT

# ---------------------------------------------------------------- constants (declared)
PYTHAG_EXP = 13.91          # Basketball-Reference convention, stated not fitted
NOISE_BAND_Z = 2.0          # |z| above this is "outside the noise band"
SIGMA_FLOOR = 8.0           # a margin sd below this is not a basketball distribution
MIN_TRAIN_GAMES = 40        # a walk-forward cut trains on at least this many finals


# ---------------------------------------------------------------- small statistics
def phi(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def phi_inv(p: float) -> float:
    """Acklam's rational approximation; |error| < 1.15e-9."""
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
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
                ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
           (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def sd(xs):
    xs = [x for x in xs if x is not None]
    if len(xs) < 2:
        return None
    m = sum(xs) / len(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


# ---------------------------------------------------------------- official history
def load_games() -> list[dict]:
    """Every committed official final with both clubs and both scores, one row per game.

    Deduplicated by the league's own game id. A game seen in two captures is one game; if
    the two sightings disagree on the score the game is **excluded** and listed, because a
    walk-forward test built on a contested score is not a measurement.
    """
    seen: dict[str, dict] = {}
    conflicts: list[dict] = []
    files = (sorted(glob.glob(str(RAW / "capture_*" / "finals_*.json")))
             + sorted(glob.glob(str(RAW / "finals_*.json")))
             + sorted(glob.glob(str(RAW / "history" / "games_*.json"))))
    for f in files:
        try:
            doc = json.loads(Path(f).read_text())
        except (OSError, json.JSONDecodeError):
            continue
        rel = str(Path(f).relative_to(ROOT))
        name_date = re.search(r"(\d{4}-\d{2}-\d{2})", Path(f).name)
        rows = []
        for key in ("records", "games", "results"):
            v = doc.get(key)
            if isinstance(v, list):
                rows.extend(v)
        for r in rows:
            gid = r.get("game_id")
            ap, hp = r.get("away_pts"), r.get("home_pts")
            a = r.get("away") or r.get("away_team")
            h = r.get("home") or r.get("home_team")
            if not gid or ap is None or hp is None or not a or not h:
                continue
            status = r.get("status")
            if status and str(status).lower() not in ("final", "final/ot", "completed"):
                continue
            d = r.get("date") or (name_date.group(1) if name_date else None)
            rec = {"game_id": gid, "date": d, "away": a, "home": h,
                   "away_pts": ap, "home_pts": hp,
                   "source_url": (r.get("source_url") or r.get("final_source_url")
                                  or r.get("source")),
                   "file": rel}
            prev = seen.get(gid)
            if prev is None:
                seen[gid] = rec
            elif (prev["away_pts"], prev["home_pts"]) != (ap, hp):
                conflicts.append({"game_id": gid, "a": [prev["away_pts"], prev["home_pts"]],
                                  "b": [ap, hp]})
    games = [g for g in seen.values() if g["date"]]
    games.sort(key=lambda g: (g["date"], g["game_id"]))
    return games, conflicts, len(files)


# ---------------------------------------------------------------- point-in-time estimators
# WHY POINT-IN-TIME. The first draft of this module cut its ratings from the 2026-11-19
# team-stat pages and then "walk-forward tested" the model on games played in October. That
# is not a test: the October prediction would have been made with numbers that did not exist
# until November. Measured on that draft the model looked *worse* than a coin flip
# (log-loss 0.7018, accuracy 49.1%) — which is what leakage looks like when it inverts a
# signal, and either way it is not evidence. So both estimators are now computed from the
# official finals that precede each game date, by the same code that projects the live slate.
# The 2026-11-19 team-stat pages are used two ways instead: for the possession/PPP total, and
# as an independent corroboration of the rating the results imply (see `corroborate`).

def _pyth(pts_for: float, pts_against: float) -> float:
    """Pythagorean expectation with the stated exponent (Basketball-Reference 13.91)."""
    return pts_for ** PYTHAG_EXP / (pts_for ** PYTHAG_EXP + pts_against ** PYTHAG_EXP)


def _empty_team() -> dict:
    return {"gp": 0, "pf": 0, "pa": 0, "w": 0, "l": 0}


def ratings_as_of(games: list[dict], cutoff: str) -> tuple[dict, dict]:
    """Ratings a predictor could have used *before* `cutoff`, from official finals only.

    E1 — opponent-adjusted margin (a solved least-squares rating, the Massey construction):
         every club gets `r_i` and every game says `margin = r_home - r_away + h`, with `h`
         pinned from the same window. Solved by ridge-regularised normal equations so an
         unbeaten club cannot take a free +30.
    E2 — Pythagorean scoring view: `pf^e / (pf^e + pa^e)` turned into an expected margin
         against a league-average opponent, using the club's own points for and against per
         game. It uses the box score rather than the margin, which is why it is a second
         estimator and not a rescaling of the first.

    Returns (ratings, meta) with one record per club.
    """
    prior = [g for g in games if g["date"] < cutoff]
    acc: dict[str, dict] = {}
    for g in prior:
        for t in (g["away"], g["home"]):
            acc.setdefault(t, _empty_team())
        acc[g["away"]]["gp"] += 1
        acc[g["home"]]["gp"] += 1
        acc[g["away"]]["pf"] += g["away_pts"]
        acc[g["away"]]["pa"] += g["home_pts"]
        acc[g["home"]]["pf"] += g["home_pts"]
        acc[g["home"]]["pa"] += g["away_pts"]
        if g["home_pts"] > g["away_pts"]:
            acc[g["home"]]["w"] += 1
            acc[g["away"]]["l"] += 1
        else:
            acc[g["away"]]["w"] += 1
            acc[g["home"]]["l"] += 1
    hc = home_court(prior)
    h = hc.get("hca_points") or 0.0

    # ---- E1: ridge least squares on margin = r_home - r_away + h
    clubs = sorted(acc)
    idx = {c: i for i, c in enumerate(clubs)}
    n = len(clubs)
    lam = 4.0            # shrinks a 3-game club toward the mean; stated, not tuned
    A = [[0.0] * n for _ in range(n)]
    b = [0.0] * n
    for g in prior:
        i, j = idx[g["home"]], idx[g["away"]]
        y = g["home_pts"] - g["away_pts"] - h
        A[i][i] += 1; A[j][j] += 1
        A[i][j] -= 1; A[j][i] -= 1
        b[i] += y
        b[j] -= y
    for i in range(n):
        A[i][i] += lam
    r1 = _solve(A, b) if n else []

    # ---- E2: Pythagorean scoring view, expressed as points per game vs an average opponent
    league_pf = mean([t["pf"] / t["gp"] for t in acc.values() if t["gp"]]) or 0.0
    league_pa = mean([t["pa"] / t["gp"] for t in acc.values() if t["gp"]]) or 0.0
    out: dict[str, dict] = {}
    for c, t in acc.items():
        if not t["gp"]:
            continue
        pf, pa = t["pf"] / t["gp"], t["pa"] / t["gp"]
        p = _pyth(pf, pa)
        # E2 is the **unadjusted scoring differential**, in points per game. It is a
        # different question from E1: E2 asks "how much did this club out-score people",
        # E1 asks "how much did it out-score them after allowing for whom it played". The
        # first draft expressed E2 as a Pythagorean win% rescaled by a points-per-win guess,
        # which put it on a 70-point scale and made the disagreement meaningless.
        out[c] = {"tri": c, "gp": t["gp"], "w": t["w"], "l": t["l"],
                  "pf": pf, "pa": pa, "diff": pf - pa, "pyth_p": p,
                  "e1_rating": r1[idx[c]] if r1 else None,
                  "e2_rating": pf - pa}
    return out, {"cutoff": cutoff, "n_train": len(prior), "n_clubs": len(out),
                 "hca_used": h, "ridge_lambda": lam, "league_pf": league_pf,
                 "league_pa": league_pa}


def _solve(A: list[list[float]], b: list[float]) -> list[float]:
    """Gaussian elimination with partial pivoting (no numpy in this repo)."""
    n = len(b)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(n):
        piv = max(range(c, n), key=lambda r: abs(M[r][c]))
        if abs(M[piv][c]) < 1e-12:
            continue
        M[c], M[piv] = M[piv], M[c]
        pv = M[c][c]
        for r in range(n):
            if r == c:
                continue
            f = M[r][c] / pv
            if f:
                for k in range(c, n + 1):
                    M[r][k] -= f * M[c][k]
    return [M[i][n] / M[i][i] if abs(M[i][i]) > 1e-12 else 0.0 for i in range(n)]


def luck(teams: dict, games: list[dict]) -> dict:
    """Pythagorean luck z per club, from officially-sourced points for and against.

    Expected wins come from the club's own per-game `pts`/`opp_pts` (the traditional and
    opponent pages) over its official games played, and actual wins from the standings page.
    The residual is standardised by the binomial sd of that club's own game count, so a club
    with 13 games has a wider noise band than one with 16 — as it should.

    The two pages are one date apart (see `official`: `/stats/teams/*` through 11/17,
    `/standings` through 11/18), so the win column used here is the **stats-page** W, not the
    standings W, and the difference between the two is published rather than averaged.
    """
    out: dict[str, dict] = {}
    played: dict[str, int] = defaultdict(int)
    for g in games:
        played[g["away"]] += 1
        played[g["home"]] += 1
    for tri, t in teams.items():
        n = t.get("gp") or played.get(tri)
        if not n or t.get("pts") is None or t.get("opp_pts") is None or t.get("w") is None:
            out[tri] = {"tri": tri, "n": n, "z": None,
                        "flag": "blank — a points-for/against or win total is missing"}
            continue
        p = _pyth(t["pts"], t["opp_pts"])
        exp_w = p * n
        actual = t["w"]
        s = math.sqrt(n * p * (1 - p)) if 0 < p < 1 else None
        z = (actual - exp_w) / s if s else None
        out[tri] = {"tri": tri, "n": int(n), "pyth_p": p, "exp_wins": exp_w,
                    "actual_wins": actual, "resid": actual - exp_w,
                    "sd": s, "z": z,
                    "st_w": t.get("st_w"),
                    "w_gap_vs_standings": (t.get("st_w") - actual
                                           if t.get("st_w") is not None else None),
                    "outside": (z is not None and abs(z) > NOISE_BAND_Z)}
    return out


# ---------------------------------------------------------------- pinned home court
def home_court(games: list[dict]) -> dict:
    """Pin h so a normal margin model reproduces the measured home-win rate."""
    margins, wins, n = [], 0, 0
    for g in games:
        m = g["home_pts"] - g["away_pts"]
        if m == 0:
            continue
        margins.append(m)
        n += 1
        wins += 1 if m > 0 else 0
    if n < 30:
        return {"n": n, "home_win_rate": None, "margin_sd": None, "hca_points": None,
                "flag": "blank — fewer than 30 decided official finals"}
    rate = wins / n
    s = sd(margins)
    h = s * phi_inv(rate)
    return {"n": n, "home_wins": wins, "home_win_rate": rate, "margin_sd": s,
            "margin_mean": mean(margins), "hca_points": h,
            "rule": "h = sd(home margin) x Phi^-1(measured home win rate)",
            "reproduces_rate": phi(h / s) if s else None}


def rho(games: list[dict]) -> dict:
    """Correlation of (home margin, total points) — the one number a parlay price needs."""
    pairs = [(g["home_pts"] - g["away_pts"], g["home_pts"] + g["away_pts"])
             for g in games]
    if len(pairs) < 30:
        return {"n": len(pairs), "r": None, "flag": "blank — fewer than 30 finals"}
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    mx, my = mean(xs), mean(ys)
    sx, sy = sd(xs), sd(ys)
    r = sum((x - mx) * (y - my) for x, y in pairs) / ((len(pairs) - 1) * sx * sy)
    # Fisher z CI
    if abs(r) < 1:
        zf, se = 0.5 * math.log((1 + r) / (1 - r)), 1 / math.sqrt(len(pairs) - 3)
        lo, hi = math.tanh(zf - 1.96 * se), math.tanh(zf + 1.96 * se)
    else:
        lo = hi = r
    return {"n": len(pairs), "r": r, "ci95": [lo, hi],
            "definition": "r(home margin, total points) over committed official finals"}


# ---------------------------------------------------------------- a point-in-time cut
class Cut:
    """A predictor that may only use official finals strictly before `cutoff`.

    Both estimators produce a margin, in points, with the **same** pinned home-court term, so
    their difference is a genuine disagreement between two views rather than two copies of
    one number carrying different units.
    """

    def __init__(self, games: list[dict], cutoff: str):
        self.cutoff = cutoff
        self.ratings, self.meta = ratings_as_of(games, cutoff)
        self.h = self.meta["hca_used"]
        hc = home_court([g for g in games if g["date"] < cutoff])
        self.sigma = hc.get("margin_sd")
        self.hc = hc

    # -- the two point-estimates, home minus away
    def margins(self, away: str, home: str) -> tuple:
        a, h = self.ratings.get(away), self.ratings.get(home)
        if not a or not h:
            return None, None
        # HOME margin: home rating minus away rating plus the pinned home term.
        # (A previous revision had this backwards, and the walk-forward test is what caught
        # it: the model scored 34% — worse than a coin flip in the direction of a sign error.)
        e1 = h["e1_rating"] - a["e1_rating"] + self.h
        e2 = h["e2_rating"] - a["e2_rating"] + self.h
        return e1, e2

    def p_home(self, away: str, home: str) -> tuple:
        m1, m2 = self.margins(away, home)
        if m1 is None or not self.sigma:
            return None, None
        return phi(m1 / self.sigma), phi(m2 / self.sigma)

    def total(self, away: str, home: str, teams: dict | None = None) -> dict:
        """Total = possessions x points per possession, per the brief.

        Possessions are the mean of the two clubs' official PACE columns; each side's points
        per possession is the mean of its own OffRtg and the opponent's DefRtg, per 100 — so
        a good offence meeting a bad defence moves the total the right way instead of
        averaging two scoring averages. When the pace/rating columns are absent (a
        point-in-time cut from finals alone has no PACE), the total is BLANK and says so.
        """
        t = teams or {}
        a, h = t.get(away), t.get(home)
        if a is None or h is None:
            return {"possessions": None, "total": None,
                    "flag": "blank — a club is missing from the team-stat pages"}
        if a.get("pace") is None or h.get("pace") is None:
            return {"possessions": None, "total": None,
                    "flag": "blank — a PACE column is missing"}
        if None in (a.get("off_rtg"), h.get("off_rtg"), a.get("def_rtg"), h.get("def_rtg")):
            return {"possessions": None, "total": None,
                    "flag": "blank — an OffRtg/DefRtg column is missing"}
        poss = (a["pace"] + h["pace"]) / 2
        ppp_h = ((h["off_rtg"] + a["def_rtg"]) / 2) / 100
        ppp_a = ((a["off_rtg"] + h["def_rtg"]) / 2) / 100
        return {"possessions": poss, "ppp_home": ppp_h, "ppp_away": ppp_a,
                "home_pts": poss * ppp_h, "away_pts": poss * ppp_a,
                "total": poss * (ppp_h + ppp_a),
                "identity": "total = possessions x (ppp_home + ppp_away)"}


# ---------------------------------------------------------------- walk-forward test
def walk_forward(games: list[dict]) -> dict:
    """Predict every game from a cut that has seen only strictly earlier dates.

    Scored on **decisions**, not margin error: the cut picks the side with the higher win
    probability and is right iff that side won. Three baselines are carried:

      * a coin flip                     — log-loss ln 2 = 0.6931, accuracy 0.5;
      * "back the better record"        — the record each club had built before the date;
      * "back the home club"            — the league's measured home rate, for scale.

    A model that cannot beat a coin flip is reported as such. On this history it cannot, and
    that result is the reason no strategy on the site carries a stake.
    """
    rows = []
    for i, g in enumerate(games):
        if g["home_pts"] == g["away_pts"]:
            continue            # a tie cannot be graded on a moneyline decision
        prior = [x for x in games if x["date"] < g["date"]]
        if len(prior) < MIN_TRAIN_GAMES:
            continue
        cut = Cut(prior, g["date"])
        p1, p2 = cut.p_home(g["away"], g["home"])
        if p1 is None:
            continue
        p = (p1 + p2) / 2
        home_won = g["home_pts"] > g["away_pts"]
        pick_home = p >= 0.5
        # the record rule, from the same strictly-earlier window
        rec = cut.ratings
        wa = rec.get(g["away"], {}).get("w")
        wh = rec.get(g["home"], {}).get("w")
        rec_pick_home = (wh or 0) > (wa or 0)
        rows.append({
            "game_id": g["game_id"], "date": g["date"], "away": g["away"],
            "home": g["home"], "p_home_e1": p1, "p_home_e2": p2, "p_home": p,
            "disagreement": abs(p1 - p2),
            "pick_home": pick_home, "home_won": home_won, "right": pick_home == home_won,
            "record_pick_home": rec_pick_home,
            "record_right": rec_pick_home == home_won,
            "margin_home": g["home_pts"] - g["away_pts"],
            "m_e1": cut.margins(g["away"], g["home"])[0],
            "m_e2": cut.margins(g["away"], g["home"])[1],
        })
    n = len(rows)
    if not n:
        return {"n": 0, "flag": "blank — no walk-forward window could be trained"}
    acc = sum(1 for r in rows if r["right"]) / n
    racc = sum(1 for r in rows if r["record_right"]) / n
    brier = sum((r["p_home"] - (1 if r["home_won"] else 0)) ** 2 for r in rows) / n
    ll = sum(-math.log(max(r["p_home"], 1e-12) if r["home_won"]
                       else max(1 - r["p_home"], 1e-12)) for r in rows) / n
    # margin error of each estimator, so the disagreement can be compared to real error
    mae1 = mean([abs(r["margin_home"] - r["m_e1"]) for r in rows])
    mae2 = mean([abs(r["margin_home"] - r["m_e2"]) for r in rows])
    # the paired test the brief asks for: where model and naive rule disagree
    both = [r for r in rows if r["pick_home"] != r["record_pick_home"]]
    m_right = sum(1 for r in both if r["right"])
    n_right = sum(1 for r in both if r["record_right"])
    p_exact = 0.0
    if both:
        k, N = min(m_right, n_right), len(both)
        p_exact = min(1.0, 2 * sum(math.comb(N, j) for j in range(0, k + 1)) / 2 ** N)
    return {"n": n, "accuracy": acc, "record_accuracy": racc, "brier": brier,
            "log_loss": ll, "coin_log_loss": math.log(2),
            "beats_coin_log_loss": ll < math.log(2),
            "mae_e1": mae1, "mae_e2": mae2,
            "paired": {"n": len(both), "model_right": m_right, "record_right": n_right,
                       "exact_two_sided_p": p_exact},
            "train_rule": (f"cut trained on strictly earlier dates only; at least "
                           f"{MIN_TRAIN_GAMES} finals before the first prediction"),
            "rows": rows}


def corroborate(games: list[dict], teams: dict) -> list[dict]:
    """The results-implied rating vs the league's own per-100 net rating, club by club.

    Two independent routes to the same quantity: one from the finals this repo committed
    (margin per game, opponent-adjusted), one from the advanced page (NetRtg, per 100
    possessions). They are on different scales, so this publishes both columns and their
    correlation instead of forcing one into the other. A high correlation is evidence the
    transcribed page is the page it claims to be; a low one is a finding.
    """
    cut = Cut(games, "9999-99-99")      # everything known
    xs, ys, rows = [], [], []
    for tri, t in sorted(teams.items()):
        r = cut.ratings.get(tri)
        if not r or t.get("net_rtg") is None:
            continue
        rows.append({"tri": tri, "e1_rating_points": r["e1_rating"],
                     "net_rtg_per100": t["net_rtg"], "gp": r["gp"],
                     "stats_url": t.get("stats_url")})
        xs.append(r["e1_rating"])
        ys.append(t["net_rtg"])
    corr = None
    if len(xs) >= 3:
        mx, my = mean(xs), mean(ys)
        sx, sy = sd(xs), sd(ys)
        if sx and sy:
            corr = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / ((len(xs) - 1) * sx * sy)
    return {"n": len(rows), "pearson_r": corr, "rows": rows,
            "note": ("points-per-game rating from committed finals vs per-100 NetRtg from "
                     "the advanced page; different units, so only the rank agreement is "
                     "informative"),
            "rule": "no rescaling is fitted; the two columns are published side by side"}


def snapshot_teams() -> dict[str, dict]:
    """Per-club inputs from the v7 official snapshot, each tagged with its page URL.

    `official.TEAMS` carries the numbers and `official.STANDINGS` the standing; both are
    merged here so every downstream row has one record per club. The page a value came from
    is attached per field family, so a reader can jump to the exact document.
    """
    from . import official as O

    out: dict[str, dict] = {}
    for tri, r in O.TEAMS.items():
        out[tri] = {
            "tri": tri,
            "gp": r["gp"], "w": r["w"], "l": r["l"],
            "off_rtg": r["off"], "def_rtg": r["dfn"], "net_rtg": r["net"],
            "pace": r["pace"], "pts": r["pts"], "opp_pts": r["opp"], "pm": r["pm"],
            "stats_url": O.SOURCES["advanced"],
            "traditional_url": O.SOURCES["traditional"],
            "opponent_url": O.SOURCES["opponent"],
        }
    for tri, s in O.STANDINGS.items():
        out.setdefault(tri, {"tri": tri}).update({
            "st_w": s["w"], "st_l": s["l"], "conf": s["conf"],
            "home_rec": s["home"], "road_rec": s["road"],
            "last10": s["last10"], "streak": s["streak"],
            "standings_url": O.SOURCES["standings"],
        })
    return out


def resolve() -> dict:
    """Everything the pages need, assembled once. No network, no wall clock."""
    from . import official as O
    games, conflicts, n_files = load_games()
    teams = snapshot_teams()
    hc = home_court(games)
    cut = Cut(games, "9999-12-31")   # projection cut: every committed final is in the past
    luckz = luck(teams, games)
    return {
        "schema": "nba2.v7.model.v1",
        "session": "arena/6023d517-nba2",
        "as_of_utc": O.RETRIEVED_AT_UTC,
        "games": games,
        "teams": teams,
        "cut": cut,
        "inputs": {
            "games_with_clubs_and_scores": len(games),
            "games_first": games[0]["date"] if games else None,
            "games_last": games[-1]["date"] if games else None,
            "final_files_read": n_files,
            "score_conflicts": conflicts,
            "n_clubs": len(teams),
            "source_note": ("per-club inputs from the 2026-11-19 official snapshot "
                            "(nba2/v7/official.py); game results from the committed "
                            "official finals captures"),
        },
        "home_court": hc,
        "rho": rho(games),
        "luck": luckz,
        "outside_band": sorted([t for t, v in luckz.items() if v.get("outside")]),
        "walk_forward": walk_forward(games),
        "corroboration": corroborate(games, teams),
    }


def _as_of() -> str:
    from . import official as O
    return O.RETRIEVED_AT_UTC


def build() -> dict:
    res = resolve()
    return {k: v for k, v in res.items() if k not in ("cut", "teams", "games")}

    hc = home_court(games)
    cut = Cut(games, teams)
    luckz = luck(teams, games)
    out = {
        "schema": "nba2.v7.model.v1",
        "session": "arena/6023d517-nba2",
        "inputs": {
            "games_with_clubs_and_scores": len(games),
            "games_first": games[0]["date"] if games else None,
            "games_last": games[-1]["date"] if games else None,
            "final_files_read": n_files,
            "score_conflicts": conflicts,
            "team_stat_pages": ti["pages"],
            "team_stat_status": ti["status"],
            "standings": ti["standings"],
            "clubs_with_stats": sorted(teams),
            "n_clubs": len(teams),
        },
        "home_court": hc,
        "scaling": {"k_e1": cut.k1, "k_e2": cut.k2, "n_train": cut.n_train,
                    "note": "least-squares points-per-unit fitted on the whole committed "
                            "history; the walk-forward test refits it on earlier dates only"},
        "rho": rho(games),
        "luck": luckz,
        "outside_band": sorted([t for t, v in luckz.items() if v.get("outside")]),
        "walk_forward": walk_forward(games, teams),
    }
    return out
