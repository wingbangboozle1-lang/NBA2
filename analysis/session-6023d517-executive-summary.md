# v7 executive summary — originated lines from the 2026-11-19 official snapshot

**Read this in one minute.** This layer re-cut the model from the official pages read on
2026-11-19 (the three team-stat pages, the standings page, the games list) and then tried to
beat the obvious rule on 167 games. It beats a coin flip and does **not** beat "back the team
with the better record" in any statistically meaningful way. Every stake is therefore 0.00,
and the measurement that says so is on the page next to the numbers it constrains.

## What was built

| Piece | Where | What it publishes |
|---|---|---|
| Originated slate, 3 days ahead | `site/v7-slate.html` | 19 games, 2026-11-19 → 11-21: both estimators, **their disagreement as the headline**, our spread, our total, rest/back-to-back/3-in-4, an empty availability column with its reason, and a 0.00 stake on every row |
| Strategy lab | `site/v7-strategies.html` | 10 strategies × 10 gates with the number each gate measured, 10 pre-registration files with sha256, and same-game parlays priced with the measured ρ beside the naive product |
| Measured skill & luck | `site/v7-skill.html` | walk-forward accuracy / log-loss / Brier against two baselines, the paired disagreement test, a luck z-score per club, the transcription corroboration, and the prop block with its arithmetic |
| Methodology | `site/v7-methodology.html` | every constant and whether it was fitted, the two clocks on the league's own site, and how each input was read |
| Verification | `site/v7-verify.html` | 7 structural checks and the 10 gates, all re-runnable |

## The numbers, and what each one means

| Measure | Value | Baseline | Reading |
|---|---|---|---|
| Walk-forward games | 167 | — | each predicted by a cut trained only on strictly earlier dates |
| Accuracy | 0.671 | 0.653 (better-record rule) | 1.8 points of accuracy over the naive rule |
| Log-loss | 0.6349 | 0.6931 (coin flip) | real improvement over a coin |
| Brier | 0.2199 | 0.25 (constant 0.5) | consistent with the log-loss |
| Paired test, model vs record rule | 16 vs 13 on 29 disagreements | exact p = 0.711 | **not significant**: the 1.8 points is noise at this sample |
| Home-win rate | 0.5143 over 210 finals | — | pins h = 0.602 pts |
| Margin σ | 16.81 pts | — | measured, not fitted |
| ρ (margin, total) | −0.044 [−0.178, +0.092] | 0 | indistinguishable from zero |
| Clubs outside the luck band | 0 of 30 | — | no club is refused by the luck gate at this date |

## Why nothing is staked — four independent reasons

1. **No market price exists in this build.** An edge is a difference between a probability and
   a price. With no price, there is no edge to compute; gate G-V7-6 is blocked and it blocks
   every strategy that needs one.
2. **The model does not separate from the better-record rule** (p = 0.711). It is better than a
   coin and not demonstrably better than the free rule.
3. **No injury report for these dates was read**, so the availability column is empty and the
   two strategies that depend on it (S-08, S-09's home-rate variant) cannot be evaluated.
4. **The prop sample is three games per player.** A prop line at ±5 points needs roughly
   15+ games; the block is arithmetic, not policy.

## What was fixed on the way in

The published tree was **not reproducible from its committed inputs** when this session
started: `python -m nba2.v6` exited 1 on a hard gate (G-V6-8) because 14 of 67 game rows had
no official URL. The URL was in the committed files — `finals_2026-11-1{4,5}.json` spell it
`final_source_url` — and the reader only knew `source_url`. Three repairs, no threshold moved:
the alias is read, the `"None @ None"` matchup string is gone, and the as-of clock is derived
from the newest committed capture instead of a typed literal that had gone stale. See
`analysis/session-6023d517-build-and-verification.md`.

## What to do next, in order of expected value

1. **Connect a closing-line feed.** Nothing on this site can become a bet until it exists.
   It is the single blocking input, and the market-anchored prior (S-10) is already written.
2. **Read the injury report every day for two weeks.** That turns the availability column from
   an empty promise into an input, and makes S-08 evaluable.
3. **Extend the player-log window past three games.** 15 games unlocks props; that is a data
   pipeline task, not a modelling task.
4. **Keep the 0.00 stake until the paired test clears p < 0.20 on at least 100 disagreements.**
   The gate is already written; it will not move by itself.

Each of these is also in the site's **Suggestions queue** with its cost and its blocker.
