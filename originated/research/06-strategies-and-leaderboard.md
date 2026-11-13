# Strategies, Validation Gates & Leaderboard

---

## 1. The rule that keeps the leaderboard honest

**A strategy may only claim an edge if it conditions on information that is not already in the
originated line.**

The line already contains: shrunken net rating, the scoring environment of both teams, home court,
rest and time-zone travel. A "strategy" that simply restates any of those is circular — it would
report an edge against a line it helped build. Every strategy in the catalog therefore declares the
**residual information** it uses, and that declaration is shown on the site.

The residual signals available are: Pythagorean-vs-actual luck, last-10 vs season divergence,
home/away split divergence, the rotation-availability index, Cup status, streaks, and the
distance of a projected total from the league norm.

## 2. Validation gates

Eight gates. A strategy is only **deployable** if it passes all eight.

| Gate | Rule | Why |
|---|---|---|
| **G1** Sample size | every team in the window has played ≥ 8 games | guards against 2-game noise |
| **G2** Provenance | every input traces to a T1 or T2 source with a live link | the project's core rule |
| **G3** No look-ahead | every input is knowable before tip-off | prevents leakage |
| **G4** Correlation control | parlay legs within a game have \|φ\| ≤ 0.25, or the correlation is explicitly priced | naive parlay pricing assumes independence |
| **G5** Beats the vig | model probability exceeds the break-even of the assumed price | a signal that cannot beat the juice is not a signal |
| **G6** Out-of-sample | positive ROI on a walk-forward hold-out not used to set parameters | the only real defence against overfitting |
| **G7** Stability | perturbing the strategy's λ by ±25% does not flip any signal's direction | guards against knife-edge parameters |
| **G8** Reproducible | recomputable from `data/*.json` by `node engine/build.js` | guards against undocumented manual steps |

### G6 fails for every strategy, and that is correct

This repository contains **no graded historical bet log**. There is nothing to run a walk-forward
against. Rather than invent one, G6 is recorded as **BLOCKED** for all ten strategies and the
leaderboard is labelled **model-expected, not realised**. Fixing this is blocker **Q‑03** and it is
the highest-value improvement available to the project.

## 3. The catalog

| ID | Strategy | Family | Residual signal | λ |
|---|---|---|---|---|
| S01 | Pythagorean Regression (Luck Fade) | single | Pythagorean vs actual win% | 12.0 |
| S02 | Recent-Form vs Season Divergence | single | L10 win% vs season win% | 10.0 |
| S03 | Venue-Split Divergence | single | home-team home% vs away-team road% | 6.0 |
| S04 | Availability Fade | single | rotation-availability index (T1) | 0.35 |
| S05 | Emirates NBA Cup incentive | single | Cup group status | 2.5 (total) |
| S06 | Extreme-Streak Mean Reversion | single | streak length | 0.12 |
| S07 | Totals: Fade the Extremes | single | distance of total from league norm | 0.35 |
| S08 | Cross-Game Parlay Builder | parlay | cross-game independence | — |
| S09 | Same-Game Parlay correlation mispricing | parlay | within-game φ from Monte-Carlo | — |
| S10 | Player Prop Combos | prop | per-player season averages | **BLOCKED** |

## 4. How to read the leaderboard

The leaderboard ranks by **mean expected value per unit staked**, using the assumed market price
described in §6. It is **not** a record of money won — no bet has been placed and no result has
been graded.

A strategy showing `meanP = 0.578` is claiming: *"on the games where this strategy fires, our model
believes the named side wins 57.8% of the time, against a market that implies 50%."* Whether that
belief survives contact with real prices is exactly what gates G5 and G6 exist to test, and G6
cannot currently be run.

## 5. Parlays — the arithmetic

Parlays are priced at the **product of the vigged leg prices**. At the 4.77% overround implied by
a −110/−110 two-way market, a parlay of *fair* legs loses:

| Legs | Cost if no leg has an edge |
|---|---|
| 1 | 4.55% |
| 2 | 8.90% |
| 3 | 13.05% |
| 4 | 17.00% |

So each leg must clear its own break-even by roughly the overround (~4.8 percentage points of
probability) just to stand still. Parlays **amplify** edge exactly as fast as they amplify vig —
which is why the strategy only accepts legs the model believes are mispriced, and only one leg per
game (to keep inter-leg correlation at zero).

> Note on method: an earlier revision priced every parlay leg at a flat −110, which produced absurd
> +278% "edges" simply because a 63% favourite was being quoted at even money. Parlays are now
> priced from each leg's fair probability from our own line, with the overround applied.

## 6. Assumed market prices

There is **no market feed** in this repository (blocker Q‑01). Two declared prices are used, and
both are labelled everywhere they appear:

1. **−110 flat** — used only for the single-bet break-even screen (G5).
2. **4.77% overround** applied to each leg's fair probability from our own originated line — used
   to price parlays.

Neither is a real price. Both exist so that the arithmetic can be shown; neither should be
mistaken for a line you can go and bet.
