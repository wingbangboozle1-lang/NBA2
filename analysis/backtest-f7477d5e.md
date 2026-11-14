# Measured skill: what 155 official finals say about the originated lines

**Session** `arena/f7477d5e-nba2` · **Generated** 2026-11-14 · **Sample** 2026-10-20 → 2026-11-12
**Machine-readable output** `backtest/data/report.json` · **Human report** `backtest/index.html`
**Checks** `python3 tools/verify_backtest.py` (12 pages, 155 sourced rows, 190 links) · `python3 -m unittest discover -s backtest/tests -t .` (46 tests)

Every number below is reproducible from `data/raw/history/*.json` by running
`python3 -m backtest.engine.build`. Nothing here is estimated, back-filled, or typed by hand.

---

## 1. Why this work exists

Before this session, the platform could publish lines but could not grade them: there was no
game-level history of official final scores. Every claim of skill in the repository was therefore
untestable, and the validation gates were all `BLOCKED` for want of evidence — an honest but
useless state.

This session captured **155 official final scores** with a per-game source URL, rebuilt the
originated pricing logic point-in-time, and graded it. The result is uncomfortable and is reported
as such.

---

## 2. The sample, and exactly what is missing

| | Count | Source |
|---|---|---|
| Games captured | **155** | one `https://www.nba.com/game/<slug>-<gameid>` per row |
| Dates covered | **21** | `nba.com/games?date=…` per day |
| Graded (≥1 prior game for both teams) | **139** | derived |
| Blocked at pricing time | **16** | opening-night / first-game teams, §4 |
| **Permanently uncapturable** | **19** | 2026-11-06 (9) and 2026-11-11 (10) |

**FLAG-BT-01 — the 19-game hole.** On the reachable official surfaces, the game cards for
2026-11-06 (a nine-game Emirates NBA Cup night) and 2026-11-11 render every score element as
`-`. The per-game route `nba.com/game/<slug>-<id>` returns the *schedule* view rather than a box
score for those dates; the static JSON endpoints return HTTP 500. These 19 games are **excluded, not
guessed**. Published on `backtest/pages/flagged-review.html`.

### Three independent integrity checks

The point of these is to catch a transcription error before it becomes a finding — the failure mode
that has bitten earlier sessions.

| # | Check | Result |
|---|---|---|
| 1 | Rebuild team W-L from final scores only, compare to the official post-game card | **70 / 70 exact**, every card on or before 2026-11-05 |
| 2 | Same, for cards after the missing dates — reconstruction must never *exceed* the official card | **64 / 64 consistent**, **0 violations** |
| 3 | Reconstruction vs the independent `data/standings-2026-11-13.csv` | **0 / 30 exceed**; every shortfall equals the 19-game hole |

Check 3 is worth stating plainly: it is the first mechanical corroboration of the standings snapshot
by a second method. Earlier sessions could only flag a documentation conflict over 28/30 vs 30/30
(now `A-05` in `analysis/audit-2c07c00b.md`); the underlying data reconciles perfectly once the 19
known-missing games are accounted for.

**A real error was found and fixed.** Game `0022600159` was first keyed `DAL@CHA`; the official
slug is `det-vs-cha-…`. Corrected in the snapshot with an explicit `correction` field. That
correction is what moved check 1 from 28/38 to 70/70 — the earlier "W-L mismatch" was my
transcription, never the source.

---

## 3. Method

- **Point-in-time replay.** `walk_forward()` walks dates in order. A game is priced using only
  games completed strictly before that date. `assert_no_leakage()` re-derives each team's pre-game
  game count from raw history on **every build** and raises rather than warns.
- **Same model as production.** Shrinkage `K = 12` toward the league mean, home-court advantage
  estimated from completed home margins only (`min_games = 40`), `sigma` from realised margins.
  Tiers are the production A/B/C thresholds.
- **Statistics, not vibes.** Wilson intervals (never a perfect 100% CI on a small sample),
  seeded permutation tests (10k draws, seed `20261114`, deterministic — asserted in the test suite),
  Brier score, AUROC with tie handling, and a power table so a null result can be read as
  "not yet knowable" rather than "disproven".
- **No market claims.** The report contains no ROI, no profit, and no vig-adjusted return. There is
  no captured closing-line history for this window, so any such figure would be invented.

---

## 4. Results

### 4.1 Margin: better than a constant, but not significantly

| Metric | Model | Baseline (always 0) | Verdict |
|---|---|---|---|
| MAE | **12.17** | 13.27 | model better by 1.09 pts |
| RMSE | 15.40 | 16.47 | model better |
| Bias | −0.62 | — | small, well within noise |

Paired permutation test on the absolute-error difference: **p = 0.35**. The model is better on this
sample but cannot be distinguished from the trivial line at any conventional threshold.

An earlier build reported a −1.7 pt home bias. That was a bug, not a finding: `estimate_hca` was
returning 0.0 by construction, manufacturing the bias. It now estimates HCA from completed home
margins, and the bias fell to −0.62.

### 4.2 Totals: the model loses to a constant

| Metric | Model | League-mean constant |
|---|---|---|
| MAE | 15.78 | **15.43** |
| RMSE | 20.34 | — |

**This is the clearest negative result in the report.** A one-number total (the league average) beats
the originated total on mean absolute error. The total line in its current form adds error, not
information. It should be published as `BLOCKED`, or replaced, before it is used.

### 4.3 Winner: 62.6%, but a one-line rule does as well

| Strategy | Hit rate | 95% CI |
|---|---|---|
| Always pick the home team | 51.8% | 43.6 – 59.9 |
| **Pick the better point differential** | **64.0%** | 55.8 – 71.5 |
| Originated model | 62.6% | 54.3 – 70.2 |

Model vs the better-differential rule: **−1.4 pp, p = 0.90**. The model is not better than a rule
that ignores the model. AUROC 0.702 and Brier 0.2266 (vs 0.25 for a coin flip) confirm the model
carries *some* signal — but that signal is already available from the raw point differential.

### 4.4 By tier: the middle is worthless, the top is real

| Tier | n | MAE | AUROC | Straight-up |
|---|---|---|---|---|
| **A** | 65 | 11.81 | **0.747** | **76.9%** (65.4 – 85.5) |
| B | 36 | 14.45 | 0.534 | 50.0% |
| C | 38 | 10.63 | 0.565 | 50.0% |

Tier A is the one genuinely interesting result: 76.9% on 65 games, AUROC 0.747. Tier C has the
lowest MAE but a coin-flip winner record — good margins, no discrimination, so it must stay unbet.

**Tiers were recomputed after the HCA fix, so earlier in-session tier figures are superseded by this
table.** This table is the output of the committed pipeline.

### 4.5 Calibration: the confident-middle bin is inverted

| Predicted | Observed | n |
|---|---|---|
| 30–40% | 25.0% | small |
| 40–50% | 38.3% | — |
| 50–60% | 54.4% | — |
| 60–70% | **73.9%** | — |
| 70–80% | 100% | 4 |

The 40–50% bin is overconfident (predicts 45%, delivers 38%); the 60–70% bin is *under*confident
(predicts 65%, delivers 74%). A model that is underconfident at the top is leaving conviction on the
table — and the 70–80% "100%" cell rests on four games and should be read as noise.

### 4.6 Correlation: the parlay premise is not supported

| Claim | Measured | Verdict |
|---|---|---|
| Margin and total are related (S-04 same-game parlay) | **r = −0.009** (95% CI −0.17 to 0.15), n = 155 | **not supported** |
| Parlay legs are dependent | joint 23.74% vs 22.89% independent, **+0.85 pp, z = 0.24** | no detectable dependence |
| Games on the same night are correlated | r = 0.0235 over 645 pairs | none |
| Back-to-back costs points | b2b −1.54 vs rested +1.27; **p = 0.38** | not significant |

The same-game-parlay argument in `S-04` assumed a margin/total relationship worth pricing. On 155
games there is none — the correlation is two orders of magnitude smaller than the noise band. The
honest treatment is to price parlay legs as independent and to state the residual (+0.85 pp) as an
unmeasured risk, not as an edge.

Rest is the one place where the effect is directional but underpowered: −2.8 pts for a back-to-back,
p = 0.38. The power table says roughly 500+ games would be needed to settle a 3-point effect.

---

## 5. Gates

Evaluated by `backtest/engine/gates.py`, which **reads the ten gate rules from `nba2/config.py` at
runtime** — the backtest cannot quietly relax a threshold to make itself pass.

| Gate | Status | Why |
|---|---|---|
| G-01 sample size (300 settled) | **FAIL** | 139 graded |
| G-02 line-shopping evidence | **BLOCKED** | no captured closing lines |
| G-03 calibration | **PARTIAL** | Brier 0.2266 ≤ 0.245 and n ≥ 100 met; calibration shape non-monotone |
| G-04 beat naive baselines by 0.30 MAE | **PASS — but DISPUTED** | wins against an unshrunk strawman; loses to a fair shrunk baseline by 0.08 pts (§5.1) |
| G-05 forward ROI | **PARTIAL** | forecast half done, ROI half blocked |
| G-06 bankroll / drawdown | **BLOCKED** | no settled bets |
| G-07 walk-forward, no lookahead | **PASS** | leakage-tested, degradation within 25% |
| G-08–G-10 | **PARTIAL / BLOCKED** | downstream of G-01 and G-02 |

**1 passed reliably (G-07), 1 passed only as registered and disputed (G-04), 1 failed (G-01),
3 partial, 4 blocked.** G-07 passing is a genuine, new result: the pipeline is now *demonstrably*
leak-free.

### 5.1 G-04 is a false positive, and that is a finding in itself

G-04's registered wording is *"beat both baselines by ≥ 0.30 MAE"*, where baseline (b) is a **raw,
unshrunk point differential**. In week one that quantity reads anywhere from **−66 to +31 points**
and is wrong by construction, so any sane model beats it. The gate passed, and a careless report
would have published that as skill.

Against a **fair** baseline — the same shrinkage, but *no* home-court term — the decomposition is:

| Component | MAE | Contribution |
|---|---|---|
| 0.0-spread baseline (a) | 13.27 | — |
| + shrinkage | **12.09** | **−1.17 pts (all of the gain)** |
| + home-court term (the model) | 12.17 | **+0.08 pts (slightly worse)** |

**Shrinkage does all the work; the home-court term does nothing on this sample.** Two consequences:

1. G-04 is now reported as `PASS` *as registered* with **`disputed: true`**, is excluded from the
   reward fraction (which falls from 2/6 to **1/6**), and is not counted as evidence of skill.
2. The registered gate wording should be tightened to compare against baseline (c). That is a
   **rule change** and is therefore listed as open question **Q-7 / decision D-01**, not made
   unilaterally by this report — changing a threshold after seeing the result is exactly the failure
   mode the gate exists to prevent.

This is the most valuable single result in the report: it caught the report's *own* temptation to
declare victory.

### Leaderboard

Strategies are ranked on a **deflated z** — `z = (acc − 0.5)/√(0.25/n)` divided by √k for the k = 4
pre-registered strategies, so a lucky subset cannot win by being chosen after the fact from a
search. Tier mapping is pre-registered: S-01→A, S-02→B, S-03→C, S-07→C.

| Rank | Strategy | Tier | n | Acc | z (raw) | z (deflated) | Reward |
|---|---|---|---|---|---|---|---|
| 1 | S-01 | A | 65 | 76.9% | 4.34 | 2.17 | **0** |
| 2 | S-02 | B | 36 | 50.0% | 0.00 | 0.00 | **0** |
| 3 | S-03 | C | 38 | 50.0% | 0.00 | 0.00 | **0** |

Reward is withheld from **every** strategy because G-01 fails (n = 65–38, far below 300) and the
gate fraction counts only reliable passes (1 of 6). That is the design
working: S-01's raw z of 4.34 would look like a triumph in a report that did not deflate for the
search or gate on the baselines.

---

## 6. What this changes about the platform

1. **The total line is worse than useless.** It loses to the league mean on MAE. Publishing it as a
   bet signal is a defect. Recommend: mark totals `BLOCKED` until a totals-specific model beats
   15.43 MAE.
2. **The spread edge is real at the top and absent in the middle.** Tier A is worth developing;
   tiers B and C should be published as information only, never as picks.
3. **"Our model is better than a naive rule" is not yet true.** It is 1.4 pp worse than picking the
   better point differential, with p = 0.90. Any headline claiming model edge overstates it.
4. **Parlay correlation pricing is unearned.** S-04's premise fails measurement; price legs as
   independent and disclose the +0.85 pp residual.
5. **The gates now have teeth — including against this report.** G-07 passes reliably; G-04 passed
   only against a strawman and is reported as disputed; no reward is paid. The gate framework is no
   longer decorative, and it caught the report's own temptation to declare victory (§5.1).

---

## 7. Open questions that must be answered before a decision

| # | Question | Why it blocks a decision | How to get it |
|---|---|---|---|
| Q-1 | What are the closing lines for 10/20 → 11/12? | ROI, CLV and G-02/G-05 are all unanswerable without a price. Straight-up accuracy is not a betting result. | Any licensed odds archive; the free tier covers historical closes |
| Q-2 | Can the 19 missing games be recovered? | They are 11% of the window and sit mid-sample, so they bias the rest/back-to-back estimates. | A paid results API, or a second official surface (`stats.nba.com` league game log) |
| Q-3 | Is Tier A's 76.9% stable out of sample? | n = 65 with a CI down to 65%. A 40-game forward window would settle it. | Continue the nightly capture; re-run this report on 11/13+ |
| Q-4 | Why does the total model lose to a constant? | It determines whether totals are fixable or should be retired. | Decompose total error into pace and efficiency components |
| Q-5 | Is the 60–70% bin's underconfidence real? | Correcting it is the cheapest available accuracy gain. | Recalibrate on the full window once n > 300 |
| Q-6 | Does the neutral-site game need its own HCA term? | One game in the sample (FLAG-BT-03); a wrong term silently corrupts pricing. | Set HCA to 0 for neutral games and verify against a larger neutral-site sample (Cup games) |
| **Q-7** | **Should G-04's baseline (b) be replaced by the shrunk no-HCA baseline (c)?** | As worded, G-04 can be passed by a strawman — it passed here while the model is *worse* than a fair baseline. Leaving it unchanged means the gate is decorative. | Propose baseline (c) in `nba2/config.py` as a **new registered rule version**, effective only on games *after* the amendment date, so the same sample cannot be re-scored |
| **Q-8** | **Does the home-court term earn its place at all?** | Measured contribution is +0.08 MAE — i.e. it makes the model slightly worse. If it never helps, it is a free parameter with no return. | Ablate HCA across the full window and across a second season before removing it |

**How to discover what is missing:** the fastest unblock is Q-1. Every ROI gate is currently
`BLOCKED` for exactly one missing input — a price. Until a closing-line source exists, no amount of
additional modelling can produce a bettable claim.

---

## 8. Suggestions for the site (for review, not implemented here)

The brief asks for a dedicated review area where a human chooses a path. Published at
`backtest/pages/suggestions.html`; this session implemented none of them beyond its own tree.

| # | Suggestion | Cost | Expected benefit |
|---|---|---|---|
| S-A | Link `backtest/` from the main navigation | trivial | the measured evidence becomes visible instead of buried |
| S-B | Lead the landing page with the honest headline ("model not yet distinguishable from a one-line rule") | trivial | stops the site overstating |
| S-C | Add a "Totals are BLOCKED" banner wherever totals are published | trivial | removes a defective signal from view |
| S-D | Show the Wilson CI next to every accuracy number | low | a reader can see 76.9% is 65–86% |
| S-E | Add a sample-size meter per strategy, against the 300-gate | low | makes "not yet knowable" legible |
| S-F | Capture closing lines nightly | medium | **unblocks every ROI gate** |
| S-G | Split the totals model into pace × efficiency | high | the only route to fixing §4.2 |
| S-H | Re-run this report automatically each night | low | turns a one-off into a track record |

---

## 9. Files

| Path | What it is |
|---|---|
| `data/raw/history/games_*.json` | 155 official finals, per-game source URL, integer `periods`, `neutral_site` |
| `data/raw/history/postgame_records_*.json` | 134 official post-game W-L rows used only for checking |
| `backtest/engine/walkforward.py` | point-in-time replay + `assert_no_leakage` |
| `backtest/engine/stats.py` | Wilson, permutation (seeded), AUC, Brier, power, MAE/RMSE |
| `backtest/engine/skill.py` | accuracy, ATS self-consistency, tiers, naive baselines, calibration |
| `backtest/engine/correlation.py` | margin×total, leg dependence, cross-game, rest |
| `backtest/engine/gates.py` | reads gate rules from `nba2/config.py`, returns verdicts |
| `backtest/engine/leaderboard.py` | deflated z, pre-registered tiers, reward gating |
| `backtest/engine/build.py` | builds `report.json` + 12 pages |
| `backtest/tests/test_backtest.py` | 46 tests: leakage, estimators, reward gating, no market claims |
| `tools/verify_backtest.py` | source-per-row, links, placeholders, null cells, determinism |

**Not touched** (owned by other sessions): `pages/**`, `index.html`, `data/site.json`, `nba2/**`,
`css/**`, `app.js`, `README.md`, `docs/**`, `dashboard/**`, `originated/**`, `verified/**`,
`data/raw/ledger/**`. Integration requests are logged in `COORDINATION.md`.
