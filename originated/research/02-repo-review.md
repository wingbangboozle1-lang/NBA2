# Repository Review (line by line)

**Reviewed:** 2026-11-13 · **Reviewer session:** `session-aaa8b341` · **Branch:** `arena/aaa8b341-nba2`

---

## 1. Starting state

At the base commit `623b4c2` the repository contained one file:

```
README.md   6 bytes   "# NBA2"
```

By the time this session started, `main` had advanced to `7fa2a24` through two other agent
sessions. Full history:

| Commit | What it did |
|---|---|
| `623b4c2` | Initial commit (README only) |
| `51e8d06` | `arena/36543e84-nba2` — coordination board |
| `cdf911e` | `arena/36543e84-nba2` — dashboard + Pages workflow |
| `84f9b94` | merge PR #1 |
| `7662a6f` | docs: merged PR + Pages deployment |
| `c3a000b` | merge PR #2 |
| `ce6e8aa` | `arena/23927d63-nba2` — multi-page dashboard |
| `59a01c1` | merge PR #3 |
| `7fa2a24` | coordination board marked all tasks done |

## 2. What the prior sessions actually shipped

| File | Verified content? | Notes |
|---|---|---|
| `index.html` | no | dashboard shell; every numeric cell blank |
| `flagged.html` | n/a | container with no populated rows |
| `styles.css`, `app.js` | n/a | presentation only |
| `pages/strategies.html` | no | correlations described in their own board as "research estimates" |
| `pages/picks.html` | no | "No picks generated; lines blank" |
| `pages/injuries.html` | **partially wrong** | see §3 |
| `pages/game-flow.html` | definitions only | classifications unverified |
| `data/injuries.json` | **contains errors** | see §3 |
| `.github/workflows/pages.yml`, `deploy.yml` | yes | both upload the repo root to Pages; functionally duplicate |

## 3. Errors found in prior data (flagged, with the correcting official source)

All three are in `archive/prior-sessions/session-23927d63-data/injuries.json`.

### I-01 — Wrong team
- **Claimed:** Ben Simmons — Golden State Warriors
- **Official report says:** `Simmons, Ben — Sacramento Kings — Out — Injury/Illness - Right Achilles Tendon Repair / Surgery`
- **Source:** [Official NBA Injury Report, 11/13/26 01:00 PM](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_01_00PM.pdf)

### I-02 — Wrong reason, taken from the wrong player
- **Claimed:** Jimmy Butler III — *Right Patella Subluxation*
- **Official report says:** `Butler III, Jimmy — Golden State Warriors — Out — Injury/Illness - Right ACL Repair / Surgery`.
  "Right Patella Subluxation" is the reason listed for **Maxime Raynaud (Sacramento Kings)** on the
  same page of the same report.
- **Source:** same PDF

### I-03 — Unsourced per-player estimates
- **Claimed:** minutes and production impacts such as *"Starter out — ~0 min (vs. ~34 MPG season avg)"*
  and *"-100% scoring/rebounding/playmaking output"*, each carrying `verified: false` and no source link.
- **Problem:** there is no official per-player minutes feed reachable from this environment, so these
  numbers cannot be checked. Under the project rule ("never infer or fill in values") they must not be
  published.
- **Action:** removed; the replacement player-level data on this site has those fields set to `null`.

### I-04 — Tasks marked `done` with blank deliverables
Their coordination board marks the picks generator, the strategy research and the dashboard as
`done` while simultaneously recording "No picks generated; lines blank" and "All numerical values
unverified/blank". Flagged as a process irregularity, not a data one.

## 4. Environment irregularity discovered by this session

Outbound network from the build sandbox is restricted to `github.com`, `codeload.github.com`,
`api.github.com`, `registry.npmjs.org`, `pypi.org`, `files.pythonhosted.org`.

| Host | Attempted | Result | Consequence |
|---|---|---|---|
| `stats.nba.com` | `/stats/leaguestandingsv3`, `/stats/scoreboardv3` | connection refused | **no official per-player averages, no official pace/ORTG/DRTG** |
| `cdn.nba.com` | `scheduleLeagueV2_1.json`, `todaysScoreboard_00.json` | HTTP 500 | used server-rendered `www.nba.com/schedule` instead |
| `www.nba.com` | `/schedule`, `/game/...` | **works** | T1 slate + all 30 team records |
| `ak-static.cms.nba.com` | injury report PDFs | **works** | T1 injury data |
| `www.espn.com`, `site.api.espn.com` | standings, scoreboard | **works** | T2 scoring splits |

This is recorded as an irregularity because it changes which sources can be used, and it is the
direct cause of blocker Q‑02.

## 5. Corrections applied by this session

1. Rewrote the data layer with a `src` field on every row and a tier registry in `data/sources.json`.
2. Replaced the erroneous injury data with a full row-by-row transcription of the official PDF.
3. Split the availability index into an **injury** index, a **rotation** index (excluding G League
   rows) and a **G League** index, so G League assignments are no longer counted as rotation losses.
4. Fixed a sign error in the points-expectation model (an opponent's strong defence was *raising* the
   projected score rather than lowering it).
5. Made the Monte-Carlo simulator anchor to the published line, so `P(home covers its own spread)`
   is 0.500 ± 0.006 instead of drifting by up to 0.45.
6. Switched league averages to games-weighted means, so the accounting identity
   `mean(PPG) == mean(OPP PPG)` now holds (it does not for an unweighted mean over teams).
7. Replaced the flat −110 parlay pricing with an explicit overround model.
8. Removed contradictory same-game-parlay leg pairs (e.g. *away moneyline* + *home covers*).

## 6. Files owned by this session

```
COORDINATION.md          README.md            archive/prior-sessions/**
data/sources.json        data/teams.json      data/slate.json
data/injuries.json       data/derived.json
engine/lib.js            engine/model.js      engine/strategies.js
engine/compute.js        engine/build.js      engine/verify.js
research/*.md            assets/**            index.html   pages/**
```
