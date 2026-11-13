# Correlation Values — Sides, Parlays, Player-Prop Combos

**Data:** [`data/correlation-matrix.csv`](../../data/correlation-matrix.csv) — every
row carries its source link, basis type (`empirical` vs `industry estimate`), and
context. Values we could not source are **left out entirely** (nothing is inferred).

## Two evidence tiers

### Tier 1 — Empirical (measured on real game logs)
From ["NBA DFS Correlation: 3 Seasons, 500,000 Pairs"](https://kindoflost.com/2026/09/nba-dfs-correlation-measured/)
(505,721 player pairs, 62,681 player-games, 2023-24 → 2025-26, scored via public
NBA stats data):

| Pair | Context | Measured r |
|---|---|---|
| Teammate fantasy scores | close games (≤8) | −0.001 … +0.017 |
| Teammate fantasy scores | blowout profile (spread ≥ 11 / margin ≥ 15) | +0.029 … +0.074 |
| Opponent fantasy scores | close games | +0.021 … +0.023 |
| Opponent fantasy scores | blowouts | −0.020 … −0.009 |
| Two bigs, rebounds | same team | **−0.012 (negative)** |
| Two bigs, rebounds | opposing teams | +0.022 |

Two actionable findings: (1) stacking teammates only pays in blowout-type games —
in close games same-team fantasy correlation is ~zero; (2) **never** stack two
same-team bigs' rebounds — the empirical value is *negative* (they cannibalize each
other's boards).

### Tier 2 — Industry estimates (ranges, treated as priors)
From [gamblingcalc.com's SGP calculator](https://gamblingcalc.com/betting/basketball/nba-same-game-parlay-correlation-calculator/)
and [sportsbettingoddscalculator.com's SGP guide](https://www.sportsbettingoddscalculator.com/guides/sgp-correlation):

| Leg pair | r range | Use |
|---|---|---|
| Spread + ML same team | +0.85 … +0.95 | **BANNED** — effectively one bet |
| 1H spread + game spread | +0.80 … +0.90 | **BANNED** |
| Game total + team total (same direction) | +0.40 … +0.60 | core parlay engine (S3a) |
| Game total + both stars' points overs | +0.50 … +0.60 | use only in up-tempo profiles |
| Big's points + big's rebounds | +0.40 … +0.50 | prop combos |
| Team win + star points (spread < 7) | +0.35 … +0.45 | core star stack (S3b) |
| Underdog spread + underdog star assists | +0.30 … +0.40 | context play |
| Team total over + player points over | +0.15 … +0.25 | prop combos |
| Player points + assists (high-usage handler) | +0.10 … +0.20 | prop combos |
| Spread + total | +0.10 … +0.20 | neutral — do not treat as edge |
| Team win + star points (all games) | +0.05 … +0.15 | weak |
| Guard rebounds + assists | +0.00 … +0.05 | near-independent |
| Big favorite (≥11) + star props | −0.20 … −0.40 | **BANNED** (blowout minutes risk) |
| Game under + player props over | −0.30 … −0.50 | **BANNED** |

## How the values are used

1. **Parlay construction (S3a/S3b):** only pairs with a documented positive band
   are combined, max 2 same-game legs (G4). Our generator uses total-flow pairs
   (r +0.40…0.60) and star stacks in competitive games only (|our margin| ≤ 10 —
   staying under the blowout risk zone).
2. **Pricing:** when a market feed exists (Q-1), combined probability is computed
   with a Gaussian-copula adjustment using the band's midpoint —
   `p_joint ≈ p1·p2 + r·√(p1·(1−p1)·p2·(1−p2))` (the same first-order approximation
   documented by [gamblingcalc.com](https://gamblingcalc.com/betting/basketball/nba-same-game-parlay-correlation-calculator/)),
   and the band's low/high become our price-sensitivity range.
3. **Leaderboard honesty:** a parlay's expected value is computed *with* the
   correlation adjustment; strategies that stack banned combos fail G4 and go
   unranked.

## What is missing (and being sought)

* Player-specific correlation (usage-dependent): a Jokić points/assists/rebounds
  triple is tighter than a generic big's. Needs play-by-play data (Q-5).
* Bookmaker SGP price grids (to measure the *priced-in* correlation vs our
  estimates). Needs market feed (Q-1).
* Empirical spread/total correlations from our own graded history once G2 sample
  matures — these replace the industry priors over time.
