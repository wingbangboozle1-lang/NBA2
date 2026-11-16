# Independent current-tree audit — `arena/0961c8b9-nba2`

**Audit read:** 2026-11-16, approximately 14:55 UTC.
**Code/data baseline:** `origin/main` at `de4f8c0` (PR #96); this audit branch was rebased onto that commit before validation.
**Scope:** read-only verification of official pages and committed snapshots. The only files changed for this audit are this report and the append-only completion entry in `COORDINATION.md`.

## Executive findings

1. **The rolling schedule window is complete, but its underlying snapshot is dated Nov 15.** The committed 34-game capture is for Nov 15–18. The current NBA schedule shows 9, 8, 5, and 12 games on those dates (34 total). I found no date/game-ID/matchup discrepancy in the checked window. The nine Nov 15 games are now final; their original tip times are supported by the dated capture, not re-observed on the postgame cards.
2. **Standings and team statistics are behind the live official pages by the nine Nov 15 finals.** The committed snapshot has 188 games / 376 team-games; the live standings now sum to 197 games / 394 team-games. Twelve of 30 W–L records still match; 18 differ, exactly the 18 teams in those nine games. Traditional, opponent, and advanced-stat examples also differ.
3. **The injury page does not use the latest captured release.** The published v2 injury page says Nov 15, 06:15 AM ET (101 rows). A later Nov 15, 06:15 PM ET capture (155 rows) is already committed in `data/raw/capture_2026-11-15/`, but is not the release named by that page. At audit time, the official index had advanced to the Nov 16, 09:45 AM ET report. These reports concern different game dates, so I do not claim a player-by-player status diff across them.
4. **Results are unsettled locally after becoming final officially.** The Nov 15 raw result capture has six finals and three pending/null rows; all nine games are final on NBA.com. The three missing finals are HOU–WAS 147–119, ATL–MIL 113–106, and OKC–SAC 125–103. The v2 results page still reports five Nov 14 finals.
5. **Local tests/builds and structural checks pass.** The separate `tools/crosscheck_site.py` exits 1: its two failures are stale README counts and snapshot freshness. No implementation files or data were edited to make checks pass.

## Evidence classes and live publication surfaces

I kept three kinds of evidence separate:

- **Committed captures:** files under `data/raw/capture_2026-11-15/`, `data/raw/results/`, `data/v2/`, and `data/v3/`. These are dated observations, not live reads.
- **Live reads:** NBA pages below fetched with the platform page-fetch tool on Nov 16. The tool returns parsed page/PDF text; no live response or PDF bytes were written into `data/**`.
- **Derived checks:** counts and comparisons rerun from the repository, listed in the validation section. A successful local check establishes consistency of committed inputs, not that those inputs are still current.

The GitHub Pages API reports `build_type=legacy`, source `main /`, status `built`. The live root [`/NBA2/`](https://wingbangboozle1-lang.github.io/NBA2/) renders an older root dashboard marked **as-of 2026-11-14**, built **2026-11-14 10:25 UTC**. The nested [`/site/index.html`](https://wingbangboozle1-lang.github.io/NBA2/site/index.html) renders a v2 dashboard based on 188 league games and Nov 15 inputs; [`/site/slate.html`](https://wingbangboozle1-lang.github.io/NBA2/site/slate.html) is the v3 34-game slate. These are distinct published surfaces, not one live-refresh result. The legacy Pages-source setting is an owner-level decision and was not changed.

## Schedule comparison

**Committed baseline:** `data/raw/capture_2026-11-15/slate_2026-11-15_to_11-18.json` records 34 games, retrieved `2026-11-15T12:00:00Z`, in the date window 2026-11-15 through 2026-11-18. Its own counts are:

| Date | Committed rows | Current official schedule/results page |
|---|---:|---:|
| 2026-11-15 | 9 | 9 games, all shown Final |
| 2026-11-16 | 8 | 8 games |
| 2026-11-17 | 5 | 5 games |
| 2026-11-18 | 12 | 12 games |
| **Total** | **34** | **34** |

The official [schedule](https://www.nba.com/schedule?date=2026-11-16) currently shows the Nov 16–18 dates and game cards; the official [Nov 15 games page](https://www.nba.com/games?date=2026-11-15) shows all nine completed games. The 34-row committed capture and the published v3 slate contain the same date/game-ID/matchup set as those live pages. For the 25 future games, I also checked the displayed ET tip times and venues against the official schedule; no difference was observed. The completed Nov 15 cards confirm the nine game IDs, matchups, venues and results, but do not expose the original tip time in the same way; those times remain supported by the dated Nov 15 capture and its recorded source cross-check, not a new live time read.

## Standings and team-stat comparison

### Standings

`data/v2/teams.json` is explicitly `as_of: 2026-11-15`; its committed integrity block reports 30 clubs, 376 team-games, and 188 games. The corresponding dated official capture is `data/raw/capture_2026-11-15/standings_2026-11-15.json`, retrieved `2026-11-15T12:00:00Z`.

I transcribed the current W–L records from the official [NBA standings page](https://www.nba.com/standings) and compared them with `data/v2/teams.json`. The page totals 197 wins and 197 losses (394 team-games / 197 league games). The full W–L comparison is below; **12 match and 18 are changed**.

| Team | Committed Nov 15 | Live NBA.com Nov 16 |
|---|---:|---:|
| ATL | 7–6 | 8–6 |
| BKN | 3–9 | 3–9 |
| BOS | 10–2 | 11–2 |
| CHA | 4–8 | 4–9 |
| CHI | 3–9 | 3–9 |
| CLE | 7–7 | 7–7 |
| DAL | 7–6 | 7–7 |
| DEN | 7–4 | 7–4 |
| DET | 8–4 | 8–4 |
| GSW | 8–5 | 8–5 |
| HOU | 10–3 | 11–3 |
| IND | 5–8 | 5–9 |
| LAC | 3–8 | 4–8 |
| LAL | 11–2 | 12–2 |
| MEM | 9–4 | 9–4 |
| MIA | 7–6 | 7–6 |
| MIL | 1–12 | 1–13 |
| MIN | 9–4 | 9–4 |
| NOP | 4–10 | 4–10 |
| NYK | 6–6 | 7–6 |
| OKC | 8–5 | 9–5 |
| ORL | 5–7 | 5–7 |
| PHI | 10–3 | 11–3 |
| PHX | 5–6 | 5–7 |
| POR | 9–3 | 9–3 |
| SAC | 1–11 | 1–12 |
| SAS | 11–2 | 12–2 |
| TOR | 5–7 | 5–8 |
| UTA | 1–12 | 1–13 |
| WAS | 4–9 | 4–10 |

The 18 changed clubs are exactly the participants in the nine official Nov 15 finals, so the difference is explained by the later results rather than an unexplained standings arithmetic error. It still makes the published W–L inputs stale for a Nov 16 read.

### Traditional, opponent, and advanced team statistics

The committed values are in `data/v2/teams.json` and `data/raw/capture_2026-11-15/team_stats_2026-11-15.json` (30 rows, retrieved `2026-11-15T12:00:00Z`). I checked representative rows in each current official table. These examples show the age of the data; they are not a full 30-club, every-column transcription.

| Club | Official table fields | Committed capture → live NBA.com |
|---|---|---|
| LAL | Traditional GP / W–L / PTS per game | 13 / 11–2 / 122.2 → 14 / 12–2 / 122.8 |
| LAL | Opponent GP / Opp PTS per game | 13 / 114.2 → 14 / 114.9 |
| LAL | Advanced OffRtg / DefRtg / NetRtg / Pace | 121.6 / 113.6 / 8.0 / 100.50 → 122.1 / 114.0 / 8.0 / 100.64 |
| BOS | Traditional GP / W–L / PTS per game | 12 / 10–2 / 114.2 → 13 / 11–2 / 115.5 |
| BOS | Opponent GP / Opp PTS per game | 12 / 103.1 → 13 / 102.4 |
| BOS | Advanced OffRtg / DefRtg / NetRtg / Pace | 117.4 / 105.6 / 11.7 / 96.62 → 118.9 / 105.1 / 13.9 / 96.53 |
| HOU | Traditional GP / W–L / PTS per game | 13 / 10–3 / 116.2 → 14 / 11–3 / 118.4 |
| HOU | Opponent GP / Opp PTS per game | 13 / 107.4 → 14 / 108.2 |
| HOU | Advanced OffRtg / DefRtg / NetRtg / Pace | 119.3 / 110.2 / 9.1 / 97.42 → 121.2 / 110.7 / 10.5 / 97.68 |

Live sources: NBA.com [traditional](https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular%20Season&PerMode=PerGame), [opponent](https://www.nba.com/stats/teams/opponent?Season=2026-27&SeasonType=Regular%20Season&PerMode=PerGame), and [advanced](https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular%20Season&PerMode=PerGame) team tables. Their current values are season-to-date after Nov 15; they should not be presented as if they were contemporaneous with the Nov 15, 188-game capture. No current stats capture was added in this audit.

## Injury-report comparison

| Evidence | Release / retrieval | Rows or status |
|---|---|---|
| Published v2 page [`site/injuries.html`](https://wingbangboozle1-lang.github.io/NBA2/site/injuries.html) and committed `data/raw/capture_2026-11-15/injury_report_2026-11-15_0615AM.json` | 2026-11-15, 06:15 AM ET; retrieved `2026-11-15T12:05:00Z` | 101 rows; this is the release the page calls current |
| Later committed file `data/raw/capture_2026-11-15/injury_report_2026-11-15_0615PM.json` | 2026-11-15, 06:15 PM ET; retrieved `2026-11-15T23:41:00Z` | 155 rows; not the release named by the current v2 injury page |
| Live official [injury-report index](https://official.nba.com/nba-injury-report-2026-27-season/) and [Nov 16, 09:45 AM ET PDF](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-16_09_45AM.pdf) | Read on 2026-11-16 | Index had releases through 09:45 AM ET; PDF is for Nov 16 games and includes explicit `NOT YET SUBMITTED` rows |

The current report applies to Nov 16, not Nov 15. I therefore do **not** treat the new PDF's players or statuses as a row-level diff against the prior day's report. The finding is about freshness and which committed release the page surfaces. In addition, the committed v3 check at `data/v3/verification.json` says its Nov 15 model used the 06:00 AM ET release even though the newest indexed at retrieval was 06:15 AM ET (`G-F3`, advisory fail; `publishable: true`). The latest scheduled refresh listed by GitHub is run [#43751588814](https://github.com/wingbangboozle1-lang/NBA2/actions/runs/43751588814), concluded failure. Its exact endpoint-level cause remains unverified; I do not infer runner reachability from browser/page-fetch results.

## Official results and settlement

`data/raw/results/results_2026-11-15.json` contains nine rows, retrieved in the `2026-11-16 ~02:05–02:14 UTC` window: six `final` and three `not final at retrieval` rows with null scores. The official [Nov 15 games page](https://www.nba.com/games?date=2026-11-15) now shows all nine final. The six already captured finals agree with that page. The three pending records are:

| Game ID | Matchup | Committed row | Current official final |
|---|---|---|---|
| 0022600242 | HOU @ WAS | pending; scores null | HOU 147–119 WAS ([game](https://www.nba.com/game/hou-vs-was-0022600242)) |
| 0022600243 | ATL @ MIL | pending; scores null | ATL 113–106 MIL ([game](https://www.nba.com/game/atl-vs-mil-0022600243)) |
| 0022600244 | OKC @ SAC | pending; scores null | OKC 125–103 SAC ([game](https://www.nba.com/game/okc-vs-sac-0022600244)) |

The HOU–WAS period scores were also checked against the official [gamebook](https://statsdmz.nba.com/pdfs/20261115/20261115_HOUWAS_book.pdf); I did not claim a gamebook quarter-sum check for the other two in this audit. The pending rows remain null in the repository; these live observations were not written into the capture.

The committed v2 results feed `data/v2/results.json` and the published [`site/official-results.html`](https://wingbangboozle1-lang.github.io/NBA2/site/official-results.html) still report **five** Nov 14 finals, retrieved `2026-11-15T12:00:00Z`. `data/settlement.json` is stamped `2026-11-14T11:46:27+00:00`. This is a dated, internally consistent historical capture, but it does not settle the Nov 15 finals now visible on NBA.com.

## Local verification chain

All commands were run after rebasing onto `de4f8c0`. The v2/v3 builders regenerated deterministically; `git status` remained clean. v2 emitted ResourceWarnings for unclosed JSON files in `nba2/v2/model.py:501` and `nba2/v2/travel.py:62,146`; they did not fail the suite.

| Command | Result |
|---|---|
| `python3 -m unittest discover -s nba2/tests -t . -q` | 79 passed |
| `python3 -m unittest discover -s nba2/v2 -t . -p 'test_*.py' -q` | 146 passed |
| `python3 -m unittest discover -s nba2/v3 -t . -p 'test_*.py' -q` | 67 passed |
| `python3 -m unittest discover -s backtest/tests -t . -q` | 49 passed |
| `python3 -m nba2.v2` / `python3 -m nba2.v2.check` | Built 24 pages; check 0 structural / 0 semantic |
| `python3 -m nba2.v3` / `python3 -m nba2.v3.check` | Built 12 pages; seal 34 rows; 7 pass / 1 advisory fail, `publishable=True`; check 0 structural / 0 semantic |
| `python3 -m nba2.pipeline.lint` | 1,427 rows / 50 tables; every row sourced and every blank explained |
| `python3 tools/verify_backtest.py` | Pass; 183 sourced game rows, 12 pages, 189 internal links; deterministic rebuild |
| `python3 tools/check_links_all.py` | Pass; 127 HTML files, 5,983 internal links, 7,126 external links |
| `python3 tools/crosscheck_site.py` | **Exit 1**; 97 checks: 88 pass, 2 fail, 7 info |
| `git diff --check` | Pass |

The two `crosscheck_site.py` failures are:

- **CC-DOC-01:** README says 1,423 rows vs 1,427 measured, and 70 tests vs 79 in the v1 suite.
- **CC-FRESH-01:** snapshot is two days old; four dates in the published window are already tipped or tipping.

The other seven results are informational, not failures. The README and freshness/output fixes overlap shared files or open refresh/integration work; they were not changed here.

## Handoff and limits

- **No out-of-scope edits:** this audit did not change `data/**`, `site/**`, `nba2/**`, `README.md`, or `.github/workflows/**`. Findings are routed to the integration/refresh owners in the completion entry in `COORDINATION.md`.
- Open PR #95 (`arena/b3914335-nba2`) contains a fresh Nov 16 capture set and v4 rolling-refresh work, but is still open and is not part of the `de4f8c0` main snapshot audited here. Open PRs #70, #72, and #80 overlap refresh workflow/data/v2 paths. Their proposed contents were not treated as merged evidence.
- The official values in this report are live page reads as of Nov 16; the pages can change. The checked-in snapshots remain the reproducible historical record. If a future implementation needs an auditable fresh capture, its owning session should save it with provenance and retrieval time.
- The current GitHub Pages source setting (`legacy main /`) was observed, not modified; changing it could replace the public root and requires an owner decision.
