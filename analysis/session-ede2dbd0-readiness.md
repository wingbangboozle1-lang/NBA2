# Independent integration-readiness audit — session `arena/ede2dbd0-nba2`

**Audit date:** 2026-11-19 UTC  
**Tree:** `main` / commit `41cfd812d2794db529090cd026e7056ca3c1b0cd` (same starting commit as this session branch).  
**Purpose:** distinguish what is present in the committed tree from what is current, measured, live-published, or still only proposed in open PRs. This is an audit, not a claim that the system is ready for betting.

## Executive finding

The repository already contains substantial infrastructure for originated lines, two estimators, projection/bet separation, schedule-derived rest, minutes redistribution, injury archives/diffs, player logs, a sealed ledger, official result coverage, market-prior scaffolding, suggestions/questions, and a source-linked multi-page dashboard. Its local consistency checks are strong. **The published data are not current enough to use:** the committed freshness checker reports a five-day-old model window and fails `CC-FRESH-01`; the latest scheduled refresh run in GitHub failed on 2026-11-18; and the live official NBA pages inspected in this audit are newer than the repository's committed model surface.

The current branch does not contain `nba2/v7/` or `data/v7/`. Two open PRs hold a proposed v7 model/capture and a v6 settlement repair, but both have merge conflicts; PR #130 also has failing verify/parity/v2 checks. A separate integration discussion on those PRs already says their changes need line-by-line integration and full re-verification. They are not part of `main`, and their claimed outputs are not treated here as verified.

**Decision:** keep stakes at zero and do not describe this snapshot as live or bet-ready. The next safe step is an integration of the unique v7 work onto the post-#133 tree, followed by fresh official capture, every gate, full rebuild/parity, and a confirmed deployed/live-content check. No model/input/site values were transcribed from an unverified source in this audit.

## Live official-source spot-check (read during this audit)

These are source-page checks, not a full transcription. No live data were written into project inputs. The NBA pages are linked for manual review; exact NBA response time was not exposed by the page reader, so only the audit date is recorded.

| Page checked | Direct observation | Source |
|---|---|---|
| Official NBA schedule for 2026-11-19 | The page displayed four games for the date, with scheduled tip times. This conflicts with treating the committed 2026-11-15 → 2026-11-18 window as current. No scores or next-three-day slate were transcribed. | [NBA Games — Nov 19, 2026](https://www.nba.com/games?date=2026-11-19) |
| NBA standings | The current season page identifies 2026–27 and displays Eastern and Western standings. No standings rows were copied into project data. | [NBA Standings](https://www.nba.com/standings) |
| Traditional team statistics | The official team-statistics page displayed the 2026–27 season and 30 rows. No statistics were copied into project data. | [NBA Stats — Traditional](https://www.nba.com/stats/teams/traditional) |
| Opponent team statistics | The official page displayed opponent statistics for NBA teams. No statistics were copied into project data. | [NBA Stats — Opponent](https://www.nba.com/stats/teams/opponent) |
| Advanced team statistics | The official page displayed advanced team measures, including ratings, pace, and possessions. No statistics were copied into project data. | [NBA Stats — Advanced](https://www.nba.com/stats/teams/advanced) |
| Injury report index | The official 2026–27 index states that reports update continually and links November 19 releases (including the 07:00 a.m. ET entry visible in the fetched page). The current PDF was not downloaded/transcribed into the repo. | [NBA Official Injury Report — 2026–27](https://official.nba.com/nba-injury-report-2026-27-season/) |

This spot-check does **not** verify every statistic, every injury designation, schedule dates + tips through T+3, or any game result. Do not use it as a replacement for a dated capture with provenance.

## Current-tree verification

Commands were run against the committed checkout. `git status` was clean after these read-only checks.

| Check | Result |
|---|---|
| `python -m unittest discover -s nba2/tests -t . -p 'test_*.py'` | 92/92 passed |
| `python -m unittest discover -s nba2/v2 -t . -p 'test_*.py'` | 167/167 passed; emitted Python `ResourceWarning`s for unclosed JSON file handles in `nba2/v2/model.py` and `nba2/v2/travel.py` |
| `python -m nba2.v2.check` | pass; 0 structural, 0 semantic issues |
| v3 suite + `python -m nba2.v3.check` | 67 tests passed; 8/8 gates, 0 structural/semantic issues |
| v4 suite + `python -m nba2.v4.check` | 61 tests passed; 8/8 gates passed |
| v5 suite + `python -m nba2.v5.check` | 26 tests passed; 8/8 gates passed; 767 player rows |
| v6 suite + `python -m nba2.v6.check` | 52 tests passed; checker exited 0 |
| `python -m unittest discover -s backtest/tests -t . -p 'test_*.py'` | 49/49 passed |
| `python -m nba2.pipeline.lint` | pass; 1,436 sourced rows across 50 tables, every blank explained |
| `python tools/check_links_all.py` | pass; 143 HTML files, 7,472 internal links |
| `python tools/verify_site.py` | pass; 13 pages, 249 rows, 303 links |
| `python tools/crosscheck_site.py` | **87 pass / 1 fail / 9 info**. Sole failure: `CC-FRESH-01`, the snapshot is five days old and five dates are already tipped or within the published window. It also reports `CC-FRESH-02` (“no explicit stale-state banner”); the generated `site/index.html` does contain text saying the snapshot is not a live refresh and the latest ingest failed, so this looks like a detector/banner wording mismatch, not proof that the warning is absent. |

The checks establish internal consistency of the **committed** snapshots. They do not establish current truth, external calibration, or profitability. The unit-test `ResourceWarning`s are a code-quality irregularity, not test failures.

## Findings and status against the request

| Area | Committed-tree evidence | Audit status | Official source / manual review |
|---|---|---|---|
| Scheduled rolling capture of schedule, standings, three team-stat pages, and injuries | `.github/workflows/refresh.yml` invokes `nba2.v2.refresh --write`; it records independent surface outcomes and gates publication. The latest listed refresh run failed on 2026-11-18, and this audit found later official pages. | Implemented, but freshness gate currently fails; no current capture was committed in this branch. | [NBA schedule](https://www.nba.com/schedule), [standings](https://www.nba.com/standings), [traditional](https://www.nba.com/stats/teams/traditional), [opponent](https://www.nba.com/stats/teams/opponent), [advanced](https://www.nba.com/stats/teams/advanced), [injury index](https://official.nba.com/nba-injury-report-2026-27-season/); [latest refresh run](https://github.com/wingbangboozle1-lang/NBA2/actions/runs/44381003145) |
| Published rolling slate | The live site currently presents a 34-game Nov 15–18 window, while the official NBA Nov 19 schedule page displayed four games for Nov 19. The repository freshness checker independently fails. | Stale; do not use as current picks. | [Live NBA schedule for Nov 19](https://www.nba.com/games?date=2026-11-19); [live site](https://wingbangboozle1-lang.github.io/NBA2/) |
| Two estimators / disagreement headline | `site/projection.html` separates estimator disagreement and labels its headline; v4 checks projection/bet surface separation. | Present in committed older surface; current inputs stale. | [NBA advanced stats](https://www.nba.com/stats/teams/advanced); [NBA opponent stats](https://www.nba.com/stats/teams/opponent) |
| Pinned HCA and luck gate | `site/projection.html` reports a measured home-win rate and pinned HCA; the v4 gate verifies captured home/road record identities. | Mechanism present; recut from current official inputs still needed. | [NBA standings](https://www.nba.com/standings) |
| Possessions × points-per-possession total | The v4 projection checks and published methodology assert this identity. | Mechanism present; no current-slate validation in this audit. | [NBA advanced stats](https://www.nba.com/stats/teams/advanced) |
| Separate projection and gated bet surfaces | `site/projection.html` and `site/bet.html` are distinct; v4 check confirms the wall and blocks unpriced bet rows. | Present. No live odds feed was found; market edge and positive stake remain unavailable. | [NBA schedule](https://www.nba.com/schedule); market prices have no official NBA source and are not claimed to exist. |
| Player availability as picks column; minutes redistribution; player logs | `site/picks.html` includes a rotation availability column; injury/minutes pages and v5 include replacement and per-player log surfaces. v5 gates report 767 sourced player rows. | Present in older committed data; newest official injury report has not been transcribed into this checkout. | [NBA injury index](https://official.nba.com/nba-injury-report-2026-27-season/); NBA gamebooks are linked per row in committed player-log data. |
| Archived injury PDFs, revision/retrieval stamps, consecutive diffs | v4/v6 include injury archive, binary manifest, diff, and page banners; latest committed v4 record is dated 2026-11-17, earlier than the current official index checked today. | Pipeline/surfaces present; current report archive and current diff absent from this branch. | [Official NBA injury report index](https://official.nba.com/nba-injury-report-2026-27-season/) |
| Official per-game results, quarter scores, settlement stamps, sealed ledger | v4–v6 store coverage/settlement and the checks verify seals and committed results. v6 coverage’s frozen source clock is `2026-11-18T19:30:20Z`; no post-capture result verification was done here. | Internally gated; not current through today. No final has been inferred. | [NBA schedule/results](https://www.nba.com/schedule); gamebook source URLs are stored row-by-row in the committed feed. |
| Strategy preregistration, leaderboard, parlay rho, props | Strategies and ledger/preregistration pages exist; measured parlay rho is published. Props/market inputs remain constrained by missing player/market prices and by sample depth. | Framework present; no current evidence of a validated reward-eligible strategy was established by this audit. | [Official NBA schedule](https://www.nba.com/schedule); odds/prices are not supplied by the NBA and no connected market feed is evidenced. |
| Suggestions, open questions, executive summary, flagged review | Category pages and registers already exist in `site/`; the source-linked flagged page includes staleness issues. | Present, but site needs its current stale-data warning/queue reconciled with live state. | [NBA injury index](https://official.nba.com/nba-injury-report-2026-27-season/), [NBA schedule](https://www.nba.com/schedule) |
| Travel distances | A travel page and arena-coordinate input exist in the repo. | Internal feature only; this audit did not independently verify each arena coordinate against a trusted official source. Keep any unverified coordinate flagged, not silently treated as official. | [NBA teams](https://www.nba.com/teams) (official team/arena navigation; not itself a source for the coordinate table) |

## Publication / integration irregularities

1. **Stale snapshot is blocking current decision use.** `CC-FRESH-01` is the only failing crosscheck. The repo has a 2026-11-17 rolling capture (`data/raw/refresh_2026-11-17/standings_2026-11-17.json` and `team_stats_2026-11-17.json`) and result coverage frozen at 2026-11-18T19:30:20Z. The official pages inspected on Nov 19 are newer. Do not regenerate a site from old inputs and call it refreshed.
2. **The latest scheduled ingest failed.** The most recent `refresh.yml` run listed on GitHub is [run 44381003145](https://github.com/wingbangboozle1-lang/NBA2/actions/runs/44381003145), conclusion failure at 2026-11-18T19:29:04Z. A failure is not a successful refresh.
3. **Open implementation PRs are not safe to merge as-is.** [PR #130](https://github.com/wingbangboozle1-lang/NBA2/pull/130) contains a unique v7 feature layer but is conflicting and its `verify`, `parity`, and `v2` checks failed at its recorded run. [PR #131](https://github.com/wingbangboozle1-lang/NBA2/pull/131) has successful checks but is also conflicting. Owner/integration comments on both call for selective integration/reverification; do not treat PR-only data as current `main` data.
4. **GitHub Pages source vs workflow/live response is inconsistent.** GitHub API reports Pages `build_type=legacy`, source `main /`, status `built`; the `pages.yml` Actions run [44476981781](https://github.com/wingbangboozle1-lang/NBA2/actions/runs/44476981781) completed successfully. Yet the live root URL returned the older 34-game Nov 15–18 page, while the local committed root `index.html` is a redirect to `site/index.html`; fetching `/NBA2/site/` returned a GitHub “Unicorns” error page during this audit. Therefore the successful workflow result does **not** prove the intended current tree is the live response. Live publication remains unverified pending a stable fetch and a confirmed Pages configuration/content match.
5. **Crosscheck stale-banner detector discrepancy.** `CC-FRESH-02` says no banner, but `site/index.html` has a visible note that the snapshot is not a live refresh and the latest scheduled ingest failed. Retest/fix the detector so a genuine stale warning passes, without relaxing the freshness gate.
6. **No current v7 files on this commit.** `nba2/v7/` and `data/v7/` are absent from `main`; the proposed v7 slate/prereg pages remain in PR #130 only. Its current check failures and integration conflicts must be resolved before those outputs can be published.
7. **Nonblocking code warning:** v2 test runs emit unclosed-file `ResourceWarning`s in `nba2/v2/model.py` and `nba2/v2/travel.py`; all tests passed, but these should be corrected separately.

## Recommended sequence (no owner answers required)

1. Integrate only the unique, reviewable PR #130 features onto current `main`; selectively retain unique PR #131 settlement behavior only if it adds coverage beyond merged PR #132. Resolve the shared v6/nav/site conflicts in a single integration tree. Keep all sealed prediction files immutable.
2. Run a dated official capture from the current schedule, standings, traditional/opponent/advanced stats, and newest injury PDF. Persist raw source bytes/URLs, revision and retrieval times, checksums, and field-level provenance. If any surface fails, preserve the prior site and publish a visible blocked/stale status; do not refresh `generated_at` as a substitute for new inputs.
3. Recompute the model and all downstream pages only after freshness/provenance gates pass. Re-run the full tests, gates, `crosscheck_site`, source/link checks, seal verification, settlement, and deterministic rebuild/parity. Verify every published row still links to the official source actually used.
4. Resolve Pages configuration/content mismatch; fetch the public URL after deploy and verify it matches the committed `site/` build, including the freshness banner and category navigation.
5. Keep bet stakes at zero until walk-forward skill is distinguishable from a baseline, price/closing-line inputs exist, and each strategy’s preregistered gates pass. Current infrastructure is a research dashboard, not a demonstrated reward-eligible betting system.

## Sources / manual review

Official sources fetched/read during this audit: [NBA schedule](https://www.nba.com/games?date=2026-11-19), [NBA standings](https://www.nba.com/standings), [NBA Stats traditional](https://www.nba.com/stats/teams/traditional), [NBA Stats opponent](https://www.nba.com/stats/teams/opponent), [NBA Stats advanced](https://www.nba.com/stats/teams/advanced), and [NBA Official injury report index](https://official.nba.com/nba-injury-report-2026-27-season/). The source pages are dynamic and this report does not substitute for a stored, timestamped capture.

GitHub evidence: [scheduled refresh run 44381003145](https://github.com/wingbangboozle1-lang/NBA2/actions/runs/44381003145), [Pages run 44476981781](https://github.com/wingbangboozle1-lang/NBA2/actions/runs/44476981781), [PR #130](https://github.com/wingbangboozle1-lang/NBA2/pull/130), [PR #131](https://github.com/wingbangboozle1-lang/NBA2/pull/131), and [live dashboard](https://wingbangboozle1-lang.github.io/NBA2/).
