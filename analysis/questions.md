# Questions, Missing Information & Answers Register

Purpose: every decision in this project must be traceable to *known* information.
This register lists (a) what is **known and verified**, (b) what is **unknown** and
blocks or weakens decisions, (c) how each gap will be discovered. Nothing here is
inferred — "unknown" means unknown.

Format: **Q-n | Question | Known today | Missing | Discovery plan | Blocks what**

---

## Known & verified (the foundation we already have)

| Fact | Source |
|---|---|
| Full slate Nov 13–16 (31 games, game IDs, tip times) | [nba.com/games](https://www.nba.com/games?date=2026-11-13) each day page |
| All 30 team records through Nov 12 | NBA.com game pages cross-checked vs [Basketball-Reference](https://www.basketball-reference.com/leagues/NBA_2027_ratings.html) |
| Team efficiency ratings (ORtg/DRtg, schedule-adjusted) | [Basketball-Reference 2026-27 Team Ratings](https://www.basketball-reference.com/leagues/NBA_2027_ratings.html) (trusted secondary) |
| Official injury statuses for every Nov 13 game + partial Nov 14 | [Official NBA injury report 5:15 p.m. ET PDF](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_05_15PM.pdf) |
| Marcus Smart 3-game suspension (HOU) | [official.nba.com](https://official.nba.com/rockets-smart-suspended) |
| Season production baselines for 27 star players (PPG/RPG/APG) | NBA.com player pages (links in [`data/player-baselines-2026-11-13.csv`](data/player-baselines-2026-11-13.csv)) |
| Empirical same-team/opponent correlation values (3 seasons) | [kindoflost.com study](https://kindoflost.com/2026/09/nba-dfs-correlation-measured/) |
| Rest/B2B picture Nov 13–16 | derived from verified schedule ([`data/recent-games.csv`](data/recent-games.csv) + [`data/games.csv`](data/games.csv)) |

## Open questions (blockers first)

**Q-1 | What are the market lines (spread/total/ML) at pick time and at close?**
Known: NBA.com's odds toggle exists but the numbers are not exposed to our
fetching tools (JS-rendered); no official odds source reachable from this sandbox.
Missing: any market line feed. Blocks: edge measurement, CLV (the core of the
luck-removal scoring), S5 activation, real parlay pricing. Discovery: connect an
odds API (The Odds API, Betfair, or a licensed feed) — needs your account/key
decision (S-1); fallback: manual line capture page. Until then picks are
"make at our number" only.

**Q-2 | What are the market player-prop lines?** Known: our own prop projections
can be built from verified PPG/RPG/APG. Missing: book prop boards. Blocks: S4
grading, prop CLV. Discovery: same feed as Q-1 (most odds APIs carry props), or
scrape-later architecture with compliance review (S-4).

**Q-3 | What are the calibrated values of our model parameters?** Known: the
formula and each parameter's current assumed value (HCA 2.0, tier impacts 4.0/2.0/0.8,
fatigue −0.6/−1.1…, defense scalar 0.35, logistic divisor 6.8). Missing: fitted
values from data. Blocks: confidence in our numbers. Discovery: backtest on
historical game logs (needs a season of results — one API pull via `nba_api` once
network policy allows, or upload of a historical CSV); grid-search + shrinkage.

**Q-4 | What is full rotation production (not just each team's leader)?** Known:
28 verified team leaders; injury rows name every player. Missing: PPG/RPG/APG and
minutes for every rotation player. Blocks: correct injury impact tiers (the
MIN −28.0 vs CHI line on Nov 14 is materially wrong without Edwards' baseline —
flagged), prop coverage beyond stars. Discovery: NBA.com/stats player pages (fetch
in next session window) or `nba_api` per-team rosters; one 30-row table fixes it.

**Q-5 | What are player-specific (not generic) correlations?** Known: generic
bands from two sources + empirical DFS-pair study. Missing: per-player
points/rebounds/assists correlations (Jokić triples ≠ generic bigs). Blocks:
finer prop-combo pricing. Discovery: play-by-play data (nba_api) → compute pairwise
correlations over rolling 365 days.

**Q-6 | Which players are on minutes limits / returning?** Known: statuses (Out/
Q…) from the official report. Missing: explicit minutes restrictions (reports give
status, not minutes). Blocks: rotation-minute precision. Discovery: official team
PR notes (nba.com/news per team) at report time; coach quotes are secondary and
will be flagged as such.

**Q-7 | What are team-specific home-court values?** Known: league-level HCA ≈ 2.0
(secondary sources). Missing: team-specific HCA (e.g. altitude, arena effects).
Blocks: margin precision in close games. Discovery: compute home/away net-rating
splits from game logs (Q-3 dependency).

**Q-8 | What do Nov 15–16 official injury reports say?** Known: only through
Nov 14 partial. Missing: everything for Sun/Mon. Blocks: final lines for 17 games
(marked PENDING). Discovery: refresh from
[official.nba.com injury index](https://official.nba.com/nba-injury-report-2026-27-season/)
on game days — automated in the collection script's next revision.

**Q-9 | Do we want NBA Cup weighting?** Known: tonight's 9 games are all Cup group
games (standings shown on nba.com). Missing: whether our leaderboard weights Cup
games differently (motivation/effort literature is thin). Blocks: nothing — it's a
policy choice. Discovery: your decision via the suggestions queue (S-5).

**Q-10 | Bankroll & reward sizing?** Known: reward framework drafted
([leaderboard.md](analysis/strategy/leaderboard.md)). Missing: actual pool sizes,
unit definition. Blocks: payouts. Discovery: your sign-off (S-2).

## Standing unknowns (do not block; never silently filled)

* LAL / CHA / TOR season-leader baselines — not yet fetched from official pages
  (blank + flagged in [`data/player-baselines-2026-11-13.csv`](data/player-baselines-2026-11-13.csv)).
* Preseason expectations / futures markets (for priors in shrinkage).
* Referee assignments (officiating crew effects) — not collected.
* Any historical closing lines (for CLV backfill).

**Rule of this register:** when an answer becomes known, the row moves up to the
verified table with its official link, and the corresponding flag comes off the
[Flagged for Review](docs/flagged.html) page. Nothing is ever "assumed answered."
