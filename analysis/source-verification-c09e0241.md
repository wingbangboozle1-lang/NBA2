# External official-source verification pass — session `arena/c09e0241-nba2` (D2)

**Date:** 2026-11-14, ~01:00–01:20 UTC (2026-11-13 ~20:00–20:20 ET).
**Scope:** live reachability + content spot-check of the official source URLs published on the
site (task A-04 from the independent audit: "link checker skips external reachability").
**Method:** each URL fetched through the platform's page fetch; content compared line-by-line
against the committed snapshots and published claims. Nothing below is inferred — every row
states only what the fetch returned.

## 1. URL reachability results

| # | URL (published as a source on the site) | Reachable | What was verified | Retrieved (UTC) |
|---|---|---|---|---|
| 1 | https://www.nba.com/schedule?date=2026-11-14 | yes | Date headers and per-day counts: Fri Nov 13 = 9 games, **Sat Nov 14 = 5**, Sun Nov 15 = 9, Mon Nov 16 = 8, Tue Nov 17 = 5. All 27 game IDs `0022600231`–`0022600257` (with `0022600256`/`0022600257` out of page order), tip times, arenas and cities read directly from the page. | 2026-11-14 ~01:05 |
| 2 | https://official.nba.com/nba-injury-report-2026-27-season/ | yes | Filing deadlines read verbatim (5 p.m. local day before a game; 1 p.m. local for the second game of a back-to-back; game-day windows 11 a.m.–1 p.m. local, or 8–10 a.m. for tips at or before 5 p.m.). The report index currently lists **November 13** reports only (12:00 a.m. → 8:00 p.m. ET); **no November 14 section exists yet**. | 2026-11-14 ~01:05 |
| 3 | https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_04_15PM.pdf | yes | Header `Injury Report: 11/13/26 04:15 PM`; columns Game Date / Game Time / Matchup / Team / Player Name / Current Status / Reason; **10 of 10 spot-check rows match the committed snapshot** (see §2); document tail shows exactly the 10 `NOT YET SUBMITTED` rows for the five 11/14 matchups that the snapshot records. | 2026-11-14 ~01:08 |
| 4 | https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_01_00PM.pdf | **no — `AccessDenied`** | S3-style `AccessDenied` response. Cross-checked against source #2: the official index has no 11/14 section yet, so the object is **not yet published** (official state), not a sandbox block. This resolves the ambiguity left by sessions 3b88f22e / 2c07c00b: no values were ever taken from this URL, and none can be until the NBA publishes it. | 2026-11-14 ~01:10 |
| 5 | https://www.nba.com/stats/help/faq | yes | Full FAQ read. It contains **no** per-minute-usage correlation and **no** `r ≈ 0.82` / `r ≈ 0.65` figures. The only correlation statement on the page is PIE vs. team winning percentage at **R² = .908**. Reconfirms irregularity I-02: those coefficients were never on this page. | 2026-11-14 ~01:12 |
| 6 | https://www.nba.com/game/nyk-vs-ind-0022600034 | yes | Page title "New York Knicks vs Indiana Pacers Nov 13, 2026 Game Summary"; body shows Friday, November 13th, 2026 7:00 PM ET, East Group B. Matches the committed slate row for game `0022600034`. | 2026-11-14 ~01:14 |

URLs cited 300+ times (the primary injury PDF, #3) and the master slate source (#1) were both
fetched directly. `stats.nba.com` remains blocked (unchanged; recorded by prior sessions).

## 2. Row-level cross-check: live PDF vs committed snapshot

Snapshot: `data/raw/injury_report_2026-11-13.json` — 95 records (85 for 2026-11-13, 10 for
2026-11-14), stamp `2026-11-13 16:15` ET, provenance URL = source #3 above.

Ten rows were re-read from the live PDF and compared (whitespace-normalised; the PDF text
extraction drops a space in "AnkleSprain" once — the snapshot keeps the correct spacing):

| Player (snapshot) | Status | Reason | Team | Live-PDF match |
|---|---|---|---|---|
| Butler III, Jimmy | Out | Injury/Illness - Right ACL Repair / Surgery | Golden State Warriors | yes |
| Curry, Stephen | Out | Injury/Illness - Right Oblique Tear | Golden State Warriors | yes |
| Mobley, Evan | Out | Injury/Illness - Left Great Toe - Sprain | Cleveland Cavaliers | yes |
| Morant, Ja | Out | Injury/Illness - Left Hamstring Strain | Portland Trail Blazers | yes |
| Markkanen, Lauri | Out | Injury/Illness - Right Hand Fracture | Utah Jazz | yes |
| Haliburton, Tyrese | Out | Injury/Illness - Left Hamstring Strain | Indiana Pacers | yes |
| Banchero, Paolo | Out | Injury/Illness - Right High Ankle Sprain | Orlando Magic | yes |
| Porzingis, Kristaps | Out | Not With Team | Golden State Warriors | yes |
| Smart, Marcus | Out | League Suspension | Houston Rockets | yes |
| Antetokounmpo, Giannis | Available | Injury/Illness - Right Wrist Sprain | Miami Heat | yes |

**Result: 10/10 match.** Document tail: the 10 `NOT YET SUBMITTED` rows for
DEN@NOP, DAL@CLE, BKN@MEM, CHI@MIN, DET@MIA (both teams each) match the snapshot's 10
2026-11-14 records exactly, and those five matchups match the official schedule (source #1).

**Not performed (stated, not implied):** a full 95-row re-transcription of the live PDF.
Only the 10 rows above plus the header, columns and document tail were re-read line-by-line.

## 3. Cross-document corroboration observed during the pass

- The five 11/14 matchups in the injury report tail (source #3) equal the five 11/14 games on
  the schedule page (source #1): DEN@NOP, DAL@CLE, DET@MIA, BKN@MEM, CHI@MIN — 5/5 agree.
- Repeat pairings **NYK @ TOR** (Nov 15 `0022600241` and Nov 17 `0022600253`) and
  **POR @ MIN** (Nov 16 `0022600250` and Nov 17 `0022600254`) are present on the official
  schedule itself — confirms FLAG-ANOM-01 is a league-schedule fact, not a capture error.
- Game IDs are not monotonic with page position (Nov 17 lists `0022600257` before
  `0022600256`) — confirms FLAG-SLATE-03 ("never infer a game ID from sequence").

## 4. Irregularities found in this pass

| ID | Finding | Evidence | Disposition |
|---|---|---|---|
| V-01 | `Injury-Report_2026-11-14_01_00PM.pdf` returns `AccessDenied` | live fetch + official index (source #2) has no 11/14 section yet | Not a defect and not a sandbox block: the report is **not yet published**. Published here so future sessions stop re-diagnosing it. No values taken. |
| V-02 | Reconfirms I-02: `nba.com/stats/help/faq` carries no `r ≈ 0.82` / `r ≈ 0.65` | full page read (source #5) | Prior correction stands; no action. |
| V-03 | Cosmetic: `pages/repo-review.html` renders markdown backticks literally inside one evidence cell (`data/site.json` → `repo_review` row 4 stores `` `git show …` vs `https://www.nba.com/schedule` ``) | `data/site.json` line-level read; rendered cell in `pages/repo-review.html` | Cosmetic only — the row's source column is separate and valid. Logged; file is owned by the pipeline/session arena-20c4f2f9, not edited here. |
| V-04 | `data/site.json` anomalies table cites `https://www.nba.com/games?dates=MM/DD/YYYY` as a literal pattern inside prose | cell text (observation about the URL pattern, not a source link) | Not a broken link (plain text in an observation cell). No action. |

## 5. Limitations

- Reachability was tested from the platform page fetch on 2026-11-14 ~01:00 UTC; NBA sources
  can be geo/time dependent, and this is a point-in-time result.
- This pass spot-checks the sources that underpin the highest-traffic rows (slate, injuries,
  the I-02 FAQ). It is **not** a full recertification of all 915 published rows; prior
  sessions' snapshots and the provenance lint remain the record for the rest.
- External non-official links (basketball-reference.com, espn.com) were not fetched in this
  pass; they are third-party by class and flagged as such on the site.
