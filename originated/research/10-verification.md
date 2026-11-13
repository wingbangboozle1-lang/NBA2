# Verification

How every number on this site was checked, and what is still unchecked.

---

## 1. The rule

> Every table row must carry a source link to an official site. If a value cannot be confirmed from
> an official source, it is left blank and flagged as unverified. No value is inferred or filled in.

Enforcement is structural, not procedural:

- Every row in `data/*.json` carries a `src` field naming an entry in `data/sources.json`.
- `data/sources.json` holds the URL, the tier and the retrieval date for each source.
- Unverifiable numeric fields are stored as **`null`**, not zero and not an estimate.
- The site renders `null` as **— UNVERIFIED —** and lists every such cell on the Flagged page.
- Model output is never presented as data; it is labelled MODEL OUTPUT and its formula is published
  in [Line Origination](04-line-origination.md).

## 2. Automated checks

`node engine/verify.js` runs all of these and exits non-zero on any structural failure.

| Check | Expectation | Result |
|---|---|---|
| Every team referenced by the slate exists in `teams.json` | 0 dangling | PASS |
| Every team referenced by the injury report maps to a known team | 0 dangling | PASS |
| Games per day match the nba.com headers | 9 / 5 / 9 | PASS |
| `mean(PPG)` == `mean(OPP PPG)` (games-weighted) | \|diff\| < 0.05 | PASS (113.43 / 113.42) |
| `P(home covers its own originated spread)` ≈ 0.500 | max deviation < 0.01 | PASS (0.0055) |
| Every data row has a `src` that exists in `sources.json` | 0 missing | PASS |
| Every strategy has all 8 gates evaluated | 8/8 present | PASS |
| No generated page contains an unresolved internal link | 0 broken | PASS |
| Every `null` numeric cell appears on the Flagged page | 0 unlisted | PASS |

Run it yourself:

```bash
node engine/compute.js     # rebuild data/derived.json from data/*.json
node engine/build.js       # rebuild index.html and pages/*.html
node engine/verify.js      # run every check above
```

## 3. Manual verification performed

### Official NBA schedule — [nba.com/schedule](https://www.nba.com/schedule)
All 23 games were read row by row from the server-rendered page: date, tip time (ET), teams, venue,
city, broadcaster and Cup group. The games-per-day counts were cross-checked against the page's own
headers ("9 Games", "5 Games", "9 Games"). Each game additionally has its own official NBA.com game
page linked from the Slates table — open any of them to confirm a row directly.

### Official NBA injury report — [PDF](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_01_00PM.pdf)
All 7 pages transcribed row by row: 81 player rows plus 10 `NOT YET SUBMITTED` team rows. Player
names, statuses and reason strings are reproduced verbatim, including the report's own punctuation
(e.g. *"Injury/Illness - Left Great Toe - Sprain"*).

Two teams that play on 13 Nov — **Milwaukee** and **New York** — have no player rows in this
edition. That is the report as published, not a transcription gap, and it is flagged (F-INJ-01).

### Team records — cross-verified between two independent sources
W-L for all 30 teams was taken from the T1 [NBA.com game rail](https://www.nba.com/game/nyk-vs-ind-0022600034)
and compared row by row against the T2 [ESPN standings](https://www.espn.com/nba/standings).
**30 of 30 match.** The 18 teams playing on 13 Nov were independently re-read from the ESPN
scoreboard as a third check: 18 of 18 agree.

### Team scoring splits — T2 only
PPG, OPP PPG, DIFF, home/away/div/conf splits, streak and last-10 come from ESPN. These are **not**
from an official NBA property, because `stats.nba.com` is unreachable from this build environment.
Every one of these cells is therefore flagged **"T2 — trusted, not official"** on the site.

---

## 4. What is NOT verified

| Item | Status | Why | Where to see it |
|---|---|---|---|
| Every individual player prop threshold | **blank** | no official per-player feed (Q-02) | Props page; Flagged |
| Minutes vacated by an injured player | **blank** | needs per-player season minutes | Injuries page; Flagged |
| Production absorbed by the next man up | **blank** | same | Injuries page; Flagged |
| `injuryK` = 0.35 (points per availability unit) | **assumption** | no history to calibrate against (Q-04) | Flagged |
| `restB2B` = −1.6, `rest3Plus` = +0.25 | **assumption** | no history | Flagged |
| `tzPerHour` = −0.15 | **assumption** | no history | Flagged |
| `priorGames` = 12, `kTotal` = 0.85 | **assumption** | shrinkage choices | Flagged |
| `sdScore`, `rhoScore`, `paceSd` | **assumption** | simulator calibration targets | Flagged |
| Pythagorean exponent 13.91 | **published constant** | Morey / Basketball-Reference, not an NBA figure | Flagged |
| Emirates NBA Cup tiebreaker | **unverified** | not yet read from an official page (Q-06) | Flagged; S05 held at G2 |
| Realised margin-vs-total correlation | **unknown** | needs box-score history (Q-07) | Flagged |
| Rest state for the nine 13 Nov games | **unknown** | 12 Nov slate not collected (Q-08) | Flagged |
| Realised ROI of any strategy | **none exists** | no graded bet log (Q-03) | Leaderboard banner |

## 5. How to re-verify any figure yourself

1. Open the page showing the figure.
2. Follow the source link in the row (or the page's source panel).
3. For model output, open the formula in [Line Origination](04-line-origination.md) and re-run
   `node engine/compute.js` — the simulator is seeded, so you will get the **identical** numbers.

If a figure disagrees with its source, it is a bug. Please log it in `COORDINATION.md` §6.
