# Line Origination Model v1.0 — Methodology

**Status:** active (parameter calibration pending — see Q-3 in [../questions.md](../questions.md))
**Code:** [`scripts/model.py`](../../scripts/model.py) (deterministic, stdlib-only, no network)
**Inputs:** [`data/team-ratings-2026-11-13.csv`](../../data/team-ratings-2026-11-13.csv), [`data/injury-report-2026-11-13.csv`](../../data/injury-report-2026-11-13.csv), [`data/games.csv`](../../data/games.csv), [`data/player-baselines-2026-11-13.csv`](../../data/player-baselines-2026-11-13.csv), [`data/recent-games.csv`](../../data/recent-games.csv)

## What "originate our own lines" means here

We publish **our own number** for every game (spread and total) and every eligible
player prop, produced by the model below. A pick is never "team X will win" — it is
*"our number says X; bet only at our number or better."* That is the originator's
contract: the line is the product, the pick is conditional on price.

## Game line formula

```
predicted home margin = (NRtg/A_home − NRtg/A_away) + HCA − injury_home + injury_away + fatigue_home − fatigue_away
predicted total       = league_mean + scoring-lean terms − 0.35 × (combined injury impact)
our spread (home)     = round(predicted margin) to nearest 0.5, expressed home-relative
our total             = round(predicted total) to nearest 0.5
```

* **Team strength** = Basketball-Reference *adjusted* net rating (`NRtg/A`, points per
  100 possessions, schedule-adjusted). Source: [Basketball-Reference 2026-27 Team Ratings](https://www.basketball-reference.com/leagues/NBA_2027_ratings.html)
  (trusted secondary — every row carries this link in the data file).
* **100 possessions ≈ 1 game** is an explicit approximation (modern pace is near
  100). Flagged as an uncalibrated parameter (Q-3).
* **HCA = 2.0 points.** Converging secondary estimates: home margin fell to ≈1.62 pts
  in 2024-25 ([ATS analysis](https://nbabettingsystem.com/spreads/)); bookmakers assign
  ≈2.05 pts on average ([kdus1060.com](https://kdus1060.com/nba-true-home-and-road-court-advantage/));
  traditional estimates 2–3 pts ([Sagarin summary](https://nbabettingrules.com/articles/nba-home-court-advantage-betting/)).
  Team-specific HCA is a listed upgrade (S-6 in suggestions).

## Injury impact model (rotation minutes & production)

Statuses come **only** from the official NBA injury report PDF
([Injury-Report_2026-11-13_05_15PM.pdf](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_05_15PM.pdf),
via [official.nba.com](https://official.nba.com/nba-injury-report-2026-27-season/)).

| Status | Multiplier |
|---|---|
| Out | 1.0 |
| Doubtful | 0.9 |
| Questionable | 0.5 |
| Probable | 0.1 |

| Player tier (verified PPG) | Margin impact if fully out |
|---|---|
| Star (≥ 24.0 PPG) | 4.0 pts |
| Starter (15.0–23.9 PPG) | 2.0 pts |
| Rotation / unknown | 0.8 pts |

* Team injury impact is **capped at 8.0 margin points**.
* G-League / two-way designations are excluded (no NBA rotation impact).
* Only each team's verified season-leader PPG is currently tiered (28 of 30 teams);
  everyone else falls to the "rotation / unknown" tier. This **understates** some
  losses (e.g. star players who are not the listed team leader) and is registered
  as Q-4 (full production data needed).
* The official report only covers games through Nov 14 in this snapshot. Lines for
  Nov 15–16 are marked **"PENDING — official report due day before game"** and are
  injury-unadjusted; they must be re-run when the reports land.

## Fatigue model (rest → rotation minutes)

Derived entirely from the verified schedule ([`data/games.csv`](../../data/games.csv)
+ [`data/recent-games.csv`](../../data/recent-games.csv)):

| Situation | Margin adjustment |
|---|---|
| Back-to-back, home | −0.6 |
| Back-to-back, road | −1.1 |
| 3 games in 4 days, home | −0.7 (on top of B2B if applicable) |
| 3 games in 4 days, road | −1.0 |

Verified situation notes for this window (from the schedule itself):
* **Nov 13:** no team on a B2B (the four Nov 12 games involve only teams resting today).
* **Nov 14:** B2B for CLE, MIA, MEM, NOP, CHI (all played Nov 13).
* **Nov 15:** DAL plays a road B2B (at CLE Nov 14 → at BOS) and its 3rd game in 4 days
  (Nov 12 at MIN, 14 at CLE, 15 at BOS).
* **Nov 16:** PHI (road B2B), HOU (road B2B + 3-in-4), WAS (home B2B), PHX (B2B with travel).

## Player prop origination

```
our prop line (points) = verified season PPG + 0.35 × (opponent DRtg/A − league mean DRtg/A)
```

* Baselines are the verified NBA.com season-leader rows ([`data/player-baselines-2026-11-13.csv`](../../data/player-baselines-2026-11-13.csv);
  every row links its nba.com player page).
* The defense term is a documented scalar (0.35) — uncalibrated (Q-3).
* Bet-able at: **Over** only at `line − 1.5` or better; **Under** only at `line + 1.5`
  or better (a 1.5-pt model-error buffer). Without a live market prop feed (Q-2),
  these are projections, not priced bets.
* Rebounds/assists projections are derived the same way from verified RPG/APG
  baselines; same buffer rule applies.

## Known limitations (honest list)

1. No market lines were reachable from official sources in this environment — edge
   vs market and CLV measurement cannot start yet (Q-1).
2. Team ratings are from a trusted secondary source (Basketball-Reference), not the
   NBA itself — flagged in every data row. NBA.com's stats JSON is not reachable
   from this sandbox.
3. Pace is approximated (100 poss ≈ 1 game).
4. Injury tiers use only verified leader PPG; full rotation production data is Q-4.
5. Nov 15–16 lines are pre-report and provisional by design.

Every one of these is on the [Flagged for Review](../../docs/flagged.html) page and
the [questions register](../questions.md).
