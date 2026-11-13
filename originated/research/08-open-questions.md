# Open Questions

A single register of **what we know**, **what we do not know**, and **how to go and find out**.
Nothing here is speculation — every "do not know" is a specific, named missing input.

Ordered by how much it blocks.

---

## BLOCKERS — the system cannot produce a bettable edge until these are answered

### Q-01 · What price will the market actually give us?
- **We have:** fair originated lines for every game in the window.
- **We do not have:** any market price, from any book, for any game.
- **Why it blocks:** "edge" is `our probability − the market's implied probability`. With no market
  price there is no edge, only a fair price. Every EV number on this site is computed against an
  **assumed** −110 and an **assumed** 4.77% overround. Those are placeholders.
- **How to find out:** add a market adapter. Options, cheapest first: (a) a paid odds API key
  (The Odds API, SportsDataIO) with a per-day call budget; (b) manual capture of closing prices
  for the slate; (c) scrape of a licensed sportsbook — check terms of service and local law first.
- **Decision needed:** which source, what budget, and do we store **closing** prices only (better
  for backtesting) or the full price history (better for CLV)?
- **Affects:** Strategies, Leaderboard, Picks, Correlations. **Blocks gates G5 (partly) and G6.**

### Q-02 · What are the official per-player season averages and minutes?
- **We have:** player status and reason from the official injury report, for 81 players.
- **We do not have:** any per-player minutes, usage, points, rebounds or assists.
- **Why it blocks:** player props cannot be originated at all without it. Every prop cell on this
  site is deliberately blank.
- **How to find out:** restore `stats.nba.com` access in the build environment, or obtain an
  official NBA Stats API key and pull `leaguedashplayerstats`. Failing that, an official team
  roster page per team (30 fetches) gives minutes only.
- **Decision needed:** is a paid NBA data licence in scope for this project?
- **Affects:** Props page, strategy S10, the injuries→production model. **Blocks gate G2 for S10.**

### Q-03 · What actually happened in past games?
- **We have:** season-to-date aggregates (W-L, PPG, OPP PPG, splits).
- **We do not have:** a single box score, and no graded record of any bet.
- **Why it blocks:** gate **G6 (out-of-sample validation) cannot be run at all.** Eight of ten
  strategies are otherwise deployable and are held back solely by this. It also blocks calibrating
  `injuryK`, `restB2B` and `tzPerHour`, which are currently educated guesses.
- **How to find out:** pull `stats.nba.com/stats/leaguegamelog` for the last 2–3 seasons (one
  request per season) and store the results in `data/history/`. Then start logging every signal the
  system emits, with a result column filled in after each game.
- **Decision needed:** how many seasons of history, and who owns the daily grading step?
- **Affects:** every strategy, the leaderboard, all calibrated parameters.

---

## HIGH — materially degrades accuracy

### Q-04 · How many points is a missing rotation player worth?
- **We have:** a rotation-availability index built from the official report (T1).
- **We do not have:** any estimate of its conversion into points.
- **Why it matters:** `injuryK = 0.35` is an uncalibrated guess. It is reported as an overlay and
  as strategy S04 rather than baked into every published line, but it is still the largest
  unquantified term in the model.
- **How to find out:** with Q-03 answered, regress realised margin on the index differential across
  a full season.
- **Decision needed:** none — this is purely a data problem. It self-resolves once Q-03 is done.

### Q-05 · What is each team's pace and schedule strength?
- **We have:** per-game scoring and allowed.
- **We do not have:** possessions, so all ratings are **per game**, not per 100 possessions.
- **Why it matters:** two teams with identical PPG can be very different if one plays at a fast
  pace. It also means we cannot compute true offensive/defensive ratings, and we apply no
  opponent adjustment (ratings are only shrunk toward the mean, not adjusted for who was played).
- **How to find out:** `stats.nba.com` `leaguedashteamstats` exposes PACE. Schedule strength can be
  computed from the game log in Q-03.
- **Decision needed:** none.

### Q-06 · What is the official Emirates NBA Cup group tiebreaker?
- **We have:** which games are Cup games, and which group (T1, from nba.com).
- **We do not have:** the official tiebreaker rule.
- **Why it matters:** if the tiebreaker is point differential, teams have an incentive to run up the
  score, which biases Cup games toward the over. Strategy **S05** rests entirely on this.
- **How to find out:** read the official rules at
  [nba.com/nba-cup/2026](https://www.nba.com/nba-cup/2026). One page. **S05 is held at gate G2
  (provenance) = FAIL until this is confirmed.**
- **Decision needed:** none — it is a verification task, and it is the cheapest blocker on this list.

---

## MEDIUM — affects specific outputs

### Q-07 · What is the real margin-vs-total correlation?
- **We have:** a model-derived value of ≈ 0 (see Correlations).
- **We do not have:** the empirical value.
- **Why it matters:** it is the whole basis of strategy S09. Our model says independence pricing is
  nearly fair for winner × totals parlays; real data may disagree.
- **How to find out:** with Q-03 answered, compute the realised correlation of margin and total
  across a season, and the realised φ between moneyline and totals outcomes.
- **Decision needed:** none.

### Q-08 · Did the teams playing on 13 Nov play the night before?
- **We have:** the full 13–15 Nov slate.
- **We do not have:** the 12 Nov slate.
- **Why it matters:** the rest/back-to-back adjustment is **set to zero** for all nine 13 Nov games
  because we cannot tell whether either team is on a back-to-back. It is not guessed.
- **How to find out:** one extra fetch of `nba.com/schedule` covering 12 Nov, or extend the schedule
  collection window to 7 days and keep it in `data/`.
- **Decision needed:** how wide should the schedule collection window be? (Recommend 10 days: it
  costs one fetch and answers rest for every game in the 3-day window.)

### Q-09 · Is the derived home-court advantage real, or small-sample noise?
- **We have:** 89-84 (.5145) across 173 split games → **+0.53 points**.
- **We do not have:** enough games to trust it. The standard error on the home win rate is about
  ±3.8 percentage points, and the multi-season NBA norm is usually quoted much higher.
- **Why it matters:** it is the single largest source of error in the originated spreads. Two games
  on this slate flip favourite between HCA 0.5 and HCA 2.5.
- **How to find out:** recompute after ~20 games per team, or blend with a documented multi-season
  prior — which requires that prior to be sourced, not remembered.
- **Decision needed:** do we publish the season-derived value (data-faithful, unstable) or a
  blended value (more accurate, needs a sourced prior)? **This is a genuine judgement call and is
  the top item on the Suggestions page.**

### Q-10 · Are the 14 Nov and 15 Nov injury reports available yet?
- **We have:** `NOT YET SUBMITTED` for all ten 14 Nov team rows, and nothing at all for 15 Nov.
- **Why it matters:** the availability index is at its most valuable close to tip-off. Right now the
  15 Nov games have no injury input whatsoever.
- **How to find out:** re-pull the injury report later on 13 Nov (teams typically re-file at 05:00
  PM) and again on 14 and 15 Nov. The report URL is predictable:
  `Injury-Report_<YYYY-MM-DD>_<HH>_<MM><AM|PM>.pdf`.
- **Decision needed:** how often should the pipeline re-pull? (Recommend: on demand, plus a
  scheduled pull at 1 PM, 5 PM and 8 PM ET on slate days.)

---

## Answers we DO have (so nobody re-derives them)

| Question | Answer | Source |
|---|---|---|
| How many games on each day of the window? | 9 / 5 / 9 = 23 | [nba.com/schedule](https://www.nba.com/schedule) |
| Are the 13 Nov games Cup games? | Yes, all nine; three groups per conference | [nba.com/schedule](https://www.nba.com/schedule) |
| Do all 30 teams appear in the window? | Yes — 18 on 13 Nov, +5 on 14 Nov, +7 on 15 Nov | [nba.com game rail](https://www.nba.com/game/nyk-vs-ind-0022600034) |
| Do ESPN's W-L records match nba.com's? | Yes, 30/30 | S04 vs S02 |
| Do the accounted points balance? | Yes — weighted mean PPG 113.43 vs OPP 113.42 | derived |
| Is the line self-consistent? | Yes — P(home covers its own spread) = 0.500 ± 0.0055 | derived |
| What is the largest correlation on the board? | home win ↔ home covers, φ ≈ 0.80 | derived (Monte-Carlo) |
| What is the winner × totals correlation? | ≈ 0, max \|φ\| 0.0136 | derived (Monte-Carlo) |
| What does a 3-leg parlay cost with no edge? | 13.05% | derived, at 4.77% overround |
