# Validation Gates & Luck Removal

A strategy must pass **all** gates before its results count on the
[leaderboard](leaderboard.md) or earn rewards. Gates are mechanical; no judgment
calls mid-season.

## Validation gates (every strategy, every season)

| Gate | Rule | Purpose |
|---|---|---|
| **G1 — Data integrity** | ≥ 95% of logged picks carry a verified source link; any pick with an unverified input is void for scoring | keeps fabricated/unknown inputs out of the sample |
| **G2 — Sample size** | ≥ 30 graded picks before any strategy is ranked; ≥ 100 before rewards pay out | kills small-sample luck |
| **G3 — Price honesty** | every pick records its `make_at` number; results graded **at our number**, never at a worse price; CLV logged when the market feed exists (Q-1) | a win at a bad price is not skill |
| **G4 — Risk & correlation caps** | max 2 legs from one game in any parlay; banned combos enforced (spread+ML same team r≈0.90); stake ≤ 0.25 fractional Kelly; no chasing (stake cannot double after a loss day) | survives variance; respects correlation matrix |
| **G5 — Luck separation** | a strategy's raw record must beat its **expected record** (from model win probability at kick) to earn performance points; the delta is published as the luck component | see below |

Status codes: `provisional` (in sample, gates partially passed) → `validated`
(G1–G5 all passed) → `reward-eligible` (G2 full sample reached). Current seeded
strategies are all `provisional` — this is the honest state on day one.

## Removing luck from the equation

Three stacked mechanisms, in [`data/luck-table.csv`](../../data/luck-table.csv)
and the leaderboard design:

### 1. Expected-record ledger (outcome luck)
Every game our model projects carries a win probability (logistic of predicted
margin, divisor 6.8 — derived from the Normal margin distribution with
σ ≈ 11.5 pts: `P(win) ≈ Φ(margin/11.5) ≈ logistic(margin/6.8)`).
A team's **expected wins** = Σ p(win). The **luck component** = actual − expected.

Current league leaders in luck (i.e. records ahead of what their ratings justify),
as of games through 2026-11-12:

| Team | Record | Expected wins | Luck component |
|---|---|---|---|
| PHI | 10-3 | 5.8 | **+4.2** |
| CHA | 4-8 | 1.4 | +2.6 |
| WAS | 4-9 | 2.5 | +1.5 |
| BOS | 10-2 | 8.6 | +1.4 |

PHI is the textbook case: a top-3 record with a *negative* adjusted net rating
(−1.42). Betting *on* their record and *against* their rating is how the public
donates; our model prices the rating, not the record.

### 2. Process Rating (skill score) vs raw ROI (luck-contaminated)
The leaderboard's **primary** sort is the Process Rating:

```
PR = 0.40·z(shrunk ROI) + 0.35·z(CLV per pick) + 0.15·z(gate compliance) − 0.10·z(max drawdown)
```

* **shrunk ROI** = Bayesian-shrunk win rate: `w' = (wins + 25) / (n + 50)` against
  the vig-free breakeven, i.e. results pulled hard toward the mean until the sample
  earns its way out (prior ≈ 25 pseudo-losses / 50 pseudo-games).
* **CLV** (closing line value) is the industry-standard skill measure — "wins and
  losses fluctuate with variance; closing line value accumulates with skill"
  ([onlinenbabetting.com](https://onlinenbabetting.com/spreads/)). It activates the
  moment a market feed exists (Q-1); until then G3 uses our `make_at` discipline as
  the proxy and PR is marked provisional.
* Raw ROI stays on the board, visually demoted and labeled *luck-contaminated*.

### 3. Conviction gating (selection luck)
Picks are only logged when the model's edge over its own baseline clears a
threshold (side: |margin| ≥ 4.0; total: ≥ 5.0 pts vs league mean). This stops the
strategy from betting every coin-flip and inflating variance — selectively skill
based, exactly as requested: the strategy plays only where the model has a stated,
repeatable reason.

## Correlation discipline

See [correlation.md](correlation.md) for the measured/estimated matrix. Hard rules:
* Same-game parlay legs ≤ 2 (G4).
* Leg pairs must exist in the matrix with a signed direction; unknown pairs default
  to r = 0 and are allowed only as singles.
* Negative-correlation combos (big favorite + star props, game under + props) are
  banned outright even if both legs pass individually.
