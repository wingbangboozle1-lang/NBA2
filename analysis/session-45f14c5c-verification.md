# Session `arena/45f14c5c-nba2` — verification report

Date of the official reads: **2026-11-17**. Branch `arena/45f14c5c-nba2`, base `d4fde59`.
Everything below was measured in this session; nothing is carried over as a claim from an
earlier one.

## 1. What this session was for

Three things, in order:

1. Make the nightly job *say why it failed* instead of failing silently (task 45-1) and
   replay the nightly job's exact rolling request from a GitHub runner so the egress
   question stops being guesswork (task 45-2).
2. Settle the 2026-11-16 game day from verified official finals (blocked on one quarter
   contradiction).
3. Re-cut the model inputs to today's official read and rebuild every published tree
   (tasks 45-4 / 45-5).

## 2. The HOU@MIA quarter contradiction — resolved, and it was a reading error

This was the only thing standing between the tree and settling 11/16, so it is recorded in
full.

- **First read** (gamebook chunk 0) showed only the HEAT banner `HEAT 29 33 39 27 128`. No
  HOU period row was visible in that chunk.
- **A later read** appeared to print HOU halftime **31** and Q3 **17**, contradicting the
  `[15, 31, 35, 29]` split already in the results feed.
- **Re-read at the period-block level** settles it: **31 is HOU's second-quarter total, not
  its halftime total, and there is no 17 in any HOU period.** Halftime is 46.

Three independent boundaries inside the same PDF agree, which is what makes this a
measurement rather than a preference:

| boundary | Rockets | HEAT | where |
|---|---|---|---|
| Q1–Q2 | 15, 31 → **46** | 29, 33 → **62** | page printing `SCORE BY PERIOD \| 1 \| 2 \| FINAL` |
| Q3 | **35** | **39** | Q3 box-score total row (60:00) + banner `HEAT 39 39` |
| Q2H cumulative | **64** | **66** | second-half block (120:00) + banner `HEAT 39 27 66` |

Cross-check that closes it: 46 + 64 = 110 and 62 + 66 = 128, matching both finals. The
record in `data/raw/results/results_2026-11-16.json` now carries a `quarter_evidence` field
with those four boundaries and their locations, so a reviewer can re-run the argument from
the PDF alone.

**Why this mattered beyond one game:** it is the third time in this project that a
`sum(quarters) == final` assertion passed while a *split* was wrong. The sums are a weak
check; a cumulative boundary is a strong one. That lesson is now written into the record
rather than into a commit message nobody will read.

## 3. Settlement — the eight 11/16 seals now grade

`nba2/v4/settlement.py` `FINALS_SOURCES` gained the 11/16 feed. Deterministic stamp is
`2026-11-16T23:59:59Z` (the stamp is the end of the latest *graded* game day, never the wall
clock, so a rebuild reproduces it byte for byte).

| measure | before | after |
|---|---|---|
| sealed rows | 83 | 83 |
| graded | 53 | **61** |
| ungraded | 30 | **22** |
| distinct games graded | 14 | **22** |
| settlement hash | `b4286a1d…` | `d7c0da26…` |

### 3.1 Two silent data losses found in the finals union

Both were in `nba2.pipeline.settle.normalise_source`, both caused by the new 11/16 feed
spelling its fields differently from the older feeds, and both were *invisible* — no error,
no warning, just missing data on the published page.

1. The module read only `source_url`. The v4 gamebook feed names its link
   `final_source_url` (game page) and `gamebook_url` (PDF). Result: all eight 11/16 records
   reached the union with an **empty source**, so the results page showed scores with no way
   back to the league.
2. The module read only `away_quarters`/`home_quarters`. The same feed spells the period
   rows `away_q`/`home_q`. Result: the quarters were **dropped**, so the page showed finals
   with no period breakdown even though the gamebook had supplied one.

Fixed with an explicit fallback chain for both, and three regression tests added — including
the rejection path, so a bad period row in the *new* spelling is still refused.

### 3.2 The luck sentence was contradicting its own table

`luck_statement` was a hard-coded literal that still read *"12 correct winners in 14 distinct
games is a hit rate of 0.857 against 0.633 expected"* while the columns beside it said
16 correct in 22 (0.727 vs 0.576). It is now generated from the same rows the table prints:

> 16 correct winners in 22 distinct games is a hit rate of 0.727 against 0.606 expected
> under the seals' own probabilities. The Poisson-binomial tail is 0.0779, so this run is
> inside the noise band …

Read the tail, not the hit rate: **p = 0.078 is not evidence of skill.** The bet surface
continues to publish zero rows, and no stake exists anywhere on the site.

## 4. Official inputs re-cut (task 45-4)

All reads are from official NBA pages on 2026-11-17 through the platform page-fetch tool.
Direct bash egress to nba.com / cdn.nba.com / statsdmz / ak-static returns **HTTP 000** from
this sandbox; that limitation is recorded in every captured document, not worked around.

### 4.1 Standings — and a cross-check that does not rely on the same page

30 clubs transcribed from `nba.com/standings`. Two independent checks:

- **Arithmetic identities.** W = L = 205; home 106-98 and road 98-106, so home wins equal
  road losses exactly; the implied neutral-site count is 1, which the official table prints
  in its own NEUTRAL column.
- **Reconstruction.** Every club's W, L, home and road split was re-derived from the 197
  committed official finals dated on or before 11/15 against the 11/16 capture, then the
  eight 11/16 finals were applied. **30/30 clubs identical**, including all four split
  figures. That compares two independent official surfaces (the standings table and the
  gamebook period rows), not one page against itself.

Measured home-win rate **0.5196** (106 of 204 decided home games), which is the number HCA
is pinned to. Standard error from the games actually observed.

### 4.2 Team stats — three pages, and honest bookkeeping about one of them

- `teams/advanced`, per game, 2026-27: **30/30 rows** read (OffRtg, DefRtg, NetRtg, PACE,
  PIE). GP and W-L on this page agree with the standings table for all 30 clubs.
- `teams/opponent`, per game: **30/30 rows** read (Opp PTS, +/-).
- `teams/traditional`, per game: PTS transcribed for **11 of 30** clubs.

**FLAG-45-01.** The 19 unread traditional rows are not a gap that matters, and the report
says exactly why: the exact points-per-game for every club is *derivable* from the 205
committed official finals, and the 11 transcribed rows agree with those derived values to
within **0.04** — a rounding artefact, since the page displays one decimal. The same holds
on the defensive side: derived points-allowed agrees with the opponent page's Opp PTS to
within **0.05** for all 30 clubs.

So the derived values are used, labelled as derived, and the unread rows are flagged rather
than quietly presented as a transcription. This is the strongest cross-check available
without a stats API: two official pages and one independent derivation all agree to half a
rounding step.

### 4.3 Slate — 30 games, 11/17 → 11/20

Re-read from `nba.com/schedule?date=2026-11-17`: **5 / 12 / 4 / 9** games across the four
dates, with game ids, ET tips, arenas, cities and broadcasters. Emirates NBA Cup group
markers appear on the nine 11/20 fixtures and nowhere else; the rest stay blank and flagged
(FLAG-V2-CUP-BLANK) rather than being inferred.

### 4.4 Injuries — the 11:30 release, transcribed and diffed

`Injury-Report_2026-11-17_10_30AM.pdf`, the newest on the league index at retrieval:
**59 rows** — 33 real player designations and 26 club rows the league had not received.

- POR@MIN and **every** 11/18 block print `NOT YET SUBMITTED`. That is the correct
  pre-deadline state (5 p.m. local the day before), not a capture gap, and it is published
  as such (FLAG-45-03).
- The delta against the 11/16 01:00 PM release was computed with the repo's own matcher
  (`nba2.v4.injury_diff.diff`), keyed on (date, matchup, team, player): 33 added for the
  11/17 filings, 24 for 11/18, 7 club rows resolved into filings, 81 rows gone with the
  11/16 game date. No status changed for a player present in both releases.

### 4.5 A bug in the injury diff: `placeholder_resolved` could only ever be 0

The resolution loop intersected *placeholder* keys with *player* keys. A placeholder's
identity is the sentinel `<placeholder>` in the player slot, so those two sets are disjoint
by construction and the intersection was always empty. The published page therefore showed
**"0 clubs resolved" next to "33 rows added"** — the same event described two contradictory
ways, with the zero looking like a finding.

Fixed: the comparison is now done at club granularity `(date, matchup, team)` and reports
how many player rows replaced each placeholder. The 11/16 09:30 → 13:00 diff consequently
reports **3 clubs resolved** instead of 0.

## 5. Rebuild — every count that had been pinned was hiding something

Reslicing v2 exposed five checks pinned to constants that had quietly become false. Each
pin was concealing a real defect, so each is now derived and additionally asserts it can
never fall below the old floor.

| pinned | was hiding | now |
|---|---|---|
| `load_games()` joins one dated capture by name | the walk-forward **never scored** the 11/15 or 11/16 finals — it was grading an 11-day-old season against 205 verified finals | globs every dated finals source; 205 games |
| `check.semantic()` expects 188 wins, reads a different window's raw file | compared the published slate to the wrong slice; the win total was a remembered number | derived from the module, and cross-checked against an independent recount of every committed final (205 = 205) |
| `live.staleness()` applies only the 11/14 finals | 29 of 30 rows reported `UNEXPLAINED` — a false alarm from the detector, not a bad table | applies every final after the fixture: **30/30 explained, 0 unexplained** |
| tests assert 34 games / 188 games / 172 predictions / 34 ledger rows | a resliced window looked like a missing ledger; a skipped game looked like a passing test | all four derive their expectation from the data |
| prose hard-codes "34-game window (Nov 15 → Nov 18)" and "188 official finals" | the site described a window it no longer published | generated from the module |

The walk-forward coverage test is worth a note: it previously asserted exactly 172
predictions. Every game after the season's opening date should be priced, so the test now
asserts that, and that the *only* legitimate skips are the first games of clubs that had
never appeared. That is the difference between a count and a property.

## 6. Gates, after all of the above

| gate | result |
|---|---|
| v2 build | 24 pages |
| v2 check | **0 structural, 0 semantic** |
| v3 build / check | 12 pages; 7 pass / 1 fail, publishable (the failure is pre-existing and unchanged — verified by stashing this session's work and re-running) |
| v4 build / check | 5 pages; **8 pass / 0 fail**; settlement hash `d7c0da26…`; 0 surface-wall |
| v5 build | 8 / 8 gates, 42 nav injections |
| lint | 1436 rows across 50 tables, every row sourced, every blank explained |
| links | 136 HTML files, 6740 internal links, all OK |
| backtest | 183 games, deterministic, verification passed (12 pages, 183 sourced rows) |
| unit tests | 79 / 146 / 67 / 61 / 26 / 49, plus 11 for `tools.test_surface_reason` — all OK |

## 7. What is still not known

Published as flags, not smoothed over:

- **No market prices.** No licensed odds feed is connected; NBA.com renders odds
  client-side. Without a price there is no edge, no CLV, no ROI and no stake — which is why
  the bet surface is gated and empty. (Q-01, blocking.)
- **Player-level game logs** exist for the captured clubs only; prop pricing needs the
  per-game distribution, not a season mean.
- **11/18 designations** cannot exist until teams file. Blank by policy.
- **The nightly job's failure cause** is now *reported* by the workflow (task 45-1) rather
  than guessed from step names; the runner-side replay (task 45-2) is committed and awaits
  its first scheduled execution.
- **Traditional-page rows 12–30** are unread; flagged, with the derived values published
  instead and the agreement bound stated (FLAG-45-01).

## 8. Reproduction

```bash
python3 -m nba2.pipeline.settle          # rebuilds the finals union from every committed source
python3 -m nba2.v2 && python3 -m nba2.v2.check
python3 -m nba2.settlement_page
python3 -m nba2.v3 && python3 -m nba2.v3.check
python3 -m nba2.v4 && python3 -m nba2.v4.check
python3 -m nba2.v5
python3 -m nba2.pipeline.build_site_data && python3 -m nba2.pipeline.build_site && python3 -m nba2.pipeline.lint
python3 tools/check_links_all.py
python3 -m unittest discover -s nba2/tests -t .   # and nba2/v2, nba2/v3, nba2/v4, nba2/v5, backtest
```

Raw captures for this report: `data/raw/refresh_2026-11-17/` (see `capture_index.json` for
the per-document source URL, row count and cross-check).
