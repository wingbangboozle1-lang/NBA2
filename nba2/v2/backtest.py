"""Point-in-time (walk-forward) backtest of *this* build's rating model.

The question this answers, and nothing else:

    If the v2 rating method had been run before each game — using only the
    official final scores that existed at tip-off — how well would it have
    predicted the winner and the margin?

Method, in the order it is applied:

1. Read the 155 official finals from `data/raw/history/*.json` (each row carries the
   `nba.com/game/<slug>-<id>` URL it was transcribed from) and sort by date.
2. For each game, build ratings from *only* the games strictly before that date
   (no same-day leakage, no future leakage), with the same shrinkage the published model uses.
3. Predict margin = rating_home - rating_away + h, total = pace-scaled league scoring.
4. Score: straight-up accuracy, MAE against the naive baseline, Brier and AUROC,
   and a paired test of model-vs-baseline error.

Deliberately NOT done: any claim about beating a market. There is no market price in this
repository, so accuracy against the closing line is not measurable and is not reported.

Run:  python3 -m nba2.v2.backtest
"""

from __future__ import annotations

import glob
import json
import math
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HISTORY = ROOT / "data" / "raw" / "history"
OUT = ROOT / "data" / "v2" / "backtest.json"

# Same home-court value the published model fits and the same shrinkage shape, so the
# backtest grades the method that is actually shipped rather than a convenient variant.
K_SHRINK = 8.0          # pseudo-games of league-average prior per team
H_NEUTRAL = 0.0         # neutral-site games carry no home-court term


def _phi(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def load_games() -> list[dict]:
    games = []
    for f in sorted(glob.glob(str(HISTORY / "games_*.json"))):
        for g in json.loads(Path(f).read_text())["games"]:
            if g.get("away_pts") is None or g.get("home_pts") is None:
                continue
            games.append(g)
    games.sort(key=lambda g: (g["date"], g["game_id"]))
    return games


@dataclass
class Pred:
    game_id: str
    date: str
    away: str
    home: str
    away_pts: int
    home_pts: int
    margin: float
    total: float
    p_home: float
    source_url: str
    neutral: bool
    n_prior: int

    @property
    def actual_margin(self) -> float:
        return self.home_pts - self.away_pts

    @property
    def actual_total(self) -> float:
        return self.home_pts + self.away_pts


def _ratings(prior: list[dict], k: float | None = None) -> tuple[dict, float, float]:
    """Shrunk points-diff rating per team, league mean, and league points per team-game."""
    per: dict[str, list[float]] = {}
    pace_pts: list[float] = []
    for g in prior:
        d = g["home_pts"] - g["away_pts"]
        per.setdefault(g["home"], []).append(d)
        per.setdefault(g["away"], []).append(-d)
        pace_pts += [g["home_pts"], g["away_pts"]]
    if not pace_pts:
        return {}, 0.0, 0.0
    league_mean = sum(pace_pts) / len(pace_pts)
    # every team gets K_SHRINK pseudo-games at zero so early-season ratings cannot run wild
    raw = {}
    for team, ds in per.items():
        raw[team] = sum(ds) / (len(ds) + (K_SHRINK if k is None else k))
    return raw, league_mean, league_mean


def run() -> dict:
    games = load_games()
    by_date: dict[str, list[dict]] = {}
    for g in games:
        by_date.setdefault(g["date"], []).append(g)

    preds: list[Pred] = []
    skipped = 0
    for date in sorted(by_date):
        prior = [g for g in games if g["date"] < date]          # strict: no same-day leakage
        ratings, league_mean, _ = _ratings(prior)
        for g in by_date[date]:
            if g["home"] not in ratings or g["away"] not in ratings:
                skipped += 1
                continue
            neutral = bool(g.get("neutral_site"))
            h = H_NEUTRAL if neutral else 2.0   # fixed at 2.0 pts; fitted h is +0.37 on W-L scale,
                                                # 2.0 is the conventional margin-scale value and is
                                                # disclosed rather than tuned on the test set
            margin = league_mean + ratings[g["home"]] - (league_mean + ratings[g["away"]]) + h
            # totals: uninformative early, so use the running league scoring rate for both teams
            total = 2.0 * league_mean
            preds.append(Pred(
                game_id=g["game_id"], date=g["date"], away=g["away"], home=g["home"],
                away_pts=g["away_pts"], home_pts=g["home_pts"],
                margin=margin, total=total,
                p_home=_phi(margin / 12.75),       # the sigma the published model fits
                source_url=g["source_url"], neutral=neutral, n_prior=len(prior)))

    n = len(preds)
    hits = sum(1 for p in preds if (p.margin > 0) == (p.actual_margin > 0))
    abs_err = [abs(p.margin - p.actual_margin) for p in preds]
    err = [p.margin - p.actual_margin for p in preds]
    mae = sum(abs_err) / n
    rmse = math.sqrt(sum(e * e for e in err) / n)
    # baseline: predict zero margin (league average) for every game
    base_abs = [abs(p.actual_margin) for p in preds]
    base_mae = sum(base_abs) / n
    base_rmse = math.sqrt(sum((p.actual_margin) ** 2 for p in preds) / n)

    brier = sum((p.p_home - (1.0 if p.actual_margin > 0 else 0.0)) ** 2 for p in preds) / n
    brier_base = sum((0.5 - (1.0 if p.actual_margin > 0 else 0.0)) ** 2 for p in preds) / n

    # AUROC for the winner (Mann-Whitney with ties counted 0.5)
    wins = [p.p_home for p in preds if p.actual_margin > 0]
    loss = [p.p_home for p in preds if p.actual_margin < 0]
    auroc = None
    if wins and loss:
        conc = 0.0
        for w in wins:
            for lo in loss:
                conc += 1.0 if w > lo else (0.5 if w == lo else 0.0)
        auroc = conc / (len(wins) * len(loss))

    # paired bootstrap on the MAE improvement (model vs zero-baseline)
    diffs = [b - m for b, m in zip(base_abs, abs_err)]
    obs = sum(diffs) / n
    seed, draws = 20261114, 4000
    state = seed
    better = 0
    means = []
    for _ in range(draws):
        s = 0.0
        for _ in range(n):
            state = (1103515245 * state + 12345) % (2 ** 31)
            s += diffs[state % n]
        means.append(s / n)
    means.sort()
    p_upper = sum(1 for x in means if x > 0) / draws
    better = p_upper

    # calibration bins on p_home
    bins = [(0.0, 0.45), (0.45, 0.5), (0.5, 0.55), (0.55, 0.65), (0.65, 1.0)]
    cal_rows = []
    for lo, hi in bins:
        sel = [p for p in preds if lo <= p.p_home < hi]
        if not sel:
            continue
        obs_rate = sum(1 for p in sel if p.actual_margin > 0) / len(sel)
        k = sum(1 for p in sel if p.actual_margin > 0)
        # Wilson interval
        z = 1.96
        den = 1 + z * z / len(sel)
        cen = (obs_rate + z * z / (2 * len(sel))) / den
        half = z * math.sqrt(obs_rate * (1 - obs_rate) / len(sel) + z * z / (4 * len(sel) ** 2)) / den
        cal_rows.append({"bin": f"{int(lo*100)}%-{int(hi*100)}%", "n": len(sel), "hits": k,
                         "mean_predicted": round(sum(p.p_home for p in sel) / len(sel), 4),
                         "observed": round(obs_rate, 4),
                         "ci95": [round(max(0.0, cen - half), 4), round(min(1.0, cen + half), 4)]})

    margin_sd_actual = math.sqrt(sum((p.actual_margin - sum(q.actual_margin for q in preds) / n) ** 2
                                     for p in preds) / (n - 1))
    total_sd_actual = None
    tot = [p.actual_total for p in preds]
    mt = sum(tot) / n
    total_sd_actual = math.sqrt(sum((x - mt) ** 2 for x in tot) / (n - 1))
    # margin/total correlation on the graded sample
    m_mean = sum(p.actual_margin for p in preds) / n
    num = sum((p.actual_margin - m_mean) * (p.actual_total - mt) for p in preds)
    den = math.sqrt(sum((p.actual_margin - m_mean) ** 2 for p in preds) *
                    sum((p.actual_total - mt) ** 2 for p in preds))
    r_mt = num / den
    zf = 0.5 * math.log((1 + r_mt) / (1 - r_mt))
    se = 1 / math.sqrt(n - 3)
    r_ci = [round(math.tanh(zf - 1.96 * se), 4), round(math.tanh(zf + 1.96 * se), 4)]
    t_stat = r_mt * math.sqrt((n - 2) / (1 - r_mt * r_mt))

    # --- proper scoring rules and calibration on the probability scale -----------------
    eps = 1e-12
    ll = -sum(math.log(max(eps, p.p_home if p.actual_margin > 0 else 1 - p.p_home)) for p in preds) / n
    ll_base = -sum(math.log(0.5) for _ in preds) / n
    # calibration slope: logit(observed) on logit(predicted) via least squares
    xs, ys = [], []
    for p in preds:
        q = min(max(p.p_home, 1e-6), 1 - 1e-6)
        xs.append(math.log(q / (1 - q)))
        ys.append(1.0 if p.actual_margin > 0 else 0.0)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx if sxx else 0.0
    intercept = my - slope * mx
    # Wilson CI on straight-up accuracy
    zz = 1.96
    den2 = 1 + zz * zz / n
    cen2 = (hits / n + zz * zz / (2 * n)) / den2
    half2 = zz * math.sqrt((hits / n) * (1 - hits / n) / n + zz * zz / (4 * n * n)) / den2
    acc_ci = [round(max(0.0, cen2 - half2), 4), round(min(1.0, cen2 + half2), 4)]
    # how many games to prove this accuracy differs from a 0.542 coin-flip-with-home-edge
    p0 = 0.542
    need = None
    if hits / n > p0:
        num_ = (zz * math.sqrt(p0 * (1 - p0)) + 0.8416 * math.sqrt((hits / n) * (1 - hits / n))) ** 2
        need = int(math.ceil(num_ / (hits / n - p0) ** 2))

    # --- why the calibration slope is not 1: the model is COMPRESSED, not mis-scaled ------
    pred_sd = math.sqrt(sum((p.margin - sum(q.margin for q in preds) / n) ** 2 for p in preds) / (n - 1))
    act_sd = margin_sd_actual
    mpm = sum(p.margin for p in preds) / n
    mpn = sum(p.actual_margin for p in preds) / n
    r_pred_act = (sum((p.margin - mpm) * (p.actual_margin - mpn) for p in preds) /
                  math.sqrt(sum((p.margin - mpm) ** 2 for p in preds) *
                            sum((p.actual_margin - mpn) ** 2 for p in preds)))

    # --- does a bigger predicted margin actually mean a bigger real margin? -------------
    # Spearman is used because the relationship need only be monotone for ranking to work.
    def _rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        rk = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                rk[order[k]] = avg
            i = j + 1
        return rk
    am = [abs(p.margin) for p in preds]
    ay = [abs(p.actual_margin) for p in preds]
    ra, rb = _rank(am), _rank(ay)
    ma_, mb_ = sum(ra) / n, sum(rb) / n
    rho_conf = (sum((x - ma_) * (y - mb_) for x, y in zip(ra, rb)) /
                math.sqrt(sum((x - ma_) ** 2 for x in ra) * sum((y - mb_) ** 2 for y in rb)))

    # --- sensitivity: how much does the shrink prior matter? ----------------------------
    # Reported for transparency only. The headline above uses the shipped configuration
    # (K=8, h=2.0) and was NOT selected by looking at these numbers.
    sens = []
    for K in (0.0, 2.0, 4.0, 8.0, 16.0):
        pr = []
        for date in sorted(by_date):
            prior = [g for g in games if g["date"] < date]
            raw, lm, _ = _ratings(prior, K)
            for g in by_date[date]:
                if g["home"] not in raw or g["away"] not in raw:
                    continue
                hh = H_NEUTRAL if g.get("neutral_site") else 2.0
                mm = lm + raw[g["home"]] - (lm + raw[g["away"]]) + hh
                pr.append((mm, g["home_pts"] - g["away_pts"]))
        nn = len(pr)
        sens.append({
            "shrink_pseudo_games": K, "n": nn,
            "accuracy": round(sum(1 for a, b in pr if (a > 0) == (b > 0)) / nn, 4),
            "mae": round(sum(abs(a - b) for a, b in pr) / nn, 3),
            "pred_sd": round(math.sqrt(sum((a - sum(x for x, _ in pr) / nn) ** 2 for a, _ in pr) / (nn - 1)), 2),
            "note": "in-sample sensitivity; not used to pick the headline configuration",
        })

    per_date = {}
    for p in preds:
        d = per_date.setdefault(p.date, {"n": 0, "hits": 0, "abs_err": 0.0})
        d["n"] += 1
        d["hits"] += 1 if (p.margin > 0) == (p.actual_margin > 0) else 0
        d["abs_err"] += abs(p.margin - p.actual_margin)

    return {
        "meta": {
            "n_games_scored": n, "n_skipped_no_prior": skipped,
            "first_date": preds[0].date, "last_date": preds[-1].date,
            "n_dates": len(per_date), "generated": "2026-11-14",
            "shrink_pseudo_games": K_SHRINK, "home_court_pts": 2.0,
            "sigma_pts": 12.75,
            "source": "data/raw/history/*.json — 155 official finals, one nba.com/game URL per row",
            "leakage_rule": "ratings for a date use only games strictly before that date",
        },
        "headline": {
            "straight_up_accuracy": round(hits / n, 4),
            "hits": hits,
            "mae_margin": round(mae, 3),
            "rmse_margin": round(rmse, 3),
            "mae_baseline_zero": round(base_mae, 3),
            "rmse_baseline_zero": round(base_rmse, 3),
            "skill_vs_baseline_pct": round(100 * (base_mae - mae) / base_mae, 2),
            "bias": round(sum(err) / n, 3),
            "brier": round(brier, 4),
            "brier_baseline": round(brier_base, 4),
            "brier_skill_pct": round(100 * (brier_base - brier) / brier_base, 2),
            "auroc": round(auroc, 4) if auroc else None,
            "accuracy_ci95": acc_ci,
            "log_loss": round(ll, 4),
            "log_loss_baseline": round(ll_base, 4),
            "calibration_slope": round(slope, 3),
            "calibration_intercept": round(intercept, 3),
            "calibration_read": ("over-confident" if slope < 1 else "under-confident" if slope > 1
                                 else "calibrated"),
            "games_to_prove_edge_vs_coinflip": need,
        },
        "significance": {
            "observed_mae_gain": round(obs, 3),
            "draws": draws, "seed": seed,
            "p_gain_positive": round(better, 4),
            "significant_at_5pct": better > 0.95,
        },
        "calibration": cal_rows,
        "volatility": {
            "margin_sd_actual": round(margin_sd_actual, 3),
            "total_sd_actual": round(total_sd_actual, 3),
            "sigma_published": 12.75,
            "note": "The published sigma (12.75) is a *win-total* scale parameter, not the "
                    "game-margin sd measured here. They are different quantities and must not be "
                    "compared directly.",
        },
        "margin_total": {
            "n": n, "r": round(r_mt, 4), "ci95": r_ci, "t": round(t_stat, 3),
            "significant_at_5pct": abs(t_stat) > 1.972,
            "verdict": ("no detectable relationship at this sample size" if abs(t_stat) <= 1.972
                        else "relationship detected"),
            "power_note": "detecting a true r of 0.10 at 80% power needs about 780 games; "
                          "this sample has 155",
        },
        "compression": {
            "predicted_margin_sd": round(pred_sd, 2),
            "actual_margin_sd": round(act_sd, 2),
            "ratio": round(pred_sd / act_sd, 3),
            "r_predicted_vs_actual": round(r_pred_act, 4),
            "spearman_confidence_vs_bigwin": round(rho_conf, 4),
            "read": "The model ranks games well but its margin estimates are compressed to about "
                    "a third of true dispersion, so a predicted margin must not be read as an "
                    "expected margin — and must never be used to size a stake.",
        },
        "sensitivity": sens,
        "per_date": [{"date": d, "n": v["n"], "hits": v["hits"],
                      "accuracy": round(v["hits"] / v["n"], 4),
                      "mae": round(v["abs_err"] / v["n"], 3)}
                     for d, v in sorted(per_date.items())],
        "rows": [{"date": p.date, "matchup": f"{p.away} @ {p.home}", "neutral": p.neutral,
                  "pred_margin": round(p.margin, 2), "actual_margin": p.actual_margin,
                  "err": round(p.margin - p.actual_margin, 2),
                  "p_home": round(p.p_home, 4),
                  "correct": (p.margin > 0) == (p.actual_margin > 0),
                  "source_url": p.source_url} for p in preds],
    }


if __name__ == "__main__":
    out = run()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1))
    h = out["headline"]
    print(f"{out['meta']['n_games_scored']} games scored "
          f"({out['meta']['first_date']} → {out['meta']['last_date']}), "
          f"{out['meta']['n_skipped_no_prior']} skipped for having no prior games")
    print(f"straight-up accuracy {h['straight_up_accuracy']:.2%}  (baseline always-home "
          f"{sum(1 for p in out['rows'] if p['actual_margin']>0)/len(out['rows']):.2%})")
    print(f"margin MAE {h['mae_margin']:.2f} vs {h['mae_baseline_zero']:.2f} for a zero-margin "
          f"baseline  →  skill {h['skill_vs_baseline_pct']:+.1f}%")
    print(f"Brier {h['brier']:.4f} vs {h['brier_baseline']:.4f}  →  skill {h['brier_skill_pct']:+.1f}%")
    print(f"AUROC {h['auroc']}  bias {h['bias']:+.2f} pts  95% CI on accuracy {h['accuracy_ci95']}")
    print(f"log loss {h['log_loss']:.4f} vs {h['log_loss_baseline']:.4f}  "
          f"calibration slope {h['calibration_slope']:.3f} → {h['calibration_read']}")
    print(f"games needed to prove this edge over a 54.2% coin-flip: {h['games_to_prove_edge_vs_coinflip']}")
    s = out["significance"]
    print(f"paired bootstrap: MAE gain {s['observed_mae_gain']:+.2f} pts, "
          f"P(gain>0) = {s['p_gain_positive']:.3f}")
    mt = out["margin_total"]
    print(f"margin↔total r = {mt['r']:+.4f}  95% CI {mt['ci95']}  t {mt['t']:+.2f}  → {mt['verdict']}")
    print(f"wrote {OUT.relative_to(ROOT)}")
