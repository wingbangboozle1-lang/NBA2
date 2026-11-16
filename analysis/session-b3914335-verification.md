# Session `arena/b3914335-nba2` — verification record

Scope: B1–B8 as claimed in `COORDINATION.md` at commit `934c855`.
Everything below was established **in this session**, from the listed URL, and is reproducible
by running the command in the last column.

Method note, because it matters for manual review: this sandbox has **no outbound network from
the shell** (`curl` to nba.com and to the GitHub Pages host returns `000`). Every official page
was read through the page-fetch tool and transcribed into `nba2/v4/capture.py` alongside its
URL and retrieval timestamp. `nba2/v4/write_capture.py` then re-materialises the snapshot from
that transcription, byte-identically, so the transcription is auditable as a diff rather than
hidden in a commit.

---

## 1. Official sources read

| # | Source | URL | What was taken | Stored in |
|---|---|---|---|---|
| 1 | Schedule | `https://www.nba.com/schedule?date=2026-11-16` | 29 games across 11/16–11/19, each with game id, tip time and game-page URL | `capture.py#SLATE` → `data/raw/refresh_2026-11-16/slate_2026-11-16_to_11-19.json` |
| 2 | Standings | `https://www.nba.com/standings` | 30 clubs, full W/L/home/road/div/conf splits | `#pages.standings` → `standings_2026-11-16.json` |
| 3 | Team advanced | `https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame` | 30 rows OffRtg, DefRtg, PACE, POSS | `team_stats_adv_2026-11-16.json` |
| 4 | Team opponent | `https://www.nba.com/stats/teams/opponent?...PerMode=PerGame` | 30 rows OppPTS | `team_stats_opponent_2026-11-16.json` |
| 5 | Team traditional | `https://www.nba.com/stats/teams/traditional?...PerMode=PerGame` | 30 rows PTS, FGM/FGA, 3PM, FTM, FT% | `team_stats_traditional_2026-11-16.json` |
| 6 | Gamebooks | `https://statsdmz.nba.com/pdfs/20261115/20261115_{INDPHI,HOUWAS,ATLMIL,OKCSAC}_book.pdf` | period-by-period splits for 4 of the 9 finals | `#pages.finals_2026_11_15` → `data/raw/refresh_2026-11-15/results_2026-11-15.json` |
| 7 | Injury report | `https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-16_09_15AM.pdf` | 70 player rows with status and reason | `#INJURY_RELEASES[0]` → `injury_transcript_20261116_0915AM.json` |
| 8 | Injury index | `https://official.nba.com/nba-injury-report-2026-27-season/` | filing rules, filename pattern, newest listed release | `#SOURCE_PAGES["injury_index"]` |
| 9 | Injury report (2nd) | `.../Injury-Report_2026-11-16_09_30AM.pdf` | identical row-for-row to #7 | `injury_transcript_20261116_0930AM.json`, flagged F-V4-09 |
| 10 | Prior finals capture | `data/raw/capture_2026-11-15/results_2026-11-14.json` | 5 finals from 11/14 that were committed but not in any v4 pool | now in the history pool |
| 11 | Live v3 site | `https://wingbangboozle1-lang.github.io/NBA2/slate.html` | what the published site currently claims, for the disagree-with-published check | — |

---

## 2. Line-by-line checks against the official pages

Each row is a claim the site now makes, the check that produced it, and the command that
reproduces it. `python3 -m nba2.v4.selftest`-equivalent is `python3 -c "from nba2.v4 import capture as C; print(C.selftest())"`, which prints `[]` when every check below passes.

| Check | Claim | Independence | Result |
|---|---|---|---|
| Points identity | `2*FGM + 3PM + FTM = PTS` on all 30 traditional rows | Self-checking: a single mis-transcribed digit breaks it | **30/30 within rounding** |
| Plus/minus sign | `+/-` is the negation of the opponent's `+/-` | Self-checking across 30 rows | **30/30** |
| Team points balance | Σ points-for = Σ points-against across 30 clubs | Self-checking | **Δ 1.9**, bound ±39.4 (from 30 clubs × 0.65 rounding) |
| Cross-page PTS | Traditional `PTS` vs advanced-derived points | Two independent pages | **max Δ 0.069** |
| OffRtg × POSS | `OffRtg/100 × POSS ≈ PTS` | Two columns of the same page | **max Δ 0.069** |
| Standings balance | ΣW = ΣL, home W = road L | Self-checking | **197 = 197**, home 102-94 / road 94-102 |
| Standings vs finals | League games implied by standings = finals transcribed | Two independent pages | **197 = 197** |
| Slate ids | 29 unique ids, all `002...`, 10 chars | Format check | **29/29** |
| Quarter rows | Each transcribed period row sums to its final | Self-checking | **17 of 18 rows sum**; DAN@BOS away row absent on the page → left `null`, flagged |
| Injury rows | 70 rows, statuses verbatim, no inferred status | Re-read against the PDF | **70/70**, 19 placeholder rows carry `""` not a status |
| Injury release pair | 09:15 and 09:30 are the same document | Row-for-row comparison | **identical**, declared F-V4-09 rather than double-counted |

### Irregularities found and how each is published

| ID | Irregularity | Where it is visible |
|---|---|---|
| F-V4-01 | No injury **PDF bytes** can be stored (no shell egress); the release is stored as a transcription with a 64-hex content hash | `v4-injuries.html`, both releases |
| F-V4-02 | `binary_stored` is `false` for every release, with the reason | same |
| F-V4-03 | The slate's tip times are the schedule's `time_et`, which the source page states without a timezone suffix | `projection.html` column header |
| F-V4-04 | No licensed odds feed, so **no market price anywhere**: no edge, no stake, no CLV | `bet.html` refusal table + all 29 refusals |
| F-V4-05 | Continuation rows in the PDF lose date/time/team on page breaks | `v4-injuries.html` layout notes |
| F-V4-06 | 6 GSW@NOP rows lose their status column in extraction → status left **blank**, never back-filled | `projection.html` availability cell, flagged `F-V4-06` |
| F-V4-07 | `POR@MIN` appears under two dates; the diff key is `(date, matchup, team, player)` | `v4-injuries.html` |
| F-V4-08 | Production impact (minutes/usage delta) is **not** published: the report states status, not minutes, and no matched before/after game pair exists | `projection.html`, availability section |
| F-V4-09 | The 09:30 release is byte-identical to 09:15 in content; declared `identical_to`, not counted as a change | `v4-injuries.html` |

---

## 3. The two headline numbers, and why they are the ones published

### Home-court advantage: pinned, not fitted

The brief forbids a free fit. The rule implemented is
`hca = margin_sd × Φ⁻¹(measured home-win rate)`, where the rate and the sd come from official
finals only.

```
history pool   : 197 games (matches the standings-implied 197)
non-neutral    : n = 196
home wins      : 102  ->  rate 0.5204
margin sd      : 16.987
hca_points     : 0.869   (= 16.987 * Phi^-1(0.5204))
```

Reproduce: `python3 -c "from nba2.v4 import model as M; r=M.build(); print(r['home_court'])"`.

**A correction worth recording.** The pool originally contained 192 games, because
`played_games()` only read the 11/15 capture. The 5 official 11/14 finals existed in the
committed `results_2026-11-14.json` but in no v4 pool, so HCA was computed on n=191. Adding
them moved the rate from 0.5183 to 0.5204 and HCA from 0.780 to 0.869. The cause was a
missing input, not a modelling choice — which is exactly the failure the "197 vs 192" check
against standings is there to catch. It now catches it.

### Correlation: measured, with its uncertainty

```
rho   = -0.038   (same-game total vs margin)
n     = 196
CI95  = [-0.177, 0.103]
```

The interval straddles zero, so the site must not claim a correlation it cannot distinguish
from noise. Parlays price with the measured rho **and** print the naive product beside it, so
the reader sees how much the assumption is doing.

### The 9/9 result: published, and disarmed

```
graded        : 9 of 34 sealed (25 ungraded, each with a stated reason)
winners       : 9 of 9
log-loss      : 0.2804   (coin flip 0.6931)
p_observed_run_under_model : 0.0802
expected hits under model  : 6.87
```

9/9 at the model's own probabilities is a ~8% event — unusual, not impossible, and nowhere
near the evidence needed to call a strategy skilled. The settlement page prints
`p_observed_run_under_model` **before** the hit rate for this reason, and the requirement
register keeps R-010 partial rather than letting a 9-game run close it.

Reproduce: `python3 -m nba2.v4.settlement`.

---

## 4. What the gates actually enforce

`python3 -m nba2.v4` runs, in order: capture → injury diff → **pre-render gates** → render →
settle → **post-render check**. A pre-render gate failure exits before anything is written.

| Gate | Enforces |
|---|---|
| G-V4-1 | 9 finals, every transcribed quarter row sums to its final |
| G-V4-2 | 30 clubs, ΣW = ΣL, home W = road L |
| G-V4-3 | Three team-stat pages complete (30/30/30) and the points identity holds |
| G-V4-4 | Slate unique, well-formed, sourced, window edges exact |
| G-V4-5 | Newest injury release stamped revision + retrieval + index check |
| G-V4-6 | **Provenance**: every captured row carries a source URL |
| G-V4-7 | Settlement re-hashes and the seal still verifies |
| G-V4-8 | **Surface wall**: no bet field on the projection HTML, no unpriced PUBLISHED row |

Tests for the gates are in `nba2/v4/test_v4.py`. Six of them deliberately break an input and
assert the corresponding gate fails, so a gate cannot pass by being vacuous: a quarter row
off by one, a row with no source, a stake smuggled onto the projection surface, a mislabelled
row, an unpriced bet row, and a blank status that must diff as blank.

**A defect this session found and fixed.** `model.assert_no_mixing()` excluded the four
fields it existed to catch (`market_price`, `stake_pct`, `edge_vs_market`, `kelly_fraction`)
from its own leak test, so a projection row carrying a 12% Kelly stake passed. The wall was
real in the templates and vacuous in the assertion. It now fails on any of those fields
holding a real number, and the test that caught it is kept.

```
$ python3 -m nba2.v4.check
v4 check: 8 gates pass / 0 fail; 0 structural, 0 surface-wall, 0 numeric; publishable=True

$ python3 -m unittest discover -s nba2/v4 -t . -p 'test_*.py'
Ran 51 tests ... OK
```

Whole repo: `Ran 379 tests ... OK`.

---

## 5. Claims the site makes that are **not** verified, and are published as such

| Claim | Status | Why |
|---|---|---|
| Actual closing lines / line movement | **blocked** F-V4-04 | no licensed odds feed |
| Edge, stake, Kelly, CLV | **blocked** F-V4-04, R-048 | an edge needs a price; a stake needs a bankroll policy the owner has not set |
| Minutes / usage delta per injured player | **blank** F-V4-08 | the official report states status and reason, not minutes; no matched before/after game pair |
| Production impact of a return | **blank** F-V4-08 | same |
| Who starts in place of an out player | **blank** | not in any official source read; starting lineups are a different page |
| Any player-prop correlation | **partial** | per-player logs exist for a subset only |
| Arena coordinates used for travel | **third-party** | Wikimedia/Wikidata P625, labelled on every row; no official NBA coordinate page exists |

Travel distances are labelled `THIRD-PARTY` in the model output for this reason: they are
sourced and reproducible, but they are not an official NBA number and are not presented as one.

---

## 6. Reproduce everything

```
python3 -m nba2.v4.write_capture     # rewrite the official snapshot from the transcription
python3 -m nba2.v4.injury_diff       # store releases, diff consecutive, cross-day
python3 -m nba2.v4.settlement        # grade the seal against verified finals, keep the stamp
python3 -m nba2.v4                   # gates -> render -> post-build check
python3 -m nba2.v4.check             # the checks alone, verbose
python3 -m unittest discover -s nba2/v4 -t . -p 'test_*.py'
```

The capture rewrite is byte-identical on a rerun, and `refresh.yml` fails if it is not — so a
drift between the transcription and the committed snapshot cannot be committed silently.
