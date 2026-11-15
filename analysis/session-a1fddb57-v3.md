# v3 — session `arena/a1fddb57-nba2`

**Date:** 2026-11-15 · **Branch:** `arena/a1fddb57-nba2` · **Base:** `fc88652`
**Live:** https://wingbangboozle1-lang.github.io/NBA2/v3-index.html

This is the session write-up for the v3 surface. It is written as a **decision log**, not a
victory lap: the useful part of a model build is which choices were made, which were reversed, and
which numbers came out worse than the thing they replaced.

---

## 1. What was asked, and what shape the answer took

The brief asks for two independent estimators with their **disagreement** as the primary confidence
signal, home-court advantage **pinned** to the measured home-win rate, luck reported as a z-score
with a refusal gate, parlay pricing with a measured ρ and the naive product beside it, totals from
**possessions × points-per-possession**, pre-registration and a tamper-evident ledger, and a site
split into a **projection** surface and a **gated bet** surface that never mix.

All of that is implemented except where an input is missing, and the missing inputs are named in
`requirements/V3_REQUIREMENTS.json` (18 rows: 11 met, 5 partial, 2 blocked) and on the
"Flagged for review" page (14 flags). Neither document is prose: each row names a file to read and
a command to run.

The one deliberate departure from a "finished product" is that **two of the published numbers are
negative results about this model**:

- raw out-of-sample log-loss **0.7082** is worse than a coin (**0.6931**);
- raw margin error **14.108** is worse than guessing a tie (**13.75**).

They are on the front page, in the executive block, next to the fix that beats both. Publishing only
the 64.5% accuracy would have been true and misleading, which is the failure mode this project
exists to avoid.

---

## 2. Results

| Metric | Value | Baseline it must beat | Verdict |
|---|---|---|---|
| Walk-forward accuracy (A) | 0.6447 | 0.50 | n=152, CI [0.5659, 0.7164] |
| Accuracy (B) | 0.6908 | 0.50 | the two estimators are **not** separable (McNemar p=0.167) |
| Log-loss (A) | 0.7414 full / **0.7082** holdout | 0.6931 | **fail** |
| Log-loss (A), shrunk ×0.55 | **0.6398** holdout | 0.6931 | **beats** |
| Margin MAE (A) | 14.108 | 13.75 (tie) / 13.658 (mean) | **fail** |
| Margin MAE, shrunk ×0.45 | **13.51** holdout | 13.75 | **beats** |
| Total MAE (forward) | 16.05 | 15.13 (constant) | **fail** |
| Total direction vs rolling mean | 0.576, p=0.082 | 0.50 | promising, **not significant** |
| Median estimator disagreement | 3.73 pts | — | the published confidence signal |
| Opposite-side disagreement | 12.5% of games | — | where the two methods genuinely split |
| ρ(margin, total) | −0.078 [−0.234, 0.082] | 0 | justifies multiplying parlay legs |
| Clubs outside the luck band | 0 of 30 | |z| > 1.96 | the refusal gate refuses nothing today |

Calibration: σ **13.05**, h **+0.963**, pinned to a measured home rate of **0.5294** over 187 games
(SE 0.0366). League PPP **1.1310**. Scoreboard: 22 originated lines (7 graded A, 15 B, 0 C).

---

## 3. The decision log

### 3.1 Pinning home advantage — and the test that caught the wrong formula

`h = σ(2p−1)` is the **tangent line at p = 0.5**. It is exact there and drifts everywhere else. At
the measured p = 0.5294 it produced h = 0.768, which fed through Φ returns **0.5234** — the model
was not reproducing the rate it claimed to be pinned to.

`TestEstimators.test_pinned_hca_reproduces_the_measured_home_rate` failed on that, and the fix is
`h = σ·Φ⁻¹(p)`, which reproduces the rate exactly. Two consequences:

- h moved **0.768 → 0.963**;
- the inverse normal CDF was consolidated into `model.inv_phi` (it had a second, private
  bisection implementation in `strategies.py`, which is how two published numbers end up
  disagreeing about the same probability).

**Why pin at all**, stated with the numbers rather than the principle: the free fit returns
h = **8.38** at σ = **8.74**, implying a home-win rate of **83.1%**. It wins an RMSE of
**0.0021**. A model that claims four out of five home teams win, to gain two thousandths of a
win, has spent its freedom on the wrong thing — and that sentence is now printed on the page.

### 3.2 The total estimator was measuring nothing

The first `correlation_register` correlated the model's margin against `total_a`, which is a single
league-mean constant carried on every prediction (**sd 1.21**). A correlation between a variable and
a constant is not a measurement, and it was being published as ρ = −0.0034.

Fixed by building `total_fwd` from **prior-window club rates and pace** (sd 12.49), giving
ρ = **−0.078 [−0.234, 0.082]**. The near-zero result survives, but now it is a result.

This also uncovered a second defect: **S3-05 fired zero bets** because it compared the model total
to that same constant, so the gap was identically zero. Rebuilt against a rolling mean, it fires 86
times.

### 3.3 The leakage audit failed on a correct implementation

The inherited test was: *delete the target game, re-run, and the forecast must be byte-identical.*
It fails on any correct implementation, because deleting a game removes it from **every later
date's** volatility estimate too — the counterfactual differs for reasons that have nothing to do
with leakage. It was reported as gate **G2 FAIL** for one revision of this build.

Replaced with three tests that isolate the property:

1. **Same-date isolation** — two games on one date must be predicted from identical ratings
   (max within-date delta 0.0);
2. **No in-sample term** — every rating, σ and baseline comes from strictly earlier dates;
3. **Future-only edit** — appending a fabricated game 30 days later changes no earlier forecast
   (max delta 0.0).

All three pass. The **rejected** test is recorded in `leakage_audit()["rejected_test"]` and on the
backtest page so it is not reintroduced — a test that fails for the wrong reason is a bug in the
test.

### 3.4 Multiplicity, direction, and the rule that looked like a winner

Two statistics bugs were found by trying to state a conclusion the numbers did not support:

- **One-sided p, upward only.** 35/86 against a 0.25 base rate produced p = 0.001 and was labelled
  "distinguishable" — true, but the reader would take it for skill. Now **two-sided**, with a
  **direction** column, and a **Holm** correction across the family of six rules (the chance one
  clears p < 0.05 by luck alone is 1 − 0.95⁶ = **26.5%**).
- **Significance without direction.** A rule that is reliably *worse* is a finding, not a
  candidate. `distinguishable_from_base` now requires both, and `significantly_worse` is its own
  published field.

After the correction, **one of six** rules clears its base rate (S3-05, p_holm = 0.010) and the site
prints three reasons it is still not a recommendation: its total leg is measured against a rolling
mean rather than a price; 86 games is far below the 100-bet ranking bar; and one survivor out of six
is what one survivor out of six looks like whether or not any of them works.

### 3.5 Two silent-contradiction defects

- **Injury banner.** It carried a typed `"10:15Z"` beside a *computed* 29-minute lag. Both numbers
  were on the same screen and contradicted each other by five hours. The UTC equivalent is now
  derived, and `check_banner_arithmetic()` fails the build if the two ever drift.
- **Prose asserting a conclusion its own arithmetic contradicted.** A `total_direction` reading
  hard-coded "also not significant" and printed immediately above `p = 0.020`. The reading is now
  composed by a function from the p-values it reports.

### 3.6 The checker was checked

`nba2/v3/check.py` was not trusted until seven failure classes were injected and each was caught:
broken internal link, template artifact, missing table caption, ledger tamper, phantom stake, banner
arithmetic, and a flag missing from the flagged page. The first version of the artifact check
produced **seven false positives** on a clean build (matching "inf" inside "information", "None"
inside "None of these are hidden"), which is how a checker teaches its reader to ignore it — every
pattern is now delimiter-anchored.

The **v2 whole-site checker initially reported 226 problems** on the new pages, all of them the
repo's oldest rule: *every table row must carry a source URL*. That rule is right, so v3 meets it —
each page adds a source column — and **0 problems** remain. Every v3 page now carries a source on
every data row and a reason in every blank.

---

## 4. What is blocked, and what would unblock it

| Blocked input | What it stops | What would fix it |
|---|---|---|
| **Odds / closing line** | the market-anchored prior (G6), any stake, ROI, CLV | any odds feed; `market_prior()` and `log_loss_weights()` are written and waiting |
| **Per-player game logs** | minutes redistribution, top-8 shares, replacement shares | player box scores for the injury-report players; `minutes_shares()` is written |
| **Inter-day injury revisions** | the within-day status diff | fetch the remaining 25 of 26 revisions at their own times; `archive()` already lists them |
| **Per-game possession/shooting** | a total forecast with real variance | play-by-play or per-game team stats |

The two captured injury releases (11/14 04:30 and 11/15 06:15) share **zero** (team, player) pairs.
That is not a naming mismatch — it is two different slates. So the diff of 84 added / 26 dropped / 0
status changes measures **slate turnover**, and calling the zero a finding would be wrong. Both the
zero and its explanation are on the page.

---

## 5. Files

| Path | What it holds |
|---|---|
| `nba2/v3/official.py` | transcribed official captures with provenance; **do not re-fetch** |
| `nba2/v3/model.py` | published arithmetic: `phi`/`phi2`/`inv_phi`, calibration, estimators, totals, travel, minutes |
| `nba2/v3/backtest.py` | walk-forward, three-test leakage audit, reliability, shrink, register |
| `nba2/v3/strategies.py` | six pre-registered rules, gates G1–G12, ledger, parlay price |
| `nba2/v3/injuries.py` | archive, banner, diff, per-club summary |
| `nba2/v3/build.py` | assembly, surface enforcement, `build_pages()` |
| `nba2/v3/render.py`, `pages.py` | primitives and the eleven page bodies |
| `nba2/v3/check.py` | structural + semantic verification |
| `nba2/v3/test_v3.py` | 50 tests; each names the defect it exists to prevent |
| `requirements/V3_REQUIREMENTS.json` | 18 requirements with evidence and a check command |
| `.github/workflows/v3-verify.yml` | capture identities → tests → build → checks → ledger → surface |

---

## 6. Honest limitations

1. **n = 152 scored games, 42 held out.** Every interval on the site is wide, and the site says so
   at each one rather than once at the bottom.
2. **α is a fitted parameter.** The shrink factor is fitted on one slice and scored on another,
   which makes the gain evidence rather than a derivation. A second season would test whether 0.55
   is a property of this model or of this month.
3. **The model is availability-blind.** It prices the season-average club. Injuries are disclosed in
   a column on every line and are not in the price, because the minutes model has no inputs.
4. **One season of history.** σ and h are identified loosely against a partial season, and the free
   fit's 83% home rate is a demonstration of that looseness, not a curiosity.
5. **No page has been visually reviewed in a browser by this session.** Rendering was verified
   structurally (every page serves, every link resolves, no artifact tokens, correct cell counts),
   not by eye.
