# Strategy Leaderboard & Reward Framework

**Data:** [`data/leaderboard.csv`](../../data/leaderboard.csv)
**Design goal:** reward *skill that survives validation*, not hot streaks. This is a
season-long competition between strategies (S1–S5), graded by the gates in
[validation-gates.md](validation-gates.md).

## Scoring (each grading period = one NBA week, Monday–Sunday)

| Component | Weight | Notes |
|---|---|---|
| Shrunk ROI (Bayesian, prior 50 games at break-even) | 40% | never reward raw win% |
| CLV per pick (when market feed live, Q-1) | 35% | skill measure least touched by luck |
| Gate compliance (G1–G5 pass rate) | 15% | process hygiene |
| Drawdown control (max bankroll drawdown) | −10% | survival |

`Process Rating = 0.40·z(shrunk ROI) + 0.35·z(CLV) + 0.15·z(gates) − 0.10·z(drawdown)`

Tie-break order: (1) higher G2 progress, (2) lower drawdown, (3) more CLV-verified
picks, (4) earlier validation date.

## Reward structure (proposal — see S-2 in suggestions for the decision gate)

* **Weekly badges:** top Process Rating per week (no money) — keeps the board live.
* **Monthly pool:** points 10/6/3 to the top-3 Process Ratings of the month,
  **only among `reward-eligible` strategies** (≥ 100 graded picks, G1–G5 passed).
* **Season grand prize:** highest cumulative Process Rating; bonus multiplier ×1.5
  if the strategy holds CLV > 0 over ≥ 250 picks.
* **Anti-luck dividend:** 20% of any monthly pool is reserved for the most improved
  *expected-vs-actual* gap (a strategy that turned a lucky month into a skill month
  by process fixes).

Amounts/eligibility are a **proposal** pending your sign-off (suggestions queue S-2).
Until the market feed exists, CLV is proxied by `make_at` compliance and reward
payouts stay locked — the board still ranks and badges.

## Current board (seeded 2026-11-13)

| Strategy | Focus | Picks | Record | Process Rating | Gate status | Rewards |
|---|---|---|---|---|---|---|
| S1 originate-side | single bets: spread | 0 | 0-0 | n/a (pre-sample) | provisional | locked |
| S2 originate-total | single bets: total | 0 | 0-0 | n/a (pre-sample) | provisional | locked |
| S3a/S3b parlay | same-game 2-leg | 0 | 0-0 | n/a (pre-sample) | provisional (correlation caps enforced) | locked |
| S4 prop-combo | player prop + game leg | 0 | 0-0 | n/a (pre-sample) | provisional (market prop feed missing Q-2) | locked |
| S5 dog-upset | ML underdogs vs model | 0 | 0-0 | n/a | not activated (needs market ML feed Q-1) | locked |

Slate picks for 2026-11-13 → 11-16 are **logged entries** (38 single picks, 64
combo legs sets — see [`data/picks.csv`](../../data/picks.csv),
[`data/parlays.csv`](../../data/parlays.csv)); they begin grading tonight and count
toward G2 samples. Until 30 graded picks accumulate, everything is provisional —
that is the point of the gate.

## Season & reset rules

* One competition season = one NBA regular season + playoffs (playoffs graded at
  0.5 weight — thinner market).
* Strategies may be revised mid-season, but a revision spawns **S1-v2** etc.; the
  old version keeps its sample (no cherry-picking resets).
* If a strategy's raw ROI is top-3 but Process Rating is not, the board displays
  the pair side by side with a **"luck-contaminated"** tag — visible, never hidden.
