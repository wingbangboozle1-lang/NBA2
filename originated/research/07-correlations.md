# Correlation Values

---

## 1. Where these numbers come from

There is **no historical betting database in this repository**, so no correlation here is an
empirical sample statistic. Every value is instead **derived from this project's own model** by
Monte-Carlo: 200,000 simulated score pairs per game, seeded and reproducible
(`node engine/compute.js`).

That distinction matters and is stated on the site. A derived correlation inherits every
assumption in the simulator — chiefly `sdScore`, `rhoScore` and `paceSd`. Where the model has no
mechanism to produce a correlation, it reports ≈ 0, and that too is reported honestly rather than
filled in from memory.

## 2. Two different correlation measures

| Measure | On | Used for |
|---|---|---|
| **Pearson r** | continuous quantities (scores, margin, total) | understanding the shape of the game |
| **φ (phi)** | binary market outcomes (win / cover / over) | **parlay pricing** — this is the one that matters for betting |

Binarising destroys most of a correlation. On this slate the continuous margin-vs-total
correlation reaches **0.061** for the most lopsided game, while the binary φ between the
corresponding moneyline and totals legs peaks at **0.0136**. Parlays are priced off the binary
number, so the binary number is the one published.

## 3. What the model produces

### Within one game

| Pair | Typical range | Reading |
|---|---|---|
| away score ↔ home score | ≈ **0.31** | shared pace and game script. This is a *calibration target*, not a finding — the parameters are tuned to land here |
| away score ↔ total | ≈ 0.88 | mechanical: a team's score is most of the total |
| margin ↔ total | **−0.04 to +0.06** | see §4 |
| **home win ↔ home covers** | **≈ 0.80** | the strongest correlation on the board |
| home win ↔ over | −0.005 to +0.004 | negligible |
| home cover ↔ over | ≈ −0.004 | negligible |

### Across different games

**Zero, by construction.** The simulator draws each game independently, and the games are disjoint
events. This is the assumption that makes cross-game parlays priceable as a simple product, and it
is the one assumption in parlay pricing that is safe.

## 4. The important negative result

**Same-game moneyline × totals parlays are priced essentially fairly by the independence
assumption.** Across all 23 games, the largest \|φ\| between a winner leg and a totals leg is
**0.0136** — under 1.4 percentage points. In money terms the independence price is off by a
fraction of a percent.

This is a consequence of the model's structure, and it is worth stating plainly: under a
bivariate-normal score model with approximately equal variances, `Cov(margin, total) =
Var(home score) − Var(away score)`, which is ~0. The only mechanism in this simulator that can
move margin and total together is the multiplicative **pace shock**, and because it scales both
scores by the same factor its effect on the *difference* is second-order.

Real NBA data does show a modest margin-vs-total correlation, driven by things this model does not
have: score-variance heterogeneity between teams, garbage-time substitution, intentional fouling
and clock management. **We cannot measure any of that without play-by-play or quarter-level box
scores**, so we do not publish a number for it. This is logged as **Q‑07**.

## 5. The correlation that actually bites

**moneyline ↔ spread-cover, φ ≈ 0.80.**

Parlaying "Team A to win" with "Team A to cover" is roughly 80% correlated — not the near-1.0 a
bettor might assume, but nowhere near independent. Multiply the two legs' prices as if they were
independent and you understate the true joint probability by a wide margin.

This is precisely the pair sportsbooks **restrict or refuse** in same-game parlays. The model
reproduces the reason for that restriction from first principles, which is a useful validation
that the simulator is behaving sensibly.

## 6. Sensitivity

The correlations are functions of `rhoScore` and `paceSd`, both declared assumptions. The
sensitivity panel re-runs the board at `rhoScore ∈ {−0.10, 0.10, 0.30, 0.50}` and reports the
resulting spread, total and win probability for each game, so the reader can see which conclusions
survive a change of assumption and which do not.

| If the true score correlation were… | Then… |
|---|---|
| negative (−0.10) | blowouts would tend to be lower-scoring; margin-vs-total correlation turns weakly negative |
| ~zero | margin and total essentially independent |
| strongly positive (0.50) | same-game winner × over parlays become systematically underpriced by independence |

Until we have real box-score history, we cannot say which row of that table is true.
