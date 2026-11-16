# Session `arena/4f780342-nba2` — verification record (2026-11-16, UTC)

Branch `arena/4f780342-nba2`, base `f943bd1` (= `main` after PR #97). Claim `d8ce8cb`, pushed
before any edit. Everything below was run in this session; nothing is quoted from a commit
message or an earlier session's summary.

## 0. What this session could and could not reach

| Capability | Result | Evidence |
|---|---|---|
| `www.nba.com`, `official.nba.com`, `ak-static.cms.nba.com` via the platform page-fetch tool | **reachable** | Standings, schedule and the 11/16 01:00 PM injury PDF were all read this session |
| `cdn.nba.com`, `stats.nba.com`, `statsdmz.nba.com`, `ak-static.cms.nba.com` from bash | **blocked** (TLS reset) | `URLError ... SSL connection has been closed (EOF)`; reproduced for each host |
| `github.com` / `api.github.com` | reachable | `gh run list`, `gh pr view` |
| GitHub Actions **job logs** | **not reachable** | `gh run view --log-failed` → `EOF` from the blob host (carried defect F-043) |

The first row matters more than the fourth. Three earlier sessions published "the official
podfs are unreachable" as a standing limitation; that is true of *bash egress from a sandbox*
and false of the fetch tool. This session read four official documents with it.

## 1. Defects found, each reproduced before it was fixed

### D-1 — the nightly job failed 5 of 5 runs and took the other surfaces with it

`gh run list --workflow=refresh.yml`: failures at 2026-11-14T14:37Z, 11-14T19:18Z,
11-15T14:38Z, 11-15T19:17Z and 11-16T16:06Z. `gh api .../jobs` on the last run pinpoints the
step: **"Fetch official finals for arrived window dates"**. Every later step was skipped —
the injury archive, the rolling refresh of schedule/standings/team stats, the gate chain and
the commit. So three of the four official surfaces the brief asks for were never refreshed by
CI, and the downloaded PDFs were thrown away with the job.

The runner-side error message is not retrievable (F-043), so the *proximate* cause is not
quoted here. What is fixed is the structure that turned any single failure into a total one:

* each surface is its own step with `continue-on-error`, so one unreachable endpoint cannot
  skip the other three;
* a date with no sealed-window games returns 0 instead of aborting (a real code path —
  `cmd_finals` now says so explicitly rather than treating an empty list as failure);
* `data/raw/refresh_verdict.json` records each surface's outcome every run;
* a separate `publish` job rebuilds only when all four surfaces captured cleanly, so
  publishing still fails closed while **evidence is still committed**;
* `.github/workflows/probe-egress.yml` measures, with HTTP status and byte counts, which
  official hosts a runner can reach — replacing the inherited assumption with a dated fact.

### D-2 — the injury data was a hand transcription, and it was wrong on six rows

The previous v4 build stored 70 transcribed rows in `capture.py` and declared the 09:30 AM
release "identical row-for-row" **without reading it**, so the guard test compared a
hard-coded string with itself. Reading both releases from their own URLs:

| Player | Earlier transcription | Official 09:30 AM PDF | Consequence |
|---|---|---|---|
| Tyson, Jaylon (CLE) | Questionable | **Doubtful** | a real status change, published as unchanged |
| Curry, Stephen (GSW) | *(blank, "extraction lost the column")* | **Out** | published as unknown when it was known |
| Moody, Moses (GSW) | *(blank)* | **Out** | same |
| Porzingis, Kristaps (GSW) | *(blank)* | **Out** | same |
| Santos, Gui (GSW) | *(blank)* | **Questionable** | same |
| Williams, Brandon (GSW) | *(blank)* | **Out** | same |

The published flag F-V4-06 blamed the PDF ("the status column did not survive"). It did
survive. The parser addressed cells **by position**, and those rows carry fewer leading
cells because of where the page broke.

**Fix.** `nba2/v4/injury_renderings.py` stores each release **verbatim** as the fetch tool
rendered it (with a sha256 over that text); `nba2/v4/injury_parse.py` assigns every cell by
**content type** — date, time, matchup, status word, `Last, First` player, reason — and never
by position. A cell it cannot type stays blank and the release publishes an `unread` count.
Both stored releases parse with **0 unread rows**.

**Verification.** `python -m nba2.v4.injury_diff` → `cross_session_check` lists exactly the six
rows above with both PDFs linked; the earlier session's 70-row file is retained byte for byte
as `injury_transcript_20261116_0930AM_superseded.json` so the comparison is against *their*
record. `test_v4.py::TestInjuryParse` (9 tests) pins the behaviour, including "a status must
never be inferred from a reason".

### D-3 — two settlements disagreed, and one of them graded a third of the picks

`nba2/v4/settlement.py` graded only the v3 seal (34 picks, 9 graded). The v1 chain graded the
other two seals (22 and 27 picks) into a file the v4 pages never read. Both numbers were
arithmetically true and neither was the whole story.

**Fix.** One surface, `data/v4/settlement/settled-all.json`, covers **all three** seals with
every digest recomputed before grading. Measured today:

| Seal | Window | Sealed | Graded | Ungraded | Winner hit | Margin MAE | Digest |
|---|---|---|---|---|---|---|---|
| `data/raw/ledger/sealed-2026-11-13.json` | 11/14–11/16 | 22 | 14 | 8 | 0.8571 | 10.887 | verified |
| `data/raw/ledger/sealed-2026-11-14.json` | 11/14–11/17 | 27 | 14 | 13 | 0.8571 | 10.887 | verified |
| `data/v3/ledger/sealed-2026-11-15.json` | 11/15–11/18 | 34 | 9 | 25 | 1.0000 | 8.267 | verified |

The three seals overlap, so the same games are graded more than once: 37 graded rows are
**14 distinct games**, with 23 repeat gradings. Publishing 37 as a sample would be a
three-fold overstatement, so both numbers are shown and every repeat row is labelled
*counted once*.

## 2. Numbers a reviewer should be able to re-derive

| Quantity | Value | Command |
|---|---|---|
| Sealed rows, all seals | 83 (22 + 27 + 34) | `python -m nba2.v4.settlement` |
| Graded / ungraded | 37 / 46 | same |
| Distinct games graded | **14** | same |
| Repeat gradings | 23 | same |
| Correct distinct winners / expected under the seals' own probabilities | 12 / 8.855 | same |
| Poisson-binomial tail, P(X ≥ 12) | **0.0425** | same |
| Exact-run product (the number *not* to quote) | 0.000199 | same |
| Distinct-game log-loss vs coin flip | 0.6088 vs 0.6931 | same |
| Distinct-game margin MAE / total MAE | 10.887 / 14.629 | same |
| Stored injury releases / unread rows | 2 / **0** | `python -m nba2.v4.injury_diff` |
| Status changes 09:30 → 13:00 | **2** (Larsson Q→D; Stewart Q→Out) | same |
| Player rows added as clubs filed | 19 | same |
| Clubs still NOT YET SUBMITTED at 13:00 | 10 | same |

**Read the tail, not the hit rate.** 12 of 14 is 0.857; the chance of doing at least that well
if the seals' own probabilities are right is 0.0425. That is just outside the 0.05 band on
fourteen games in one week. It is not a measured edge and nothing is staked on it.

## 3. Official sources read this session

| Document | URL | Used for |
|---|---|---|
| NBA.com Standings | https://www.nba.com/standings | re-read today; all 30 clubs match the committed 11/16 capture (checked BOS 11-2, PHI 11-3, MIL 1-13, SAC 1-12, UTA 1-13 including streak and home/road splits) |
| NBA.com Schedule | https://www.nba.com/schedule?date=2026-11-16 | 8 games on 11/16 — ids, tip times and arenas match the committed slate exactly |
| Injury report index | https://official.nba.com/nba-injury-report-2026-27-season/ | established that releases are published every ~15 minutes and that 13:00 PM is newer than anything stored |
| Injury PDF 09:30 AM | https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-16_09_30AM.pdf | stored verbatim, source of the six corrections |
| Injury PDF 01:00 PM | https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-16_01_00PM.pdf | stored verbatim, source of the two status changes |

## 4. Verification performed (all run here)

```
python -m unittest discover -s nba2/tests -t .           79 OK
python -m unittest discover -s nba2/v2 -t . -p test_*   146 OK
python -m unittest discover -s nba2/v3 -t . -p test_*    67 OK
python -m unittest discover -s nba2/v4 -t . -p test_*    61 OK
python -m unittest discover -s backtest/tests -t .       49 OK
python -m nba2.v2.check               OK — 0 structural, 0 semantic
python -m nba2.v3.check               OK — 0 structural, 0 semantic (1 advisory freshness gate, pre-existing)
python -m nba2.v4.check               8 gates pass / 0 fail; 0 structural, 0 surface-wall, 0 numeric
python -m nba2.pipeline.lint          LINT OK — 1436 rows across 50 tables
python3 tools/check_links_all.py      ALL INTERNAL LINKS OK — 132 files, 6461 internal
python3 -m nba2.pipeline.seal_predictions --verify   both v1 seals VERIFIED
python -m backtest.engine.build + tools/verify_backtest.py   VERIFICATION PASSED
```

**Parity check (what `pages.yml` and `publish-parity.yml` gate on):** after rebuilding every
tree from the committed inputs in CI order, `git diff --cached --stat` over `site/`,
`data/v2`, `data/v3`, `data/v4`, `data/site.json`, root `*.html`, `pages/` and `backtest/`
reported **0 files changed**. A rebuild reproduces the published tree byte for byte.

## 5. Irregularities for review (published on the Flagged page; none blocks publication)

* **I-4F-01 (fixed, F-V4-06 / F-V4-09 marked resolved):** the injury transcription errors in
  D-2. The register now states the date, the finding and what is published instead.
* **I-4F-02 (open):** the nightly job's runner-side error text cannot be retrieved from this
  sandbox (`gh run view --log-failed` → EOF). The structural repair is testable without it
  because the repair is about job structure, not the specific network error; `probe-egress.yml`
  and `refresh_verdict.json` are designed to record it from the runner next time.
* **I-4F-03 (open):** `data/raw/egress_probe.json` and `data/v4/injury/binary_manifest.json`
  will be written by the next scheduled run. Until then F-V4-01 (PDF bytes not stored) stays
  published as an open gap even though the code path to close it now exists.
* **I-4F-04 (open):** settlement stops at the 11/15 game day. The 11/16 slate completes
  tonight and nothing in the repository can grade it until a 11/16 finals capture exists;
  suggestion S-60 proposes the guard that would make that visible as a failure rather than an
  absence.
* **I-4F-05 (observed, not fixed — outside this session's scope):** PR #98 (`arena/fe0ffa49-nba2`)
  is `CONFLICTING` and appears to restate several of the same findings (a self-re-issuing v3
  seal, re-freezing v2 prereg files, σ double-counting five games). This session did not touch
  it. Whoever integrates it should expect overlap with the settlement rewrite here.
* **I-4F-06 (observed, not fixed):** `data/site.json` is rewritten with a build timestamp by
  `nba2.pipeline.build_site_data`, so an interrupted run leaves it dirty and one v1 test
  (`TestReproducibility`) then fails against its own earlier output. It passes on a clean
  tree; the flakiness is real and is worth a guard, but it is the v1 chain's design, not this
  session's code.

## 6. Not done, and where it is published

| Item | State | Where a reader sees it |
|---|---|---|
| PDF bytes in the repo (F-V4-01) | code path added, no runner result yet | Flagged page, `v4-injuries.html#bytes` |
| Market-anchored prior / odds | blocked, no licensed feed | F-V4-04, bet surface 0 rows |
| Player props and combos | blocked, no prop feed | props page, every row blank by policy |
| Per-player logs for 11/15–11/16 | not captured | F-V4-02 |
| Settling the 11/16+ slates | needs a 11/16 finals capture | suggestion S-60, settle page "what is not graded" |
| Pages source setting (legacy vs workflow) | owner decision | FLAG-PAGES-01 / F-033 |
