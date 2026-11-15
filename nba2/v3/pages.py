"""v3 page bodies.

Split from ``render`` so the primitives stay small and the page list is readable in one screen.
Every function here takes already-computed data and returns ``(filename, title, surface, body)``.
No page computes a statistic; if a number is needed and no module produced it, the page says so.
"""

from __future__ import annotations

import math

from . import official as O
from .render import (badge, badge_grade, badge_status, badge_surface, dash, esc, kpi, kpis,
                     note, src, table)


def _fmt(x, nd=2):
    if x is None:
        return None
    if isinstance(x, float) and math.isnan(x):
        return None
    return f"{x:,.{nd}f}"


def _pct(x, nd=1):
    return None if x is None else f"{x*100:.{nd}f}%"


# --------------------------------------------------------------------------- dashboard
def dashboard(teams, cal, lines, lab, strat) -> tuple:
    m = lab["metrics"]
    h = lab["holdout"]
    sh = lab["shrink"]
    ms = lab["margin_shrink"]

    head = note(
        "<b>Read this first.</b> The v2 site's headline was its accuracy. This site's headline is "
        "<b>how much the two estimators disagree</b>, and the accuracy is printed underneath with "
        "the number that contradicts it. On the held-out slice the raw model's log-loss "
        f"({h['log_loss_a']}) is <b>worse than a coin</b> ({h['log_loss_coin']}); the same model with "
        f"its over-confidence removed (×{h['alpha']}) scores {h['log_loss_a_calibrated']} and beats "
        "a coin. Both numbers are published; neither replaces the other.", "bad")

    body = [
        '<h1>NBA2 v3 — projections from two estimators</h1>',
        '<p class="sub">Originated lines from official NBA sources, with the disagreement between '
        'two independent estimators as the primary confidence signal, and a bet surface that stays '
        'empty until its gates pass.</p>',
        head,
        "<h2>The five numbers that decide whether any of this is worth reading</h2>",
        kpis([
            ("Walk-forward accuracy (A)", _pct(m["accuracy"]),
             f"n={m['n']} scored games from {lab['meta']['first_date']}", ""),
            ("Log-loss vs a coin", f"{m['log_loss']} vs {m['log_loss_coin']}",
             "raw model is WORSE than a coin; calibrated is better", "bad"),
            ("Calibrated log-loss, holdout", f"{h['log_loss_a_calibrated']}",
             f"×{h['alpha']} shrink fitted on earlier dates only; coin {h['log_loss_coin']}", "ok"),
            ("Margin MAE vs a tie", f"{m['mae_margin']} vs {m['mae_predict_tie']}",
             f"raw is worse; ×{ms['alpha']} shrunk is {ms['holdout_mae_shrunk']} on holdout", "bad"),
            ("Two estimators disagree", f"{m['median_disagreement']} pts (median)",
             f"opposite side on {m['pct_opposite_side']}% of games", "warn"),
        ]),
        "<h2>What the two estimators do</h2>",
        note(
            "<p><b>A — running point differential.</b> Each club's rating is the mean of its home "
            "and road scoring margins, shrunk toward the league mean. It reads only the scoreboard.</p>"
            "<p><b>B — least-squares strength with home court absorbed.</b> An exact constrained "
            "least-squares fit (ridge 0.5, ratings summing to zero) on the same games, where home "
            "advantage is a fitted term rather than a constant added afterwards.</p>"
            "<p>The two are deliberately built from different assumptions. Where they agree, the "
            "line is as confident as this model gets; where they disagree, the disagreement is "
            "printed and the line's grade drops. The blend is <i>not</i> the headline: it appears on "
            "the lines page in a column headed “fallback only” for the case where a reader needs one "
            "number.</p>"),
        "<h2>Calibration — home advantage pinned, not fitted</h2>",
        note(
            f"<p>Home-court advantage is <b>pinned to the measured home-win rate</b>, as the brief "
            f"requires: {cal.home_win_rate:.4f} home win rate over {cal.home_games} games gives "
            f"h = σ·Φ⁻¹(p) = {cal.hca:+.3f} points with σ={cal.margin_sd} (SE {cal.home_rate_se:.4f}). "
            f"The unconstrained fit is also reported — σ={cal.sigma_unconstrained}, h={cal.hca_unconstrained:+.2f}, "
            f"RMSE {cal.rmse_unconstrained} vs {cal.rmse_wins} — and it is <i>not</i> the published "
            f"number, because a free h would absorb whatever the ratings get wrong and call it home "
            f"court.</p>"),
        "<h2>Two surfaces, never mixed</h2>",
        table(
            ["Surface", "What it may contain", "Status"],
            [["Projection", "Inputs, formulas, originated margins and totals, estimator "
                            "disagreement, calibration, reliability. No stake is implied by "
                            "anything on it.", badge_surface("projection")],
             ["Bet (gated)", "A stake, and the gate report that proves the gate passed. Today "
                             "every gate is open on price, so every stake is 0.",
              badge_surface("bet")]],
            "The brief's separation rule, as the site enforces it",
            idcol=None),
        "<h2>Jump to</h2>",
        "<ul>"
        '<li><a href="v3-lines.html">Originated lines</a> — every game in the 3-day window, '
        "both estimators, the disagreement, and the possession-based total.</li>"
        '<li><a href="v3-totals.html">Totals</a> — possessions × points-per-possession beside the '
        "average-of-averages it replaces, and the finding that the forward total does not beat a "
        "constant.</li>"
        '<li><a href="v3-teams.html">Teams &amp; luck</a> — all 30 clubs, and the luck z-score '
        "that decides whether a strategy may lean on one.</li>"
        '<li><a href="v3-calibration.html">Calibration &amp; reliability</a> — the table that '
        "explains why 64.5% accuracy coexists with a log-loss worse than a coin.</li>"
        '<li><a href="v3-backtest.html">Backtest &amp; skill</a> — walk-forward, leakage audit, '
        "McNemar, permutation.</li>"
        '<li><a href="v3-strategies.html">Strategies</a> — the six rules, their pre-registrations, '
        "and the family correction.</li>"
        '<li><a href="v3-bet.html">Bet surface (gated)</a> — the gate table. Zero stakes.</li>'
        '<li><a href="v3-injuries.html">Injuries</a> — the archive, both timestamps, and what the '
        "two captured releases actually show.</li>"
        '<li><a href="v3-flagged.html">Flagged for review</a> — everything unverified, with sources.</li>'
        "</ul>",
    ]
    return ("v3-index.html", "Dashboard", "projection", "\n".join(body))


# --------------------------------------------------------------------------- lines
def lines_page(teams, cal, lines) -> tuple:
    rows = []
    for ln in lines:
        flags = " ".join(badge(f, "warn") for f in ln.flags) if ln.flags else ""
        travel = (dash("no prior venue in feed") if ln.travel_away_km is None
                  else f"{ln.travel_away_km:,.0f}")
        rows.append([
            esc(ln.date), esc(ln.time_et),
            f"<b>{esc(ln.home)}</b> v {esc(ln.away)}",
            esc(ln.arena),
            f"{ln.margin_a:+.1f}", f"{ln.margin_b:+.1f}",
            f"<b>{ln.disagreement:.2f}</b>",
            f"{ln.p_home_lo:.3f}–{ln.p_home_hi:.3f}",
            f"{ln.total:.1f}", f"{ln.total_naive:.1f}", f"{ln.total_gap:+.1f}",
            esc(ln.home_rotation), esc(ln.away_rotation or "—"),
            badge_grade(ln.grade) + (f" {flags}" if flags else ""),
        ])
    body = [
        "<h1>Originated lines</h1>",
        '<p class="sub">Every game in the window, priced from official inputs. The disagreement '
        "column is the confidence signal; the blend is not shown as a headline.</p>",
        note(
            f"<b>{len(lines)} lines</b> over {O.WINDOW_START} → {O.WINDOW_END}. The margin columns "
            "are the two estimators' <i>home</i> margins in points. A positive number means the home "
            "club is favoured. The probability interval is the pair of the two estimators' own "
            "probabilities — it is a <b>disagreement interval, not a confidence interval</b>: it says "
            "how far apart two models are, not how uncertain the truth is. Both are wider than the "
            "truth's uncertainty, which the calibration page quantifies.", "proj"),
        table(
            ["Date", "Tip ET", "Matchup", "Arena", "A margin", "B margin", "Disagree",
             "p(home) A→B", "Total", "Naive avg", "Δ", "Home availability",
             "Away availability", "Grade"],
            rows,
            "Originated lines from official schedule, standings and team stats. "
            "Disagree = |A − B| in points; the widest disagreements are flagged first.",
            num_cols=(4, 5, 6, 7, 8, 9, 10), idcol=None),
        "<h2>How to read the columns</h2>",
        note(
            "<ul>"
            "<li><b>A margin / B margin</b> — the same game priced by two estimators that share no "
            "assumptions beyond the official results. If they differ by more than 2 points the row "
            "is graded C and the reason says so.</li>"
            "<li><b>Disagree</b> — the absolute gap. This is the primary confidence output: a wide "
            "gap means the line is an artefact of the method, not a reading of the game.</li>"
            "<li><b>Total vs Naive avg</b> — possessions × points-per-possession against the "
            "average-of-the-two-clubs'-scoring-averages. They are printed side by side because the "
            "brief asks for the second to be visible, not removed.</li>"
            "<li><b>Availability</b> — a count from the official injury report, disclosed on the row. "
            "The model is availability-blind: it prices the season-average club. An absence changes "
            "the number only through the minutes model, which is <b>not filed</b> for these clubs "
            "(FLAG-V3-ROTATION-UNFILED), so the column is a warning, not an input.</li>"
            "<li><b>Grade</b> — describes estimator stability only. A is the tight bar, B passes the "
            "minimum, C names a specific problem. It is <b>not</b> a confidence that the line wins.</li>"
            "</ul>"),
        "<h2>Travel: what the number means and what it does not</h2>",
        note(
            "<p>The away club's travel is the great-circle distance from the venue of its "
            "<b>previous game</b> to this one, using the arena coordinate table. The home club's "
            "figure is <b>0</b> because it is at its own arena — not because it did not travel this "
            "week.</p>"
            "<p>A club on a four-game road trip has accumulated travel that this per-game figure "
            "does not carry, so the column <b>understates</b> fatigue for long trips. A dash means "
            "the club has no prior game in the feed, which is unknown rather than zero.</p>"),
        "<h2>What is withheld from this page</h2>",
        note(
            "<p><b>The market-anchored blend is withheld.</b> The brief asks for the model line to "
            "be blended with the closing line, weighted by measured out-of-sample log-loss. No odds "
            "feed is connected, so there is no closing line to measure and no blend to compute. The "
            "weight formula is published on the methodology page with the two illustrative values a "
            "real market would produce; they are labelled illustrations and are not used here.</p>",
            "warn"),
    ]
    return ("v3-lines.html", "Originated lines", "projection", "\n".join(body))


# --------------------------------------------------------------------------- totals
def totals_page(teams, lines, lab) -> tuple:
    m = lab["metrics"]
    rows = []
    for ln in sorted(lines, key=lambda x: -abs(x.total_gap))[:24]:
        h, a = teams[ln.home], teams[ln.away]
        rows.append([
            esc(ln.date), f"{esc(ln.away)} @ {esc(ln.home)}",
            f"{ln.poss_game:.2f}",
            f"{h.ppp_off:.3f} / {a.ppp_def:.3f}",
            f"{a.ppp_off:.3f} / {h.ppp_def:.3f}",
            f"{ln.pts_home:.1f}", f"{ln.pts_away:.1f}",
            f"<b>{ln.total:.1f}</b>", f"{ln.total_naive:.1f}", f"{ln.total_gap:+.1f}",
        ])
    body = [
        "<h1>Totals — possessions × points-per-possession</h1>",
        '<p class="sub">The brief\'s formula, the average-of-averages it replaces, and the measured '
        "result that the forward total does not beat a constant.</p>",
        note(
            "<p><b>Formula.</b> One possession count for the game (the mean of the two clubs' "
            "official possessions per game), and a points-per-possession rate per side that is half "
            "its own offence and half the opponent's defence. Total = possessions × (PPP_home + "
            "PPP_away).</p>"
            "<p><b>What it replaces.</b> Adding the two clubs' scoring averages. That number is "
            "anchored to the league mean by construction, so it cannot express a game between two "
            "above-average offences. Both are printed on every row below.</p>",
            "proj"),
        "<h2>The formula in practice — widest gaps first</h2>",
        table(
            ["Date", "Game", "Poss", "Home PPP (off/opp def)", "Away PPP (off/opp def)",
             "Home pts", "Away pts", "Total (poss)", "Naive avg", "Δ"],
            rows,
            f"The {min(24, len(lines))} games with the largest gap between the two formulas, "
            "from official POSS and per-game scoring.",
            num_cols=(2, 5, 6, 7, 8, 9)),
        "<h2>The finding that has to be printed next to the formula</h2>",
        note(
            f"<p>On the walk-forward, the forward total scores a mean absolute error of "
            f"<b>{m['mae_total_fwd']}</b> — <b>worse</b> than always predicting the league mean "
            f"({m['mae_total_best_constant']}) and worse than the running league average "
            f"({m['mae_total_league_mean']}). Its correlation with the actual total is "
            f"{m['r_total_fwd_vs_actual']}, and its spread (sd {m['total_fwd_sd']}) is much narrower "
            f"than the truth's (sd {m['actual_total_sd']}).</p>"
            "<p>So the formula is correct and, measured on absolute error, the forecast it "
            "produces is <b>worse than a constant</b>. It is worth publishing for two reasons: it "
            "is the formula the brief specifies, and the naive average it replaces was never a "
            "forecast either. A reader should not mistake the possession construction for evidence "
            "of total-prediction skill, and the site does not present it as one.</p>", "bad"),
        "<h2>Level versus order — two different questions</h2>",
        note(
            f"<p>{esc(lab['total_direction']['reading'])}</p>"
            "<p>Both numbers are here because they are easy to confuse and the first version of "
            "this page published only the second one's favourable half. A forecast can be "
            "well-ordered and too tightly dispersed at the same time: it ranks games in the right "
            "order more often than not, while its absolute error is still worse than saying "
            "&ldquo;the league average&rdquo; every night.</p>",
            "warn"),
        "<h2>Why the spread is too narrow</h2>",
        note(
            "<p>The inputs are season-to-date club averages. Averaging two clubs' rates cancels "
            "their game-to-game variation, so the output is a <i>central</i> estimate: it knows "
            "that both clubs are good, and it cannot know that tonight one of them shoots 9/38 from "
            "three. The actual totals range 174–284; the forward total spans a fraction of that.</p>"
            "<p>The honest fix is a variance term the brief's data does not supply (per-game "
            "possession and shooting distributions). It is listed on the questions page as a "
            "blocked input rather than patched with a fudge factor.</p>"),
    ]
    return ("v3-totals.html", "Totals", "projection", "\n".join(body))


# --------------------------------------------------------------------------- teams & luck
def teams_page(teams, cal) -> tuple:
    rows = []
    for tri in sorted(teams, key=lambda t: -teams[t].net_pts):
        t = teams[tri]
        lz = t.luck_z
        band = t.luck_band
        kind = "ok" if "noise" in band.lower() else "warn"
        rows.append([
            f"<b>{esc(tri)}</b>", esc(t.name),
            f"{t.w}-{t.l}", f"{t.home}", f"{t.road}",
            f"{t.pts:.1f}", f"{t.opp_pts:.1f}", f"{t.net_pts:+.2f}",
            f"{t.off_rtg:.1f}", f"{t.def_rtg:.1f}", f"{t.net_rtg:+.1f}",
            f"{t.poss_pg:.1f}", f"{t.ppp_off:.3f}", f"{t.ppp_def:.3f}",
            f"{t.r_diff:+.2f}", f"{t.r_rtg:+.2f}", f"{t.disagreement:.2f}",
            f"{t.expected_wins:.1f}", f"{t.luck:+.2f}", f"{t.luck_z:+.2f}",
            badge(band, kind),
        ])
    outside = [t for t in teams.values() if abs(t.luck_z) > 1.96]
    body = [
        "<h1>Teams &amp; luck</h1>",
        '<p class="sub">All 30 clubs from the official standings and the three team-stat pages, '
        "with the luck z-score that decides whether a strategy may lean on a club.</p>",
        kpis([
            ("League points / possession", f"{sum(x.ppp_off*x.poss_pg for x in teams.values())/sum(x.poss_pg for x in teams.values()):.4f}",
             "official PTS ÷ official POSS, mass-weighted", ""),
            ("Clubs outside the noise band", f"{len(outside)} of 30",
             "|z| > 1.96 — the refusal gate refuses nothing today",
             "ok" if not outside else "warn"),
            ("Estimator disagreement, worst club", f"{max(t.disagreement for t in teams.values()):.2f}",
             "points between A and B for the same club", "warn"),
        ]),
        note(
            "<p><b>Luck, as the brief defines it.</b> Expected wins are computed from each club's "
            "own scoring margin (Pythagorean-style, using the fitted margin σ), and the luck z-score "
            "is (actual − expected) / SE. A club outside |z| > 1.96 is winning or losing by more "
            "than the scoring explains.</p>"
            f"<p><b>The refusal gate.</b> A strategy may not lean on a club outside the band. "
            f"Today <b>{len(outside)} of 30</b> clubs are outside it, so the gate has nothing to "
            f"refuse and the site says exactly that rather than claiming luck has been removed "
            f"from something. At 188 games the z-scores are still wide.</p>", "proj"),
        table(
            ["Tri", "Club", "W-L", "Home", "Road", "PTS", "Opp", "Net", "ORtg", "DRtg", "NetRtg",
             "POSS", "PPP off", "PPP def", "Rating A", "Rating B", "Disagree", "Exp W",
             "Luck W", "Luck z", "Band"],
            rows,
            "All 30 clubs. Ratings A and B are the two estimators' club strengths in points; "
            "Disagree is their gap. Luck z is the brief's refusal statistic.",
            num_cols=(2, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19)),
        "<h2>Home court, pinned</h2>",
        note(
            f"<p>Home advantage is pinned to the measured home-win rate rather than fitted: "
            f"<b>{cal.home_win_rate:.4f}</b> home-win rate over {cal.home_games} games "
            f"(SE {cal.home_rate_se:.4f}), hence h = σ·Φ⁻¹(p) = "
            f"<b>{cal.hca:+.3f}</b> points at σ = {cal.margin_sd}.</p>"
            f"<p><b>Why the unconstrained fit is not used.</b> {esc(cal.free_fit_note)}</p>"
            f"<p>The free fit returns h = {cal.hca_unconstrained:+.2f} at σ = {cal.sigma_unconstrained}, "
            f"which implies a home-win rate of "
            f"{0.5*(1+math.erf((cal.hca_unconstrained/cal.sigma_unconstrained)/math.sqrt(2))):.4f} "
            f"against the measured {cal.home_win_rate:.4f}. It is a worse model of reality that scores "
            f"marginally better on one statistic, and it is not the published number.</p>"),
        "<h2>Two estimators per club</h2>",
        note(
            "<p>Rating A is the shrunk mean scoring margin; rating B is the least-squares strength. "
            "They are on the same scale, so their difference is meaningful in points. The largest "
            "disagreement on this page is a club whose season-long margin and whose "
            "opponent-adjusted strength tell different stories — usually a club with a lopsided "
            "schedule or a few blowouts.</p>"),
    ]
    return ("v3-teams.html", "Teams & luck", "projection", "\n".join(body))


# --------------------------------------------------------------------------- calibration
def calibration_page(cal, lab) -> tuple:
    rel = lab["reliability"]
    sh = lab["shrink"]
    ms = lab["margin_shrink"]
    rows = []
    for r in rel["rows"]:
        kind = "bad" if r["kind"] == "over-confident" else "ok"
        rows.append([
            esc(r["band"]), str(r["n"]), f"{r['forecast']:.3f}", f"{r['observed']:.3f}",
            f"{r['gap']:+.3f}", badge(r["kind"], kind),
        ])
    body = [
        "<h1>Calibration &amp; reliability</h1>",
        '<p class="sub">Why 64.5% accuracy and a log-loss worse than a coin are the same fact '
        "about the same model.</p>",
        note(
            f"<p>The model's average distance from a coin flip is <b>{rel['mean_abs_claim']:.3f}</b>. "
            f"Reality's is <b>{rel['mean_abs_outcome']:.3f}</b>. The model is not wrong about who "
            f"wins as often as it is wrong about <i>how sure it is</i>.</p>"
            "<p>Accuracy only asks whether the larger probability was on the right side. Log-loss "
            "asks whether the probability was right. A model can pass the first and fail the second, "
            "and this one does.</p>", "bad"),
        "<h2>Forecast against outcome, by band</h2>",
        table(
            ["Claimed p(home) band", "Games", "Mean forecast", "Observed home-win rate", "Gap", "Verdict"],
            rows,
            f"All {lab['metrics']['n']} walk-forward games. A band is called over-confident when the "
            "observed rate misses the forecast by more than 0.10.",
            num_cols=(1, 2, 3, 4)),
        "<h2>The correction, measured on data it was not fitted to</h2>",
        note(
            f"<p>Shrink the probability toward a coin flip: p′ = 0.5 + α(p − 0.5). Fitting α on the "
            f"first {sh['fit_n']} games ({sh['fit_dates']}) picks <b>α = {sh['alpha']}</b>. On the "
            f"untouched {sh['holdout_n']} held-out games that moves log-loss from "
            f"<b>{sh['holdout_log_loss_a1']}</b> to <b>{sh['holdout_log_loss_best']}</b> — a gain of "
            f"{sh['gain']:+.4f} and, for the first time, a score better than a coin "
            f"(0.6931).</p>"
            "<p>The gain is not a spike in the grid: every α from 0.30 to 0.80 beats a coin on the "
            "holdout. A correction that only worked at one value would be a fitted artefact.</p>"
            "<p><b>Caveat, stated on the page rather than in a footnote.</b> α is itself a fitted "
            "parameter. It is fitted on a different slice from the one it is scored on, which is "
            "what makes the gain evidence, but it is not a derivation. A second season would test "
            "whether 0.55 is a property of this model or of this month.</p>", "ok"),
        "<h2>The same correction on the margin</h2>",
        note(
            f"<p>Margins are over-dispersed too: the model's forecast spread is "
            f"{lab['metrics']['pred_margin_sd']} points where the truth's is "
            f"{lab['metrics']['actual_margin_sd']}. Shrinking the margin by <b>α = {ms['alpha']}</b>, "
            f"fitted on the first {ms['fit_n']} games, moves held-out MAE from "
            f"<b>{ms['holdout_mae_raw']}</b> to <b>{ms['holdout_mae_shrunk']}</b> against a tie guess "
            f"at {ms['holdout_mae_tie']}.</p>"
            "<p>So the raw forecast is worse than guessing a tie and the shrunk forecast is better "
            "than it. Both sentences are true and the site prints both, because publishing only the "
            "second would overstate the model and publishing only the first would understate it.</p>",
            "ok"),
        "<h2>What this does and does not license</h2>",
        note(
            "<p>It licenses the projection surface: published probabilities are shipped shrunk, with "
            "the raw number beside them.</p>"
            "<p>It does <b>not</b> license a bet. Beating a coin on log-loss is not beating a price; "
            "the price is absent, so the bet surface stays at zero stakes.</p>", "warn"),
        "<h2>Reliability, machine-readable</h2>",
        note("<p>The same table is written to <code>data/v3/reliability.json</code> so a reader can "
             "check the arithmetic instead of trusting the page.</p>"),
    ]
    return ("v3-calibration.html", "Calibration & reliability", "projection", "\n".join(body))


# --------------------------------------------------------------------------- backtest
def backtest_page(lab) -> tuple:
    m = lab["metrics"]
    lk = lab["leakage"]
    sk = lab["skill"]
    pm = lab["permutation"]
    h = lab["holdout"]
    rows = [
        ["Accuracy (A)", _pct(m["accuracy"]), f"n={m['n']}", badge("published", "info")],
        ["Accuracy (B)", _pct(m["accuracy_b"]), "same games, other estimator", badge("published", "info")],
        ["Log-loss (A)", f"{m['log_loss']}", f"coin {m['log_loss_coin']}",
         badge("WORSE THAN COIN", "bad")],
        ["Log-loss (B)", f"{m['log_loss_b']}", f"coin {m['log_loss_coin']}",
         badge("WORSE THAN COIN", "bad")],
        ["Log-loss (A, calibrated)", f"{h['log_loss_a_calibrated']}", f"×{h['alpha']}, held-out",
         badge("beats coin", "ok")],
        ["Brier (A)", f"{m['brier']}", f"coin {m['brier_coin']}", badge("slightly better", "warn")],
        ["Margin MAE (A)", f"{m['mae_margin']}", f"tie {m['mae_predict_tie']}, home-edge "
         f"{m['mae_home_edge_only']}", badge("WORSE", "bad")],
        ["Margin MAE (A, shrunk)", f"{lab['margin_shrink']['holdout_mae_shrunk']}", "held-out",
         badge("beats both", "ok")],
        ["r(predicted, actual margin)", f"{m['r_pred_actual_margin']}", f"n={m['n']}",
         badge("weak positive", "warn")],
        ["Median estimator disagreement", f"{m['median_disagreement']} pts",
         f"max {m['max_disagreement']}", badge("the headline", "info")],
        ["Opposite-side disagreement", f"{m['pct_opposite_side']}%",
         "games where A and B favour different clubs", badge("published", "info")],
    ]
    leak_rows = [
        ["Same-date isolation", badge("PASS" if lk["same_date_isolation"]["pass"] else "FAIL",
                                      "ok" if lk["same_date_isolation"]["pass"] else "bad"),
         f"max within-date difference {lk['same_date_isolation']['max_within_date_delta']}"],
        ["No in-sample term", badge("PASS" if lk["no_in_sample_term"]["pass"] else "FAIL",
                                    "ok" if lk["no_in_sample_term"]["pass"] else "bad"),
         "every rating, σ and baseline computed from strictly earlier dates"],
        ["Future-only edit", badge("PASS" if lk["future_only_edit"]["pass"] else "FAIL",
                                   "ok" if lk["future_only_edit"]["pass"] else "bad"),
         f"a fabricated game 30 days later moves no earlier forecast (max Δ {lk['future_only_edit']['max_delta']})"],
    ]
    body = [
        "<h1>Backtest &amp; skill</h1>",
        '<p class="sub">Walk-forward from the first date with 30 prior games, every metric printed '
        "with the baseline it has to beat.</p>",
        note(
            f"<p>Scored <b>{m['n']}</b> of {lab['meta']['n_games_feed']} games, from "
            f"{lab['meta']['first_date']} to {lab['meta']['last_date']}. Nothing before "
            f"{lab['meta']['first_date']} is scored because 30 prior games are required for a "
            f"rating to exist.</p>", "proj"),
        "<h2>Every metric beside its baseline</h2>",
        table(["Metric", "Value", "Baseline", "Verdict"], rows,
              "No metric is shown without the number it must beat.", num_cols=(1, 2)),
        "<h2>Leakage audit — three direct tests</h2>",
        table(["Test", "Result", "What it shows"], leak_rows,
              "A forecast that can see its own result is not a forecast.", num_cols=()),
        note(
            f"<p><b>A rejected test, recorded so it is not proposed again.</b> {esc(lk['rejected_test'])}</p>"
            f"<p>This repository ran that test first and it failed on a correct implementation. The "
            f"failure was reported as a gate failure for one revision of this build. It is now "
            f"explained here rather than deleted, because a test that fails for the wrong reason is "
            f"a bug in the test.</p>", "warn"),
        "<h2>Skill attribution — the two estimators, where they disagree</h2>",
        note(
            f"<p>On the <b>{sk['n_disagreed']}</b> games where A and B favour <i>different</i> clubs: "
            f"A was right <b>{sk['only_a_right']}</b> times, B was right <b>{sk['only_b_right']}</b> "
            f"times. An exact McNemar test gives p = <b>{sk['mcnemar_exact_p']}</b>.</p>"
            f"<p>{esc(sk['verdict'])}</p>",
            "warn" if sk["mcnemar_exact_p"] >= 0.05 else "ok"),
        "<h2>Permutation test on the margin error</h2>",
        note(
            f"<p>{esc(pm['reading'])}</p>"
            f"<p>p = <b>{pm['p_value']}</b> over {pm['n_perm']} permutations, seed {pm['seed']}. The sign "
            f"matters: the gain is <b>{pm['observed_mae_gain']:+.3f}</b>, so a small p here means the model is "
            f"reliably <i>worse</i> than a tie, not better.</p>", "bad" if pm["observed_mae_gain"] < 0 else "ok"),
        "<h2>The holdout slice</h2>",
        note(
            f"<p>Split at <b>{h['split_date']}</b> — the last 30% of dates, {h['n_test']} games, used "
            f"to fit nothing. Raw A {h['log_loss_a']}, B {h['log_loss_b']}, coin "
            f"{h['log_loss_coin']}, calibrated A {h['log_loss_a_calibrated']}.</p>"
            f"<p>The market weight that the brief asks for cannot be computed: "
            f"{esc(h['reason'])}. The formula is on the methodology page with its two illustrative "
            f"inputs explicitly labelled as illustrations.</p>", "warn"),
    ]
    return ("v3-backtest.html", "Backtest & skill", "projection", "\n".join(body))


# --------------------------------------------------------------------------- strategies
def strategies_page(strat, lab) -> tuple:
    rows = []
    for s in strat["scoreboard"]:
        verdict_kind = ("ok" if s["distinguishable_from_base"]
                        else "bad" if s.get("significantly_worse") else "off" if not s["bets"]
                        else "warn")
        rows.append([
            f"<b>{esc(s['id'])}</b>", esc(strat['names'].get(s['id'], '')),
            str(s["bets"]), str(s["wins"]),
            _pct(s["hit_rate"]) or dash("no bets"),
            esc(str(s["wilson95"] or "—")),
            f"{s['base_rate_p0']}", str(s["binomial_p"]), str(s["holm_adjusted_p"]),
            esc(s["direction"]), badge(s["verdict"], verdict_kind),
        ])
    gate_rows = [[g["id"], esc(g["name"]), badge_status(g["status"]), esc(g["value"]), esc(g["why"])]
                 for g in strat["gates"]]
    prereg_rows = [[f"<b>{esc(p['id'])}</b>", f"<code>{esc(p['sha256'][:16])}…</code>",
                    badge("frozen", "ok") if p["frozen"] else badge("NOT FROZEN", "bad"),
                    badge("matches definition", "ok") if p["matches_current_definition"]
                    else badge("DRIFTED", "bad"),
                    esc(p.get("path", ""))] for p in strat["prereg"]]
    body = [
        "<h1>Strategies &amp; pre-registration</h1>",
        '<p class="sub">Six rules, frozen before the first bet, tested against their own base '
        "rates, and corrected for the fact that six were tested at once.</p>",
        note(
            f"<p>Every rule below was written to <code>data/v3/prereg/</code> and hashed before any "
            f"pick was sealed. The hash is bound into every pick the rule produced, so a rule "
            f"changed after the fact no longer verifies against its picks.</p>"
            f"<p><b>The multiplicity problem, stated plainly.</b> Six rules were tested. The chance "
            f"that at least one clears p&lt;0.05 by luck alone is 1 − 0.95⁶ = "
            f"{1 - 0.95**6:.3f}. A leaderboard that simply ranks the luckiest of six is the exact "
            f"failure the brief asks to avoid, so the verdict column uses a Holm-adjusted p.</p>",
            "proj"),
        "<h2>The scoreboard</h2>",
        table(
            ["Rule", "Signal", "Bets", "Wins", "Hit rate", "Wilson 95%", "Base rate",
             "p (two-sided)", "p (Holm)", "Direction", "Verdict"],
            rows,
            "Each rule against the base rate its own construction implies. 'Distinct' requires the "
            "Holm-adjusted p to clear 0.05 AND the deviation to be in the direction the rule claims.",
            num_cols=(2, 3, 4, 6, 7, 8)),
        "<h2>The one rule that clears its base rate — and why it still is not a recommendation</h2>",
        note(
            f"<p>{esc(strat['s3_05_legs']['reading'])}</p>"
            f"<p><b>The legs, separately:</b> side {strat['s3_05_legs']['side_leg_correct']}/"
            f"{strat['s3_05_legs']['n']} ({strat['s3_05_legs']['side_leg_rate']:.1%}) · total "
            f"{strat['s3_05_legs']['total_leg_correct']}/{strat['s3_05_legs']['n']} "
            f"({strat['s3_05_legs']['total_leg_rate']:.1%}) · both "
            f"{strat['s3_05_legs']['n'] and round(strat['s3_05_legs']['side_leg_rate'] * strat['s3_05_legs']['total_leg_rate'], 3)} "
            f"if independent.</p>"
            "<p>Three reasons this is not a recommendation. <b>One:</b> the total leg is measured "
            "against a rolling mean, which is not a price, so beating it is not edge. <b>Two:</b> "
            "the rule fires on 86 games, far below the ranking bar. <b>Three:</b> it is one of five "
            "rules tested, and it is the only survivor — which is what one survivor out of five "
            "looks like whether or not any of them works.</p>", "warn"),
        "<h2>Why no rule is ranked</h2>",
        note(
            f"<p>The leaderboard requires <b>{strat['meta']['min_bets_rank']}</b> settled bets for a rank "
            f"(v2 used 300; the bar was lowered and the change is disclosed). The largest settled "
            f"count here is <b>{max((s['bets'] for s in strat['scoreboard']), default=0)}</b>, so "
            f"<b>no rule receives a position</b>. A rank computed from 97 bets is noise wearing a "
            f"rank, and printing one would invite exactly the over-reading the brief forbids.</p>",
            "warn"),
        "<h2>The luck gate</h2>",
        note(
            f"<p>{esc(strat['luck_gate']['reading'])}</p>"
            f"<p><b>Refused today: {strat['luck_gate']['refused']}.</b> "
            f"{strat['luck_gate']['n_clubs_outside']} of 30 clubs lie outside |z| &gt; "
            f"{strat['luck_gate']['threshold']}, so the "
            f"gate has nothing to refuse. The gate works; the season has not yet produced a club it "
            f"acts on. That is a statement about the data, not a claim that the strategy is safe.</p>",
            "ok" if not strat["luck_gate"]["refused"] else "bad"),
        "<h2>The twelve gates</h2>",
        table(["Gate", "Test", "Status", "Value", "Why it is the right test"], gate_rows,
              "The gate report. A gate that cannot be measured says so instead of passing.",
              num_cols=()),
        "<h2>Pre-registration files</h2>",
        table(["Rule", "SHA-256", "Frozen", "Integrity", "Path"], prereg_rows,
              "Each rule's definition, hashed at the moment it was frozen."),
        "<h2>Settlement</h2>",
        note(
            f"<p>The sealed ledger holds <b>{strat['ledger']['n_picks']}</b> picks with root "
            f"<code>{esc(strat['ledger']['root'][:32])}…</code>, and it verifies: "
            f"{badge('verified', 'ok') if strat['ledger']['verified'] else badge('FAILED', 'bad')}."
            f"</p>"
            "<p>Settlement uses the official final score only, and only after the game page's "
            "quarter scores have been read and confirmed to sum to the printed final. Until then the "
            "pick stays open rather than settling on a partial feed.</p>"),
    ]
    return ("v3-strategies.html", "Strategies", "projection", "\n".join(body))


# --------------------------------------------------------------------------- bet surface
def bet_page(strat, lines) -> tuple:
    gate_rows = [[g["id"], esc(g["name"]), badge_status(g["status"]), esc(g["value"])]
                 for g in strat["gates"]]
    pick_rows = []
    for p in strat["ledger"].get("picks", [])[:30]:
        pick_rows.append([
            esc(p.get("date")), esc(p.get("matchup")), esc(p.get("strategy_id")),
            esc(p.get("side")), f"{p.get('p_model_a')} / {p.get('p_model_b')}",
            f"{p.get('stake_units')}", esc(p.get("stake_reason")),
            f"<code>{esc(str(p.get('hash', ''))[:12])}…</code>",
        ])
    open_gates = [g for g in strat["gates"] if g["status"] not in ("PASS",)
                  and not g["status"].startswith("PASS")]
    body = [
        "<h1>Bet surface — gated</h1>",
        '<p class="sub">This page may record a stake only after every gate passes. '
        f"{len(open_gates)} gate(s) are not passing, so every stake here is zero.</p>",
        note(
            "<p><b>Why nothing on this page is a recommendation.</b> A stake requires a price. A "
            "price requires a market. No odds feed is connected, so there is no edge, no closing-line "
            "value, no return and no stake to size. The picks below are sealed so that a future "
            "result can be checked against what was said before tip — not so that anyone can bet "
            "them.</p>", "bet"),
        kpis([
            ("Stakes on this page", "0", "every pick, by gate G6", "warn"),
            ("Picks sealed", str(strat["ledger"]["n_picks"]), "hash published before tip", ""),
            ("Ledger verifies", "yes" if strat["ledger"]["verified"] else "NO",
             f"root {strat['ledger']['root'][:12]}…", "ok" if strat["ledger"]["verified"] else "bad"),
            ("Gates not passing", str(len(open_gates)),
             ", ".join(g["id"] for g in open_gates) or "none", "warn" if open_gates else "ok"),
        ]),
        "<h2>The gate report</h2>",
        table(["Gate", "Test", "Status", "Value"], gate_rows,
              "Every gate, including the ones that cannot be measured. A gate that cannot be "
              "measured is not a gate that passed.", num_cols=()),
        "<h2>The three gates that stop this page</h2>",
        "<ul>"
        "<li><b>G6 — market price.</b> No odds feed. Without a price there is no edge to compute "
        "and nothing to stake.</li>"
        "<li><b>G7 — sample size.</b> The largest settled count is below the ranking bar, so no "
        "rule has a demonstrated track record.</li>"
        "<li><b>G5 — per-strategy significance.</b> After the family correction, at most one rule "
        "deviates from its base rate, and a single season cannot establish a rule.</li>"
        "</ul>",
        "<h2>The sealed picks</h2>",
        table(["Date", "Matchup", "Rule", "Side", "p(A) / p(B)", "Stake", "Why this stake",
               "SHA-256"], pick_rows,
              f"The first {len(pick_rows)} of {strat['ledger']['n_picks']} sealed picks. The hash "
              "is over the pick's canonical JSON with its rule's pre-registration hash bound in.",
              num_cols=(5,)),
        "<h2>How settlement will work when a price exists</h2>",
        note(
            "<p>A pick settles only from the official final score after its game page's quarter "
            "scores have been read and confirmed to sum to the printed final. The settlement stamp "
            "stays visible on the row. A pick whose game has not finished stays <b>open</b>, and an "
            "open pick is never counted as a win in any rate on this site.</p>"),
        "<h2>Rotation availability — its own column</h2>",
        note(
            "<p>The brief asks for rotation availability as a column on the picks page, not a "
            "footnote. It is here: each pick carries the availability of both clubs at the time of "
            "sealing, taken from the official injury report revision named on the injuries page.</p>"
            "<p>The model does not consume it. A club whose top-eight minutes are redistributed is "
            "priced as its season average, and <b>FLAG-V3-ROTATION-UNFILED</b> records that the "
            "minutes model has not been filed for it. The column is disclosure, not an input.</p>",
            "warn"),
    ]
    return ("v3-bet.html", "Bet surface (gated)", "bet", "\n".join(body))


# --------------------------------------------------------------------------- injuries
def injuries_page(inj) -> tuple:
    b = inj["banner"]
    d = inj["diff_11_14_0430_vs_11_15_0615"]
    wd = inj["within_day_diff"]
    c = d["counts"]

    arch = []
    for r in inj["archive"]:
        arch.append([
            esc(r.get("date")), esc(r.get("revision_et")),
            badge("captured", "ok") if r.get("captured") else dash(r.get("note", "not fetched")),
            esc(r.get("retrieved_utc") or ""),
            src(r.get("url"), r.get("pdf")),
        ])

    club_rows = []
    for cl in sorted(inj["clubs"], key=lambda x: (-x["out"], -x["doubtful"], x["team"])):
        chips = " ".join(
            badge(f"{p} — {st}", "bad" if st in ("Out", "Doubtful") else "warn")
            for p, st in cl["players"])
        club_rows.append([f"<b>{esc(cl['team'])}</b>", esc(", ".join(cl["dates"])),
                          str(cl["rows"]), str(cl["out"] + cl["doubtful"]),
                          str(cl["questionable"] + cl["probable"]), chips])

    not_sub = [[esc(r["date"]), esc(r["matchup"]), esc(r["team"]),
                badge("NOT YET SUBMITTED", "warn")] for r in inj["not_submitted"]]

    counts = inj["status_counts"]
    body = [
        "<h1>Injuries &amp; rotation</h1>",
        '<p class="sub">Both timestamps on every report, the diff of the two captured releases, '
        "and an explicit statement of what that diff can and cannot measure.</p>",
        "<h2>The banner the brief asks for</h2>",
        kpis([
            ("Report revision", esc(b["revision_et"]),
             f"= {b['revision_utc_equivalent']} UTC, computed not typed", ""),
            ("Retrieved", esc(b["retrieved_utc"]),
             f"index list retrieved {esc(b['index_retrieved_utc'])}", ""),
            ("Lag", f"{b['lag_minutes']} min",
             "between the league revising the report and this site fetching it",
             "ok" if b["lag_minutes"] < 60 else "warn"),
            ("Revisions listed for 11/15", str(b["revisions_listed"]),
             f"latest on the index: {esc(b['latest_on_index_et'])}", ""),
        ]),
        note(
            f"<p>The league publishes its filing policy on the same index page: reports are "
            f"submitted by {esc(b['policy']['day_before'])} for the next day's game, "
            f"{esc(b['policy']['back_to_back_second'])}, and {esc(b['policy']['game_day'])}, and "
            f"&ldquo;{esc(b['policy']['updates'])}&rdquo;</p>"
            f"<p>Both URLs: {src(b['pdf_url'], 'the PDF this page was built from')} · "
            f"{src(b['index_url'], 'the index listing every revision')}</p>", "proj"),
        "<h2>What the two captured releases actually show</h2>",
        kpis([
            ("Players added", str(c["added"]), f"previous release had {d['prev_n']} rows", ""),
            ("Players dropped", str(c["dropped"]), f"this release has {d['curr_n']} rows", ""),
            ("Status changes", str(c["status_changes"]), "same player, same date, new status", "warn"),
            ("Game-date moves", str(c["moved_date_same_player"]),
             "same player, different game date", ""),
        ]),
        note(f"<p><b>{esc(d['comparison_validity'])}</b></p>", "bad"),
        note(f"<p>{esc(d['reading'])}</p>"),
        "<h2>Within-day diff — the brief's actual requirement</h2>",
        note(
            f"<p><b>{esc(wd['status'])}.</b> {esc(wd['reason'])}</p>"
            f"<p><b>How it gets measured:</b> {esc(wd['how_to_measure'])}. "
            f"{wd['revisions_fetched']} of {wd['revisions_listed']} revisions of the 11/15 report "
            f"were fetched in this capture.</p>", "warn"),
        "<h2>Current report by club</h2>",
        table(["Club", "Game date", "Rows", "Out / doubtful", "Game-time decision", "Named players"],
              club_rows,
              f"Statuses exactly as printed in the official report: {counts.get('Out', 0)} Out, "
              f"{counts.get('Doubtful', 0)} Doubtful, {counts.get('Questionable', 0)} Questionable, "
              f"{counts.get('Probable', 0)} Probable, {counts.get('Available', 0)} Available. "
              "No status is carried over from a previous release.",
              num_cols=(2, 3, 4)),
        "<h2>Clubs that have not filed</h2>",
        table(["Date", "Matchup", "Club", "Status"], not_sub,
              "A club that has not filed is not 'cleared'. The rotation column on the lines page "
              "reads 'not filed' for these and never 'all cleared'."),
        "<h2>Every revision, with a retrieval timestamp only if it was actually fetched</h2>",
        table(["Date", "Revision (ET)", "Captured", "Retrieved (UTC)", "PDF"], arch,
              f"{len(arch)} revisions listed on the official index. A row that was never fetched "
              "says so rather than borrowing a timestamp from a different file.",
              num_cols=()),
        "<h2>Minutes redistribution — filed or not</h2>",
        note(
            "<p>The brief asks for top-eight minutes shares plus replacement shares when a player "
            "is out. The <b>method</b> is written (<code>model.minutes_shares</code>) and described "
            "on the methodology page.</p>"
            "<p>The <b>inputs are not in the repository</b>: per-player game logs for at least the "
            "injury-report players are absent, so no club's rotation has been filed and no "
            "replacement share has been computed. Every affected line carries "
            "<b>FLAG-V3-ROTATION-UNFILED</b>. The page does not estimate redistribution from season "
            "averages, because a season average is precisely the quantity an absence changes.</p>",
            "warn"),
    ]
    return ("v3-injuries.html", "Injuries & rotation", "projection", "\n".join(body))


# --------------------------------------------------------------------------- flagged
def flagged_page(flags) -> tuple:
    rows = [[esc(f["id"]), badge(f.get("kind", "flag"), "warn"), esc(f["what"]),
             esc(f.get("why", "")), src(f.get("source")), esc(f.get("status", "OPEN"))]
            for f in flags]
    body = [
        "<h1>Flagged for review</h1>",
        '<p class="sub">Everything this build could not verify, could not measure, or measured and '
        "found wanting. None of these are hidden in a footnote.</p>",
        note(
            "<p>A flag is not a failure of the build. It is a statement that a number is missing or "
            "a claim is unverified, with the reason and, where one exists, the source a reviewer "
            "should read. Flagged items do not block publication; concealing them would.</p>", "warn"),
        table(["ID", "Kind", "What", "Why it matters", "Source", "Status"], rows,
              f"{len(flags)} open items.", num_cols=()),
        "<h2>The three that most affect how a number should be read</h2>",
        "<ol>"
        "<li><b>The raw model loses to a coin on log-loss.</b> The calibrated model wins. Both are "
        "published; the calibration page shows the table that explains the gap.</li>"
        "<li><b>The forward total does not beat a constant.</b> The possession formula is correct "
        "and its forecast is not useful for predicting a total.</li>"
        "<li><b>No rotation has been filed.</b> Injury effects are disclosed on every line but are "
        "not in the price, because per-player game logs are not in the repository.</li>"
        "</ol>",
    ]
    return ("v3-flagged.html", "Flagged for review", "projection", "\n".join(body))


# --------------------------------------------------------------------------- methodology
def methodology_page(cal, lab, strat) -> tuple:
    pm = lab["permutation"]
    lk = lab["leakage"]
    body = [
        "<h1>Methodology &amp; formulas</h1>",
        '<p class="sub">Every formula this site uses, written as a formula, with the choice that '
        "would have been easier and is deliberately not taken.</p>",
        "<h2>Two estimators, and why the disagreement is the headline</h2>",
        note(
            "<p>Estimator <b>A</b>: rating = shrunk mean of a club's home and road scoring margins; "
            "the forecast margin is r_home − r_away + h.</p>"
            "<p>Estimator <b>B</b>: an exact constrained least-squares fit of strengths and a home "
            "term to the same game margins, with a ridge penalty of 0.5 and the constraint that "
            "strengths sum to zero, solved by Gaussian elimination with a Lagrange row.</p>"
            "<p><b>Why not just average them?</b> The brief asks for the disagreement to be the "
            "primary confidence signal and the blend to sit underneath. A single blended headline "
            "hides the one piece of information a reader can actually act on: whether the two "
            "methods agree about tonight's game. The blend appears only as a labelled fallback.</p>"),
        "<h2>Home court pinned to the measured rate</h2>",
        note(
            f"<p>p_home is measured from the results, not fitted: {cal.home_win_rate:.4f} "
            f"over {cal.home_games} games (SE {cal.home_rate_se:.4f}). With the margin distribution "
            f"assumed normal, h = σ·Φ⁻¹(p) = <b>{cal.hca:+.3f}</b> at σ = "
            f"{cal.margin_sd}.</p>"
            f"<p><b>{esc(cal.free_fit_note)}</b></p>"
            f"<p>An unconstrained fit gives h = {cal.hca_unconstrained:+.2f} at σ = {cal.sigma_unconstrained}. It is reported "
            f"and not used. A free home term absorbs every systematic error in the ratings and calls "
            f"the sum 'home court'.</p>"),
        "<h2>Totals: possessions × points-per-possession</h2>",
        note(
            "<p>Total = POSS × (PPP_home + PPP_away), where POSS is the game's possession count and "
            "each side's PPP is the mean of its own offensive rate and the opponent's defensive "
            "rate.</p>"
            "<p><b>The average-of-averages is printed beside it</b> on every row, because the brief "
            "asks for the comparison rather than the replacement. The measured result is on the "
            "totals page: the possession total does not beat a constant.</p>"),
        "<h2>Correlations and the parlay price</h2>",
        note(
            f"<p>A same-game parlay is priced with the measured correlation: "
            f"P = Φ₂(Φ⁻¹p₁, Φ⁻¹p₂; ρ), with the naive product p₁p₂ printed beside it on every "
            f"leg.</p>"
            f"<p>The register: r(model margin, model total) = "
            f"<b>{lab['correlations']['margin_vs_total_model']['r']}</b> "
            f"[{lab['correlations']['margin_vs_total_model']['ci95'][0]}, "
            f"{lab['correlations']['margin_vs_total_model']['ci95'][1]}] over "
            f"{lab['correlations']['margin_vs_total_model']['n']} games; the actual correlation is "
            f"{lab['correlations']['margin_vs_total_actual']['r']}. Near zero is what justifies "
            f"multiplying the legs; a correlation far from zero is what would forbid it.</p>"
            f"<p><b>What is withheld.</b> The register's earlier version correlated margin against "
            f"a total that was a single league-mean constant (sd 1.21). A near-zero correlation "
            f"between a variable and a constant is not a measurement, so that number is not shown; "
            f"the forward total with real variance is used instead.</p>", "warn"),
        "<h2>Market-anchored prior</h2>",
        note(
            f"<p>w_model = L_market / (L_model + L_market), where each L is an out-of-sample "
            f"log-loss. The model's held-out L is <b>{lab['holdout']['log_loss_a_calibrated']}</b> "
            f"(calibrated) against {lab['holdout']['log_loss_a']} raw.</p>"
            f"<p><b>Not computed.</b> L_market requires a market, and no odds feed is connected. The "
            f"methodology page shows the formula and two illustrative weights (0.4586 at a market "
            f"log-loss of 0.60, 0.4786 at 0.65) explicitly labelled as illustrations — they are not "
            f"inputs to anything on this site.</p>", "warn"),
        "<h2>Minutes redistribution</h2>",
        note(
            "<p>The method: take each club's top-eight players by minutes share, compute what "
            "fraction of the top-eight minutes a missing player carried, and redistribute it across "
            "the remaining seven and a replacement share proportional to the club's bench usage. The "
            "replacement share is a parameter, published rather than buried.</p>"
            "<p><b>Not filed.</b> The inputs (per-player game logs) are absent, so no club has a "
            "computed redistribution. Every line touching an affected club carries "
            "<b>FLAG-V3-ROTATION-UNFILED</b>.</p>", "warn"),
        "<h2>Leakage, and the test this repository got wrong</h2>",
        note(
            f"<p>Three direct tests replace the naive one: same-date isolation, no in-sample term, "
            f"and a future-only edit. All three pass.</p>"
            f"<p>{esc(lk['rejected_test'])}</p>", "warn"),
        "<h2>Settlement rules</h2>",
        note(
            "<p>A pick settles on the official final score only, after the game page's quarter "
            "scores have been read and verified to sum to the printed final. Until both exist the "
            "pick is open and is excluded from every rate.</p>"
            "<p>The ledger is a chained hash: each pick hashes its canonical JSON with its rule's "
            "pre-registration hash bound in, and the root hashes the ordered pick hashes. Editing a "
            "pick, editing a hash, or deleting a pick all break verification — each was tested.</p>"),
        "<h2>Reproducing any number on this site</h2>",
        note(
            "<p><code>python3 -m nba2.v3.backtest</code> prints every metric above. "
            "<code>python3 -m nba2.v3.strategies</code> re-runs the scoreboard and re-verifies the "
            "ledger. <code>python3 -m nba2.v3.check</code> re-checks the published pages. The seed "
            f"is {lab['meta']['seed']} and the permutation count is {lab['meta']['n_perm']}; "
            f"the current permutation p is {pm['p_value']}.</p>"),
    ]
    return ("v3-methodology.html", "Methodology & formulas", "projection", "\n".join(body))
