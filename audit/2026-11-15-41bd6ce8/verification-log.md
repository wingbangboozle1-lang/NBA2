# Verification log — session `arena/41bd6ce8-nba2` (2026-11-15)

Scope: the per-player capture in `data/raw/capture_2026-11-15-41bd6ce8/`, the injury
release of the same evening, and the gates that make the capture publishable. (The three
pages this session first published were withdrawn after session `arena/f8f8f2b8-nba2`
published the same questions from the official gamebooks — see
`analysis/session-41bd6ce8-player-logs.md` § Reconciliation.)

Method: every value below was read from the official page named in the Source column on
2026-11-15 through the platform page-fetch tool. Nothing is inferred, modelled, or
copied from another file. Where a value could not be read, the cell is blank on the page
and the reason is listed here.

## 1. Player game logs — three identities per player

| Player | Club | id | Rows captured | Rows the page declares | mean PTS / official PPG | mean REB / official RPG | mean AST / official APG | max MIN | date range | Verdict | Source |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Curry, Stephen | GSW | 201939 | 10 | 10 | 27.8 / 27.8 | 3.7 / 3.7 | 3.9 / 3.9 | 35.75 | 2026-10-21 → 2026-11-11 | PASS | [official](https://www.nba.com/stats/player/201939/boxscores-traditional?Season=2026-27&SeasonType=Regular+Season) |
| Santos, Gui | GSW | 1630611 | 10 | 10 | 5.6 / 5.6 | 3.9 / 3.9 | 1.4 / 1.4 | 27.68 | 2026-10-21 → 2026-11-13 | PASS | [official](https://www.nba.com/stats/player/1630611/boxscores-traditional?Season=2026-27&SeasonType=Regular+Season) |
| Williams, Brandon | GSW | 1630314 | 10 | 10 | 10.4 / 10.4 | 2.1 / 2.1 | 2.3 / 2.3 | 24.88 | 2026-10-21 → 2026-11-09 | PASS | [official](https://www.nba.com/stats/player/1630314/boxscores-traditional?Season=2026-27&SeasonType=Regular+Season) |
| Murphy III, Trey | NOP | 1630530 | 9 | 9 | 15.6 / 15.6 | 4.8 / 4.8 | 3.6 / 3.6 | 39.78 | 2026-10-21 → 2026-11-08 | PASS | [official](https://www.nba.com/stats/player/1630530/boxscores-traditional?Season=2026-27&SeasonType=Regular+Season) |
| Murray, Dejounte | NOP | 1627749 | 9 | 9 | 13.4 / 13.4 | 4.6 / 4.6 | 4.4 / 4.4 | 44.50 | 2026-10-21 → 2026-11-11 | PASS | [official](https://www.nba.com/stats/player/1627749/boxscores-traditional?Season=2026-27&SeasonType=Regular+Season) |

5 players / 48 official player-games.
Every row's `game_id` is an official game id (`00226…`, 10 digits) and links to
`https://www.nba.com/game/<id>/`.

## 2. Players on the release whose log was not captured

Recorded with the reason; no rows published, nothing substituted.

| Player | Club | Status | Reason it is blank | Source |
|---|---|---|---|---|
| Butler III, Jimmy | GSW | Out | the page renders the player header (PPG 20.0, RPG 5.6, APG 4.9) and then prints 'No data available' where the game-log table should be; a second request without the query string behaves identically | [official](https://www.nba.com/stats/player/202710/boxscores-traditional?Season=2026-27&SeasonType=Regular+Season) |
| Moody, Moses | GSW | Out | same rendering as Butler III: header present (PPG 12.1, RPG 3.3, APG 1.6), table prints 'No data available' | [official](https://www.nba.com/stats/player/1630541/boxscores-traditional?Season=2026-27&SeasonType=Regular+Season) |

24 further designated players were outside this session's capture budget (two clubs captured in full); they are listed on the page with the same wording and no numbers.


## 3. Rosters — official player ids

| Club | Players on the official roster | Club page |
|---|---|---|
| GSW | 18 | [official](https://www.nba.com/team/1610612744/warriors) |
| NOP | 18 | [official](https://www.nba.com/team/1610612740/pelicans) |

Every id comes from the `/player/{id}/` link in the club's own roster table; none was constructed.


## 4. Injury release (06:15 PM ET) — what was checked

The release transcribed by this session was **withdrawn**: session `arena/f8f8f2b8-nba2`
transcribed the same PDF (155 rows) and merged it first, so the repository keeps one
transcription (`data/raw/capture_2026-11-15/injury_report_2026-11-15_0615PM.json`) and
`nba2/v4/official.py` resolves whatever newest capture holds one. The counts below are
that file's.

| Check | Measurement | Source |
|---|---|---|
| rows transcribed | 111 | [PDF](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15PM.pdf) |
| rows naming a player | 105 | |
| club slots marked NOT YET SUBMITTED | 6 | |
| games covered | 17 | |
| G League rows excluded from minutes-at-risk | 39 | |

The prior release (06:15 AM ET, `data/raw/capture_2026-11-15/injury_report_2026-11-15_0615AM.json`) is diffed row by row on `injury-diff.html`; a player whose status moved between the two is printed with both values and the direction.


## 5. Endpoints that do not work

Measured this session so the next one does not spend its budget rediscovering them.

| Endpoint | Result |
|---|---|
| `https://cdn.nba.com/static/json/liveData/boxscore/boxscore_0022600231.json` | HTTP 500 on every request — the JSON endpoints the site itself calls are not reachable from the build environment |
| `https://www.nba.com/stats/players/traditional?Season=2026-27&SeasonType=Regular+Season&PerMode=Per+Game` | page renders but the table prints 'No data available' — it is built by a second request the reader cannot see, so there is no one-shot league-wide player table |
| `https://www.nba.com/stats/team/1610612755/traditional?Season=2026-27&SeasonType=Regular+Season` | reachable, but it publishes club splits (overall / home / road / wins / losses), not per-player rows — S-51's 'per-club season table' is not this page |
| `https://www.nba.com/` | blocked in this environment (TLS connect fails); captures are possible only through the platform page-fetch tool, which is why coverage scales with pages read |
