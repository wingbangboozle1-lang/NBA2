# Session `arena/6023d517-nba2` — build repair and line-by-line verification (2026-11-19)

Everything below was run in this session against this working tree, or read from the official
URL named beside it. Where something could not be confirmed it says so and is flagged; nothing
is inferred.

## 1. The defect the session found before doing anything else

`python -m nba2.v6` — the last step of the Pages build — **exited 1** on the committed base
`a5380e1`, with `HARD GATE FAILURE G-V6-8`. Reproduced twice. Consequence: the published tree
could not be rebuilt from its own committed inputs, and `pages.yml` would have failed the
`site differs from rebuild` step.

| Measure | Before | After | Why it changed |
|---|---|---|---|
| Game rows with no official URL | 14 of 67 | **0 of 67** | the URL was in the file, under `final_source_url` |
| Rows printing the literal `None @ None` | 14 | **0** | matchup built from whichever artefact has both clubs |
| As-of clock | typed literal `2026-11-17` | **derived** from the newest committed capture | the literal had aged past a capture |
| `2026-11-17` status | `not ended` (wrong: 5 finals on disk) | `incomplete` (5 finals, 0 graded) | status now follows the evidence |

Evidence for the root cause, not an assumption: in `data/raw/finals_2026-11-14.json` and
`finals_2026-11-15.json` every record carries the key `final_source_url` and the clubs under
`away_team`/`home_team`; `nba2/v6/results_coverage.py` read only `source_url`/`official_source`
and `away`/`home`. Confirmed by reading both files, not inferred from the gate message.

## 2. What was verified against official sources this session

| # | Claim | Source read | Result |
|---|---|---|---|
| V1 | 12 finals on 2026-11-18, with scores | <https://www.nba.com/games?date=2026-11-18> (via each `nba.com/game/<id>` page) | 12/12 match the snapshot in `nba2/v7/official.py` |
| V2 | 4 games on 2026-11-19, ids, tips, clubs | <https://www.nba.com/games?date=2026-11-19> | 4/4 match, tips included |
| V3 | 9 games on 2026-11-20 incl. Cup group labels | <https://www.nba.com/games?date=2026-11-20> | 6/6 games that had scrolled into the fetched chunk match, including group labels |
| V4 | Standings W-L for 15 clubs (both conferences) | <https://www.nba.com/standings> | 15/15 match |
| V5 | Advanced team stats: OffRtg, DefRtg, NetRtg, PACE for 30 clubs | <https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season> | 30/30 transcribed; `NetRtg = OffRtg − DefRtg` holds on all 30 to ±0.15 |
| V6 | Traditional PTS per game, 30 clubs | <https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season> | 30/30; `PTS − OppPTS = +/−` holds on all 30 to ±0.20 |
| V7 | Opponent PTS per game, 30 clubs | <https://www.nba.com/stats/teams/opponent?Season=2026-27&SeasonType=Regular+Season> | 30/30 |
| V8 | Every club's W equals its wins in the committed finals | NBA.com game pages already in `data/raw/**` | 30/30 reconcile over 222 games |
| V9 | Home-win rate and margin sd | the same 210 committed finals | 0.5143 and 16.81 |

The two identities in V5/V6 and the reconciliation in V8 are encoded as tests
(`nba2/v7/test_v7.py`), so a future transcription slip fails the build rather than the reader.

## 3. Irregularities flagged for review (none blocks the merge)

| ID | Irregularity | Evidence | Disposition |
|---|---|---|---|
| F-V7-AVAIL | The 2026-11-19 official injury report was **not read** in this session, so the availability column on the slate is empty | deliberate: `INJURY_REPORT_READ = False` | published as a blank with the reason on every row and blocked as gate G-V7-8 |
| F-V7-CLOCK | The league's own pages disagree by one date: `/stats/teams/*` runs through 2026-11-17, `/standings` through 2026-11-18 | measured on Utah (stats GP 15 vs standings 3-13 = 16 games; UTA beat LAL on 11/18) | both clocks published; the gap column is on the skill page |
| F-V7-TRANSPORT | The transcription cannot be reproduced from this sandbox (no TLS egress) or from a GitHub runner (`stats.nba.com` times out, `cdn.nba.com` 403) | `curl` returns 000; `data/raw/egress_probe.json` | recorded in the module docstring and on the methodology page; the three identities are the counterweight |
| F-V7-MARKET | No market price exists, so no edge is computable and every stake is 0.00 | gate G-V7-6 BLOCKED | published; strategy S-10 is written and blocked, not deleted |
| F-V7-PROPS | The largest committed per-player log is **3 games**; a ±5-point line needs ~15 | `data/v5/player_logs_union.json` (421 players, max 3 games) | props page shows the arithmetic instead of a number |
| F-V7-PREREG | Pre-registration hashes live in the same commit as the strategy, so they are tamper-*evident* only against later edits, not against a rewrite of the commit | by construction | suggestion SG-V7-04: move the hash to a git tag |
| F-V7-PAGES | GitHub Pages `build_type` is `legacy`, source `main /`, so `/NBA2/` serves the root pointer rather than the uploaded `site/` artefact | `gh api repos/.../pages` returns `{"build_type":"legacy","source":{"branch":"main","path":"/"}}` | pre-existing; needs one owner action in Settings (suggestion SG-V7-12) |
| F-V7-LEAK | The first draft of the v7 model cut its ratings from the 11/19 pages and "tested" October games with them | measured: accuracy 34%, log-loss 1.2368 | **fixed before publication**; the point-in-time test now guards it |

## 4. Verification run in this session

```
python -m nba2.v7                                 -> 5 pages, 7/7 structural checks, 6/10 gates PASS
python -m nba2.v2.check                           -> OK — 0 structural, 0 semantic
python -m nba2.v3.check                           -> 8 gates pass / 0 fail
python -m nba2.v4.check                           -> 8 gates pass / 0 fail; publishable=True
python -m nba2.pipeline.lint                      -> LINT OK — 1436 rows across 50 tables
python -m unittest discover -s nba2/tests -t .    -> 88 tests OK
python -m unittest discover -s nba2/v2 -t ...     -> 167 tests OK
python -m unittest discover -s nba2/v3 -t ...     -> 67 tests OK
python -m unittest discover -s nba2/v4 -t ...     -> 61 tests OK
python -m unittest discover -s nba2/v5 -t ...     -> 26 tests OK
python -m unittest discover -s nba2/v6 -t ...     -> 51 tests OK
python -m unittest discover -s nba2/v7 -t ...     -> 27 tests OK
rebuild twice, diff -rq site                    -> byte-identical
```

Total: **487 tests**, three checkers, one linter, and a deterministic rebuild.

## 5. What I could not verify, and will not claim

- The 2026-11-19 injury report content (not read).
- The 11/21 slate against the live page (the 11/20 fetch was truncated before it reached 11/21;
  the 11/21 rows come from the snapshot, and each row links its game page so a reader can check).
- Any market price, closing line or edge.
- Arena coordinates: third-party, already flagged FLAG-V2-ARENA-COORDS before this session; v7
  does not publish travel distance.
