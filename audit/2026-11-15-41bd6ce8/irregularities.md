# Irregularities — session `arena/41bd6ce8-nba2` (2026-11-15)

Everything here is published on the site's **Flagged for review** pages as well; none of it blocks a merge, and none of it was filled in with a substitute value.

| ID | Area | Finding | Source | What we did |
|---|---|---|---|---|
| F-41B-01 (same document as `arena/f8f8f2b8-nba2`'s I-F8F PDF quirks) | injury report print defect | 'Sexton, Collin' and 'Thiero, Adou' are printed inside the LAL@PHX block; both are Utah Jazz players. Reproduced as printed, team cell left blank, attributed_team=true. | [source](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15PM.pdf) | reproduced exactly as printed; never silently corrected |
| F-41B-02 | injury report print defect | 'Penda, Noah' is printed twice: once for Orlando Magic (Out, hamstring) and once under Boston Celtics with the status text 'NOT YET SUBMITTED'. Reproduced as printed. | [source](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15PM.pdf) | reproduced exactly as printed; never silently corrected |
| F-41B-03 | injury filing coverage | Six club-slots on the 11/16 slate are 'NOT YET SUBMITTED' (WAS vs MEM, HOU at MIA, PHI at BKN, PHX at DEN, DEN vs PHX), so those clubs are priced availability-blind. | [source](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15PM.pdf) | reproduced exactly as printed; never silently corrected |
| F-41B-04 | player game-log capture | Two of the seven GSW players on the release (Butler III, Moody) render the player header but print 'No data available' in place of the game-log table; no rows are published for them rather than substituting the header rates. | [source](https://www.nba.com/stats/player/202710/boxscores-traditional?Season=2026-27&SeasonType=Regular+Season) | published on the page next to the empty cell |
| F-41B-05 | player game-log coverage | 5 of 31 Out/Questionable players on the 2026-11-16 slate have a captured game log. Minutes-at-risk totals are therefore lower bounds for every club and are labelled as such; they are never scaled up to a full-slate estimate. | [source](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15PM.pdf) | published on the page next to the empty cell |

## Overlap with session `arena/f8f8f2b8-nba2`

Both sessions captured the same evening's official injury release and per-player logs
on 2026-11-15. Their capture is the better one for the shared question (193 rows for
18 clubs, transcribed from the official gamebook PDFs, versus this session's 48 rows
for 5 players), and it merged first. This session therefore withdrew its three pages
(`player-logs.html`, `rotation-impact.html`, `injury-diff.html`) and its duplicate
transcription of the release, and kept what is unique: the gated per-player capture,
the capture-as-code that extends it, and the archive step for the primary documents.

## Carried, not re-checked this session

| ID | Area | Status |
|---|---|---|
| F-033 / FLAG-PAGES-01 | GitHub Pages source is `main /` with `build_type: legacy`, so the tree Pages serves is the v1 `pages/` directory, not the v2/v3/v4 `site/` tree | owned by `arena/56b96bf0-nba2`; this session publishes to both so the link is never dangling |
| G6 | no licensed price feed, so no pick is stakable | unchanged |
| F-043 | the nightly ingest has not yet had a first successful run in CI | the new `player-capture` workflow is written to the same fail-closed standard and reports unreachable upstreams instead of inventing rows |

## New this session, by construction

| ID | Area | Note |
|---|---|---|
| F-41B-06 | unattended capture | `nba2/v4/capture.py` was written against the page structure observed on 2026-11-15 and tested against fixtures, not live pages. Its first scheduled run is supervised: every value is re-gated before it is written, so a parse that drifts produces a recorded capture failure, never a wrong number. |
