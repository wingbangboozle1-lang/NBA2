# Injuries, Rotation Minutes, Production & Game Flow

---

## 1. What the official report gives us

The [Official NBA Injury Report](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_01_00PM.pdf)
(7 pages, published 11/13/26 01:00 PM) is the project's richest **T1** source: 81 player rows
plus 10 `NOT YET SUBMITTED` team rows for the 14 Nov games.

Its columns are exactly:

```
Game Date | Game Time | Matchup | Team | Player Name | Current Status | Reason
```

### Statuses

| Status | Meaning | Weight in the index |
|---|---|---|
| Out | Will not play | 1.00 |
| Doubtful | Unlikely to play | 0.75 |
| Questionable | Uncertain | 0.40 |
| Probable | Likely to play | 0.15 |
| Available | Expected to play; monitored | 0.00 |
| NOT YET SUBMITTED | team had not filed | **excluded** |

`NOT YET SUBMITTED` is excluded on purpose. It is an **absence of information**, and treating it
as "healthy" or as "one unavailable player" would both be fabrications.

## 2. Three separate indices (and why the distinction matters)

| Index | Includes | Use |
|---|---|---|
| **rotationIndex** | Injury/Illness, Not With Team, League Suspension | the only index that drives a betting signal |
| **injuryIndex** | Injury/Illness only | diagnostic |
| **gLeagueIndex** | G League – Two-Way, G League – On Assignment | diagnostic only |

**Why split them:** a G League two-way assignment removes a player who was not in the NBA
rotation. Counting those rows as rotation losses is the single easiest way to get this wrong, and
it materially changes the answer. Worked example from this slate:

| Team | All rows | G League rows | rotationIndex |
|---|---|---|---|
| Oklahoma City Thunder | 5 Out + 1 Questionable | 0 | **5.40** |
| LA Clippers | 4 Out | 1 (Martinelli) | **4.00** |

Counted naively, the Clippers look *more* depleted (5.0 vs 5.4 — close). Once G League rows are
stripped out, the gap widens and the direction is unambiguous: **OKC is the more short-handed
team**, which inverts the naive read on OKC @ LAC.

## 3. Why minutes and production impacts are **blank**

Tracking injuries through to rotation minutes and individual production requires two inputs this
project does not have:

1. **per-player season minutes** (to know how many minutes a sidelined player actually vacates), and
2. **per-player usage / production rates** (to know who absorbs them).

Neither is available from any reachable official source — `stats.nba.com`, which is the NBA's own
per-player endpoint, is unreachable from this build environment (see
[Data & Sources](03-data-and-sources.md)). Under the project rule, those cells are therefore
**left blank and flagged UNVERIFIED**, not estimated.

A previous session published figures like *"~34 MPG season avg"* and *"-100% scoring output"* with
no source. Those have been removed; the correction is logged as irregularity **I-03**.

### What is published instead

For each team: the **rotation-availability index**, the **count by status**, the **full player list
with the official reason**, and the **points-overlay at the declared (uncalibrated) coefficient**.
The overlay is shown as a separate column precisely because the coefficient is not calibrated.

### How to unblock it

1. Restore `stats.nba.com` access (or supply an official NBA Stats API key) →
   `leaguedashplayerstats` gives season minutes and usage per player.
2. Then: `vacated minutes = Σ(minutes of players at Out/Doubtful)`,
   `absorbed = redistribute by each remaining player's usage rate`, and
   `production delta = absorbed minutes × per-minute rate`.
3. Only calibrate the points coefficient `injuryK` after at least one full season of that data.

See **Open Questions Q‑02** and **Q‑04**.

## 4. Game flow

Game flow factors are derived from the official schedule (T1) with no external input.

| Factor | How it is derived | Status |
|---|---|---|
| **Rest days** | gap between a team's games inside the 3-day window | known for 14–15 Nov; **unknown for 13 Nov** |
| **Back-to-back** | rest days = 0 | derived |
| **Time zones crossed** | UTC offset of home market vs venue market | derived |
| **Venue** | from nba.com | T1 |
| **Cup group** | from nba.com | T1 |

### Back-to-backs on this slate

| Date | Game | Team on the second night of a B2B |
|---|---|---|
| 14 Nov | DEN @ NOP | **New Orleans** (played 13 Nov vs MEM) |
| 14 Nov | DAL @ CLE | **Cleveland** (played 13 Nov at MIA) |
| 14 Nov | BKN @ MEM | **Memphis** (played 13 Nov at NOP) |
| 14 Nov | CHI @ MIN | **Chicago** (played 13 Nov vs ATL) |
| 14 Nov | DET @ MIA | **Miami** (played 13 Nov vs CLE) |
| 15 Nov | DAL @ BOS | **Dallas** (played 14 Nov at CLE) |

Two of these compound with travel: **Chicago** plays at home on 13 Nov then travels to Minnesota,
and **New Orleans** hosts Memphis then hosts Denver (no travel, but a B2B against a rested
Denver team that last played 12 Nov).

### Rest is unknown for 13 Nov

The 12 Nov slate was not collected in this session, so rest days for the nine 13 Nov games are
**null**, not zero. The model applies **no** rest adjustment rather than guessing one. This is
flagged on the Lines page and is the reason those games' `restKnown` flag is false.

## 5. Cup motivation — a hypothesis, not a finding

All nine games on 13 Nov are **Emirates NBA Cup** group games (three groups per conference). If
group standings are separated by **point differential**, teams have an incentive to keep scoring
in blowouts, which would bias Cup games toward the over.

That tiebreaker rule has **not** been verified against an official NBA document in this session.
Strategy **S05** is therefore held at gate **G2 (provenance) = FAIL** and its output is published
as a hypothesis only. Verifying the rule is a one-line check against
[nba.com/nba-cup/2026](https://www.nba.com/nba-cup/2026) — see **Open Questions Q‑06**.
