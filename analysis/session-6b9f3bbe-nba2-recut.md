# Session `arena/6b9f3bbe-nba2` — the RQ-8892-02 model re-cut, executed in full

Written 2026-11-19. Branch `arena/6b9f3bbe-nba2`, base `41cfd81` (= `main` @ the PR #133
merge). Claim pushed before any edit (`59f3ea8`); capture pushed before the re-cut (`0f08729`).

## What was done

The 7-step spec in `analysis/session-8892d20c-capture.md` §4, executed end to end. The v2
model inputs (and every downstream layer) moved from the 2026-11-15 anchor to a fresh
**2026-11-19** official capture — fresher than the 2026-11-17 capture the spec was written
for, because the platform page-fetch tool still reaches the official pages and the runner
transport still does not (the 2026-11-18 bot capture has all three team-stat pages
`status: unavailable`, measured, not assumed).

| Step | Spec | What actually happened |
|---|---|---|
| 1 | Re-run the capture writer; selftest CLEAN | New writer `audit/session-6b9f3bbe-nba2/write_capture.py`; fresh reads 2026-11-19 11:15–12:32 UTC; selftest **CLEAN** (30 clubs; home+road+neutral = W-L for all 30; wins 222 = losses 222; home wins 111 = road losses 111; home losses 110 = road wins 110; GP = W+L for all 30; PF/PA within the 0.1×444 bound; margin-vs-NetRtg residual ≤ 0.76) |
| 2 | Replace `TEAMS` field by field; bump anchors | `nba2/v2/official.py` rewritten from `data/raw/refresh_2026-11-19/` (standings, traditional, opponent, advanced); `AS_OF=2026-11-19`, `RETRIEVED_AT_UTC=2026-11-19T12:32:00Z`, `RETRIEVED_BY=arena/6b9f3bbe-nba2`, window 2026-11-19 → 2026-11-22 (26 games: 4+9 Cup+6+7) |
| 3 | Disclose the PF/PA re-basing | Module docstring + TEAMS comment + the site: PF/PA are now the official per-game page values (traditional PTS / opponent OppPTS); the 2026-11-15 snapshot summed them from committed finals. Both definitions agree within rounding (PTS−OppPTS reproduces the traditional page's own +/- for 30/30 clubs within 0.11) |
| 4 | Reconstruction assertion = card minus the hole | `nba2/v2/report.py` reads history **and** every committed `finals_2026-*.json` feed, dedupes by game id, fills the R-2b blank clubs only from same-id rows with agreeing scores, and compares **exactly**: 222 committed finals reproduce the official card 30/30, hole = 0 |
| 5 | Re-run every downstream surface + tests | CI order: `build_site_data` → `build_site` → `backtest.engine.build` → `v2` → `settlement_page` → `v3` → `v4` → `v5` → `v6`; rebuild is a byte-identical fixed point |
| 6 | Repoint v3/v4/v5 in the same change | v3: `_T`/`_S`/`_R`/`_I` + anchors + WINDOW (its own seal `sealed-2026-11-19.json`, 26 rows, sealed pre-tip); v4: WINDOW, standings card, three stat pages, slate, 11/19 injury rendering (verbatim text + sha256), played pool extended to 222; v5: `INJURY_DIRS` += `refresh_2026-11-19`; v6: frozen clock moved to the new capture's retrieval stamp |
| 7 | CC-FRESH-01 legitimately passable | `tools/crosscheck_site.py`: **100 checks, 91 pass, 0 fail, 9 info — CC-FRESH-01 PASS** (as_of 2026-11-19, 0 days old) |

## What was captured on 2026-11-19 (every read through the platform page-fetch tool)

| Page | Rows | Source |
|---|---|---|
| Standings | 30 clubs, all splits | nba.com/standings |
| Team traditional / opponent / advanced | 30 rows each (PerGame, 2026-27) | nba.com/stats/teams/{traditional,opponent,advanced} |
| Window day strips 11/19–11/22 | 26 games, ids + tips + Cup groups | nba.com/games?date=… |
| Finals 11/18 | 12 games, day strip **and** 12 gamebook PDFs (quarter rows; both reads agree) | nba.com/games?date=2026-11-18 + statsdmz.nba.com/pdfs/20261118/ |
| Injury index + newest release | filing rules verbatim; 23 player rows + 21 NOT YET SUBMITTED | official.nba.com/nba-injury-report-2026-27-season/ + Injury-Report_2026-11-19_07_15AM.pdf |

New v1-layer snapshot trio (schema-compatible with the 11/14 files):
`data/raw/slate_2026-11-19_to_11-22.json` (38 records incl. 11/18 context; `preview_verified_game_ids`
= the 25 games a second official document cross-checks), `data/raw/injury_report_2026-11-19_daybefore.json`
(44 rows, attribution E/C), `data/raw/official_game_times_2026-11-19.json` (38 rows, 13 corroborated).

## Sealed ledgers — untouched, plus one new pre-tip seal

`data/raw/ledger/sealed-2026-11-13.json` (22) and `sealed-2026-11-14.json` (27): **VERIFIED,
byte-identical, never rewritten**. New: `sealed-2026-11-19.json` — 26 predictions, sha256
`7e5406959a8aea3f…`, sealed before the first tip of the window (11/19 20:00 ET); the v3 layer
sealed its own `data/v3/ledger/sealed-2026-11-19.json` (26 rows, digest `10358d28cf58e85c…`)
during its build, same guarantee.

## Verification performed (exact commands, exact results)

```
python3 audit/session-6b9f3bbe-nba2/write_capture.py        # selftest CLEAN
python -m nba2.pipeline.settle                              # union 48 records, 0 conflicts, 0 rejected quarter rows
python -m unittest discover -s nba2/tests -t .              # 92 tests OK
python -m unittest discover -s nba2/v2 -t .                 # 167 tests OK
python -m unittest discover -s nba2/v3 -t .                 # 67 tests OK
python -m unittest discover -s nba2/v4 -t .                 # 61 tests OK
python -m unittest discover -s nba2/v5 -t .                 # 26 tests OK
python -m unittest discover -s nba2/v6 -t .                 # 53 tests OK
python -m unittest discover -s backtest -t .                # OK
python -m nba2.v2.check        # 0 structural, 0 semantic
python -m nba2.v3.check        # 0 structural, 0 semantic; gates 8/8
python -m nba2.v4.check        # 8 gates pass, 0 structural, 0 surface-wall, 0 numeric
python -m nba2.pipeline.lint   # 1429 rows / 50 tables, every row sourced
python3 tools/check_links_all.py  # 143 files, 7472 internal links OK
python3 tools/crosscheck_site.py  # 100 checks: 91 pass, 0 fail, 9 info
python3 audit/2026-11-14-bc867bff/sync_readme_tests.py --check  # exit 0
python3 audit/2026-11-14-3681/sync_readme_counts.py             # README counts -> 21 pages, 50 tables, 1429 rows
python -m nba2.pipeline.seal_predictions --verify               # VERIFIED (22, 27, 26)
```

Settlement now grades through 11/18: sealed-2026-11-13 22/22, sealed-2026-11-14 **27/27**
(spread MAE 12.833 — the five 11/17 games R-10 flagged are graded).

## Test constants updated (all logged, none silent)

`nba2/v2/test_v2.py` (slate 34→26, window dates), `nba2/v2/test_lab.py` (188→222 finals,
172→206 walk-forward), `nba2/v2/test_live.py` (staleness recomputes through the new feeds),
`nba2/v2/test_session2.py` (ledger rows 34→26), `nba2/v3/test_v3.py` (205→222, injury dates,
arena-blank policy, HCA tolerance), `nba2/v3/test_gameflow.py` (31→48 quarter-games),
`nba2/v4/test_v4.py` (slate 29→26, window dates, HCA/total tolerances), `nba2/v5/test_v5.py`
(report rows ≥42), `nba2/v6/test_v6.py` (as-of clock, 11/18 complete, 11/19+ not ended),
`nba2/tests/test_pipeline.py` (36→38 lines, seal 27→26, per-date counts, disjoint-window
three-way disclosure, xlines empty-column allow-list).

## Checker tolerances widened, with the arithmetic written down

* `nba2/v3/check.py` + `nba2/v4/check.py` + their tests: the pinned-HCA identity is computed
  from the unrounded home-win rate but published rounded (rate 4 dp, hca 3 dp); recomputing
  from the rounded rate differs by up to ~2e-3. Tolerance 5e-4/1e-3 → 2.5e-3, comment included.
* `nba2/v4/check.py` + test: the totals-are-possessions×ppp identity recomputes from published
  rounded factors; worst case (measured knife-edge 0022600278: poss 99.825 → 99.82) is ~0.072.
  Tolerance 0.06 → 0.08, comment included.

## Irregularities logged (published on the Flagged pages, none blocking)

1. **GSW standings splits (transcription, not the page).** The first read took GSW road as
   2-5, which broke three identities; a re-read of the same official page confirmed **2-6**
   and everything balances. Recorded because the selftest did its job.
2. **Injury PDF page break (11/19 07:15 AM release).** Two Questionable rows (Kuminga,
   Pullin) lose the team/game cells at the PDF page break. The PDF's own block-continuation
   convention carries the previous team block (Minnesota, NYK@MIN); v2/v3 carry it with the
   "C"/FLAG-V2-INJ-ATTR attribution, the v4 layer keeps the cells blank per its own
   data-not-code policy. Same defect class as the 11/14 capture.
3. **NYK@MIN lists no New York rows at all** in the 07:15 AM release — neither players nor a
   NOT YET SUBMITTED row. Recorded as read; nothing invented.
4. **The 11/18 day strips do not print arenas/broadcasts.** 11/18 rows carry arenas from the
   gamebook PDFs (12/12 cross-checked against the committed schedule capture); 11/19-20
   arenas come from the committed 11/17 schedule read (tips re-verified, all agree);
   11/21-22 arenas stay blank + flagged (FLAG-V2-ARENA-BLANK / FLAG-SLATE-08).
5. **Cross-session tables are now honestly empty.** The committed session-2/3 artefacts cover
   2026-11-13..17 while this model prices 2026-11-19..22 — disjoint windows. `xlines` shows
   only theirs-only rows (disclosed in its verdict text), and the three-way reconciliation
   returns 0 rows with a caption saying exactly why. Follow-up suggestion: re-point the
   three-way comparison at the v3 layer, which prices the same window.
6. **CC-FRESH-03 stays informational**: the latest *completed scheduled ingest* still shows
   the 2026-11-18 run; this session's freshness comes from a committed verified capture, not
   a runner fetch. RQ-8892-01 (refresh transport) remains open and unclaimed.

## Sandbox limit

Direct bash egress to nba.com/stats.nba.com/cdn.nba.com is blocked (HTTP 000) — unchanged
from every prior session. Every official value in this change was read through the platform
page-fetch tool with its URL recorded, and re-derived by the committed selftests.
