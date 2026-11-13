# Line Origination

How a fair spread, total and moneyline is produced for each game. Every formula below is
implemented in [`engine/model.js`](../engine/model.js) and is reproducible with
`node engine/compute.js`.

---

## Step 0 — League context

Games-weighted league averages (`G` = games played):

```
lgPPG = Σ(PPG × G) / Σ G          = 113.43
lgOppPPG = Σ(OPP PPG × G) / Σ G   = 113.42   (identity check: must equal lgPPG)
```

Home-court advantage is **derived, not assumed**. From the home/away splits of all 30 teams:

```
homeWinRate = Σ homeW / (Σ homeW + Σ homeL) = 89 / 173 = 0.5145
HCA_points  = marginSD × Φ⁻¹(homeWinRate)  = 14.55 × Φ⁻¹(0.5145) = +0.53
```

> ⚠️ This is the most fragile number in the build. 173 split games give a standard error of about
> ±3.8 percentage points on the home win rate, and 0.5145 is well below the multi-season NBA norm.
> The **Sensitivity** panel re-prices the whole board at HCA = 0.5 / 1.5 / 2.5 so the reader can see
> how much rides on it. Two games flip favourite between HCA 0.5 and HCA 2.5.

## Step 1 — Team ratings

For each team, with `G = W + L`:

```
MOV        = PPG − OPP PPG
shrunkMOV  = (G × MOV + 12 × 0) / (G + 12)          [12-game league-average prior]
offRating  = PPG − lgPPG                            [points vs league average, scored]
defRating  = lgPPG − OPP PPG                        [positive = allows fewer than average]
pythWin%   = PPG^13.91 / (PPG^13.91 + OPP PPG^13.91)  [Morey / Basketball-Reference exponent]
luck       = actualWin% − pythWin%
```

The 12-game prior is a declared assumption. At 10–13 games played it removes roughly half of each
team's observed differential, which is deliberate — early-season MOV is extremely noisy.

**`luck` is the project's "remove luck" signal.** A team at +0.20 luck is winning about 2.4 games
more than its scoring profile implies, and is a fade candidate regardless of its headline record.

## Step 2 — Projected total

```
E[away pts] = lgPPG + k × (away.offRating − home.defRating) / 2      k = 0.85
E[home pts] = lgPPG + k × (home.offRating − away.defRating) / 2
total       = E[away] + E[home]
```

The sign of `defRating` matters: a strong defence has a **positive** `defRating` and must be
**subtracted**. (An earlier revision of this model added it, which inflated the totals of every
game involving a bad defence. It is now covered by the accounting-identity check.)

`k = 0.85` shrinks the projection toward the league average. Without it, a team allowing 15.4
points more than average (Chicago) drags its opponent's projection to implausible heights.

## Step 3 — Projected margin

```
ratingΔ      = home.shrunkMOV − away.shrunkMOV
baseMargin   = ratingΔ + HCA_points
restAdj      = (restPts(home) − restPts(away))          [0 if rest unknown]
tzAdj        = −0.15 × |tzHome − tzAway|                [charged to the traveller]
margin       = baseMargin + restAdj + tzAdj
```

`restPts` = **−1.6** on the second night of a back-to-back, **+0.25** for 3+ days of rest,
otherwise 0. Rest is derived from the official schedule **within the 3-day window only**, so it is
**unknown** for the 13 Nov games (the 12 Nov slate was not collected) and is set to 0 there.

## Step 4 — Prices

```
spread  = −round_half(margin)                     [from the home team's perspective]
total   = round_half(total)
P(home) = Φ(margin / marginSD)                    marginSD = 14.55
ML      = americanOdds(P(home))
```

A **Pythagorean / log5 cross-check** is computed alongside, entirely independently of the Normal
assumption and without a home-court term:

```
pythP(home) = log5(home.pythWin%, away.pythWin%)
            = (pH − pH·pA) / (pH + pA − 2·pH·pA)
```

The two probabilities are shown side by side on the Lines page. Where they disagree, the
disagreement is itself information — usually that one team's record is out of line with its
scoring profile.

## Step 5 — The simulator

200,000 draws per game, seeded (seed `20261113` + a hash of the game id) so every figure on the
site is reproducible.

```
pace  = 1 + 0.04·z                          multiplicative possessions shock, applied to both teams
away  = (mA + 11.5·xa) × pace
home  = (mH + 11.5·xh) × pace
xh    = 0.20·xa + √(1 − 0.20²)·xb          within-game score correlation
```

The simulator is **anchored to the published line**, not to the raw points model:

```
mH − mA = the originated margin
mH + mA = the originated total
```

Without this anchoring the spread and the simulator disagree and `P(home covers)` drifts far from
0.500. With it, the worst deviation across the 23 games is **0.0055**.

Calibration check on 13 Nov games: realised single-team score SD ≈ 12.7, margin SD ≈ 14.5,
total SD ≈ 20.0, score correlation ≈ 0.31.

## Declared assumptions

Every one of these is a modelling choice, **not** a sourced fact. They are all exposed on the
Flagged for Review page and every one appears in the sensitivity panel.

| Parameter | Value | Why it matters |
|---|---|---|
| `priorGames` | 12 | how far each team's MOV is pulled to league average |
| `kTotal` | 0.85 | how far projected scores are pulled to league average |
| `sdScore` | 11.5 | sets the width of every probability on the site |
| `rhoScore` | 0.20 | within-game score correlation before the pace shock |
| `paceSd` | 0.04 | the only mechanism coupling totals to team quality |
| `pythagExp` | 13.91 | Pythagorean exponent (Morey / Basketball-Reference) |
| `restB2B` | −1.6 | back-to-back penalty |
| `rest3Plus` | +0.25 | extended-rest bonus |
| `tzPerHour` | −0.15 | travel penalty per time zone |
| `injuryK` | 0.35 | points per unit of rotation-availability index — **uncalibrated** |
| `mcIterations` | 200,000 | Monte-Carlo precision |

## What is deliberately **not** in the line

The injury / availability index is computed and published, but its **translation into points is
uncalibrated** — we have no historical sample from which to estimate how many points a unit of
missing rotation is worth. Rather than bake an unverified coefficient into every line on the
board, the availability overlay is reported as a **separate column** and as a strategy (S04).
The same treatment is given to the Cup, streak and venue-split effects.
