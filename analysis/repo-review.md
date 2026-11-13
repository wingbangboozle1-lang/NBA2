# Repo Review (line by line)

Reviewed by session `arena-10957a28` on 2026-11-13, at commit `623b4c2` ("Initial
commit") plus this session's additions. Protocol: read every file, verify every
claim against official/trusted sources, flag irregularities, never infer.

## State at review start (commit 623b4c2)

| File | Content | Verdict |
|---|---|---|
| `README.md` | one line: `# NBA2` | nothing to verify; no claims made. Updated by the integration step with project docs and source policy. |
| `.git/` | standard repo metadata | fine |

**Irregularities found at start:** none (empty repo). Noted: no license file, no
`.gitignore`, no data-at-rest policy. Recommendations logged as suggestions
queue items (see [suggestions.md](suggestions.md); license ask is with the owner).

## This session's additions (reviewed line by line at write time)

| Path | What it is | Verification performed |
|---|---|---|
| `COORDINATION.md` | shared task board | n/a (process file) |
| `data/games.csv` | 31 games Nov 13–16 | each row's game_id/time/teams taken from that day's official nba.com games page; `source_url` per row |
| `data/standings-2026-11-13.csv` | 30 team records | cross-checked NBA.com game-page records vs Basketball-Reference ratings page; the two agree on all 30; rows from secondary source say so in the `verified` column |
| `data/team-ratings-2026-11-13.csv` | ORtg/DRtg/MOV + adjusted | copied from Basketball-Reference 2026-27 Team Ratings table; `source_type=trusted secondary` per row |
| `data/injury-report-2026-11-13.csv` | 100+ official status rows | transcribed from the official 5:15 p.m. ET PDF; every row links the PDF |
| `data/player-baselines-2026-11-13.csv` | 27 star baselines + 3 blanks | each stat from NBA.com game-page season-leader widgets; player page links per row; LAL/CHA/TOR left blank + flagged |
| `data/correlation-matrix.csv` | 21 correlation rows | each row links its study/guide; empirical vs industry labeled; no value invented |
| `data/recent-games.csv` | Nov 10–12 results | AP/CBS stories + official Smart release; source_type per row |
| `data/our-lines.csv`, `picks.csv`, `parlays.csv`, `prop-lines.csv`, `luck-table.csv`, `leaderboard.csv` | model outputs | deterministic from the inputs above; each row carries the game's nba.com link |
| `scripts/model.py` | line origination engine | reviewed post-edit; signs re-checked against hand calculations (NYK@IND margin −9.69 → NYK −9.5 ✓) |
| `analysis/strategy/*` | methodology docs | every quantitative claim carries its source link |
| `analysis/executive-summary.md`, `game-flow.md`, `questions.md`, `suggestions.md` | narrative | claims trace to data rows or linked sources; analyst judgments labeled as such |
| `docs/*` (site) | generated dashboard | built from the CSVs; link-check script verifies internal links + per-row sources |

## Flagged irregularities (all published on the site's Flagged page)

1. **Ratings provenance** — team efficiency values are Basketball-Reference
   (trusted secondary), not NBA.com (the sandbox cannot reach NBA stats APIs).
   Every affected row is labeled; swapping to an official feed is suggestion S-1/S-3 context.
2. **Missing baselines** — LAL, CHA, TOR season-leader rows blank by policy.
3. **Key-absence tiering (raised and resolved during the build)** — first model run
   under-charged Haliburton (IND), Banchero (ORL), Edwards (MIN), Morant (POR) and
   Mobley (CLE) because only each team's listed leader had a verified baseline.
   Verified baselines were then pulled (BRef per-game + ESPN + BRef player page),
   added to [`data/player-baselines-2026-11-13.csv`](../data/player-baselines-2026-11-13.csv)
   and the model re-run: NYK −9.5 → −11.0, ORL −7.5 → −4.0, MIN −28.0 → −25.0.
   Residual Q-4 remains for non-star rotation players.
4. **Nov 15–16 injury data** — official reports not yet published at snapshot;
   those picks are `PENDING`.
5. **Correlation values** — 15 of 21 rows are industry ranges, not measurements;
   only 6 rows are empirical. Labeled per row; priors pending own-history (Q-5).
6. **Unverified-but-used secondary facts** (2026-11-12 scores for rest context)
   come from CBS/AP and nba-grid rather than NBA.com; marked `trusted secondary`.

No fabricated values were found or introduced. Where an official value could not
be obtained, cells are blank and flagged rather than filled.
