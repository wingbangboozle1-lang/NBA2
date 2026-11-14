# NBA2 — executive summary and integration notes (session `arena/5b80b88a-nba2`, 2026-11-14)

Read with: [`analysis/crosscheck-5b80b88a.md`](crosscheck-5b80b88a.md) — the 80 checks this
session ran, each with its recomputation — and
[`queue-additions-5b80b88a.json`](queue-additions-5b80b88a.json), the merge-ready queue rows.

Baseline for every number below: `main` at `1ba60fc` (PR #28/#30, 2026-11-14 ~01:19 UTC), which adds the
measured-skill backtest surface from session `arena/f7477d5e-nba2` on top of the data-window refresh
(`ed017f5`, PRs #24/#25/#27). If `main` moves again, the
counts move with it — which is finding F2 below, in another form.

## 1. What the system is, in one paragraph

Committed official snapshots (NBA.com schedule, the referee-operations injury PDFs, a third-party
ratings table) feed a Python pipeline that calibrates team ratings, originates a spread / total /
moneyline per game, prices parlays under an explicit correlation sweep, turns the injury report
into rotation-body arithmetic, runs ten validation gates per strategy, and renders all of it into
a static GitHub Pages site where a row with no source is a build error and an unconfirmed value is
blank plus a flag instead of a guess. Forward picks are pre-registered in a sealed, hashed ledger
so nothing can be re-fitted after tip-off, and a nightly workflow (`nba2/pipeline/refresh.py`,
`refresh.yml`) now exists to archive the official injury releases, fetch finals, settle the ledger
and rebuild — failing closed if any gate or endpoint fails.

| What | Number | Measured by |
|---|---|---|
| Published tables / rows | 36 tables, 964 rows | `python3 -m nba2.pipeline.lint` + `CC-DOC-01` |
| Canonical pages | 18 (landing + 17 subpages), every nav link and flag anchor resolving | `CC-HTML-02/04/05` |
| Games in the pick window | 31 (2026-11-13 → 11-16; as-of 11-13) | `CC-SNAP-04/06/07` |
| Injury rows | 95 from the 11/13 16:15 ET release + 31 window rows from the 11/13 19:30 ET release | `CC-SNAP-08:*`, `CC-PUB-02` |
| Strategies × gates | 9 × 10 = 90 results, 0 passed | `CC-GATE-04` |
| Sealed forward predictions | 22, digest `cf7dedc689597cb8…` printed on every page; equals the displayed line table | `CC-SEAL-01…06` |
| Reward pool | 100 units, 0 allocated, no strategy promoted | `CC-GATE-03/05` |
| Tests | 62, all passing | `python3 -m unittest discover -s nba2/tests -t .` |
| This session's independent checks | 88: 72 pass, 8 fail, 8 info | `tools/crosscheck_site.py` |

## 2. What is real, what is derived, and what is deliberately empty

**Real (read from an official document, verifiable at the cited URL):** the slate — dates, tip
times, arenas, broadcasts, Emirates NBA Cup groups, official game IDs; win-loss records; the
injury report's seven columns for two releases; the two-document corroboration (11 of 31 games
confirmed twice, 3 with the time cell lost to a page break, 0 mismatches, 17 outside that report —
all verified by recomputation in `CC-PUB-05`, not taken from the caption).

**Derived (ours, reproducible, the actual product):** ratings with reliability shrinkage; spread /
total / moneyline and our own fair prices; P(cover) / P(over); correlation sweeps and parlay joint
intervals; rotation-body counts, expected missing bodies and rotation floors; schedule-supported
game-flow factors (rest, back-to-back, 3-in-4, home/away load); luck/z-scores; tiers; gate
verdicts. The identities that keep these honest all pass: margin↔spread sign, total↔projected
scores, P(home)↔our fair price, net = PS/G − PA/G, shrunk = SRS × λ, GP = W+L, rotation counts = a
recount of the injury rows, sealed ledger = the published line table.

**Empty by policy — and that is the right answer, not a gap:** every minutes-impact,
production-impact and line-adjustment cell for all injury rows; every player-prop line and
projection; all nine strategy scores and every reward amount; every stake percentage; the four
in-game game-flow columns. Three of those cells were fabricated by an earlier session and deleted
in review (irregularities I-01…I-03 on the Flagged for Review page). A number there would be the
failure mode this project exists to avoid.

## 3. The eight failing checks, as eight findings

Each was reproduced by recomputing from the committed files; **none of them changes a published
line, pick, or model input**, and three of them are defects in code merged within the hour before
this report was written.

| # | Finding | Evidence | Why it matters |
|---|---|---|---|
| **F1** | **A negative count is published on the live site.** `availability_window` shows `no_rows_yet = -5` for 2026-11-14, and `not_yet_submitted = 10` where the true figure is 5. `build_site_data.py:487-491` computes `slots − filed − nys` from two *overlapping* team sets: a team that filed in the 19:30 release is still counted as "not yet submitted" from the 16:15 release | `CC-DER-11`, `CC-DER-12`; recomputed: slots 10 − filed 5 − not-submitted-only 5 = **0**, not −5 | A reader cannot tell a coverage statement from an arithmetic slip; the number that answers "how blind is this slate?" is wrong, and the lint cannot see it because the cell is a number with a source |
| **F2** | README's generated-site counts are already stale: it says 33 tables / 915 rows, the build now emits 36 / 964 | `CC-DOC-01` vs `python3 -m nba2.pipeline.lint` | Fourth session to hit hand-copied counts; the fix is to stop copying them (S-27), not to re-copy them |
| **F3** | The ratings snapshot publishes two false self-diagnosed FAILs; recomputing its own 30 records gives `sum(close_w)=99=sum(close_l)`, `sum(blowout_w)=88=sum(blowout_l)` — balanced | `CC-SNAP-13` vs `data/raw/team_ratings_2026-11-13.json` → `provenance.internal_consistency_checks` | `FLAG-RAT-02` accuses the site of a defect its data does not have, and is the stated reason those four columns are excluded from the model |
| **F4** | The column labelled "W-L (official NBA.com)" is filled from the third-party source, so the advertised disagreement guard cannot fire | `build_site_data.py:111` (`wl_official` from the same object as `wl`); 30/30 identical; `CC-DER-05` | It reads as verification and is a copy |
| **F5** | AT-RISK gates are reported as "blocked" on all nine leaderboard rows | `leaderboard.py:149` folds `"AT-RISK"` into `gates_blocked`; matrix says 8 blocked + 2 at-risk; `CC-GATE-02` | At-risk gates are the ones a single data change can move — the roadmap is hidden by the flattening |
| **F6** | Washington is keyed `WSH` on one surface and `WAS` on four others | `originated/data/teams.json` vs `nba2/data/records.json`, `data/standings-2026-11-13.csv`, the ratings snapshot, the published table; `CC-X-00` | Any join drops the club *silently*; it is also how a coverage figure gets misread as a data conflict |
| **F7** | The measured result lives on a second surface only. The canonical site still reads `gates_passed = 0 of 90` and "nothing has settled yet", while `backtest/` reports 2 of 10 gates PASS on 139 graded games — different metrics (graded games vs settled bets against a price), so not a contradiction, but a reader of the landing page cannot see that grading happened at all. The two also use different gate vocabularies: `AT-RISK` on the site, `PARTIAL` in the backtest | `CC-BT-08`; `backtest/data/report.json` → `gates.summary`, `data/site.json` → `meta.gates_passed` | The project's headline question — "is there skill here?" — has a partial answer that the site does not carry |
| **F8** | 7 published rows are rendered on no page (`parlays_xg`, `parlay_costs`) | `build_site_data.py:852-853` vs `build_site.py:260`; `CC-HTML-03` | Cross-game parlays and stacking cost — both explicitly requested — are invisible while being counted in every total |

What the harness *confirmed*, because a verification log that only lists faults is not a
verification: no value on any blocked-source row; every blank carrying a flag or a note; every
`official` label pointing at an NBA-official host; no dangling flag reference and no orphan flag;
tip times agreeing across three independent surfaces; the sealed ledger matching the displayed
lines exactly; every rendered row carrying a source cell; every internal link and every flag
anchor resolving.

## 4. The `28/30` vs `30/30` dispute, closed with row-level evidence

Appendix 1 of the cross-check report is a 30-row matrix of every committed capture. Reading it:

* **Agreement is 30/30.** For every club that any two captures both contain, the W-L is identical.
  Zero disagreements, across five independent captures (ratings snapshot, `nba2/data/records.json`,
  `originated/data/teams.json`, `data/standings-2026-11-13.csv`, the published table).
* **Coverage was the 28.** "28 of 30" is *visibility inside one retrieved page text* — the
  2026-11-13 22:26 UTC `nba.com/games` capture did not show Toronto and Washington. That is a
  property of that capture, not a dispute about any record.
* **The gap is closed by a second official capture.** `nba2/data/records.json` records TOR and WAS
  from their official team pages; the standings CSV cites `nba.com/games?date=…` for both
  (`CC-X-03`: no club is uncovered once the official captures are unioned).
* **And the trap that made it look like a defect:** the `WSH`/`WAS` alias (F6). A tricode join
  reports Washington as "missing" from one side, which is exactly how a coverage number turns into
  an apparent conflict.

**Recommended site wording:** "30/30 clubs agree; 28/30 were visible in the 11/13 22:26 UTC
game-card capture; TOR and WAS are confirmed by a second official capture." Never a bare "28/30".

## 4b. What the measured backtest says — and it is not "we have edge"

`backtest/data/report.json` (session `arena/f7477d5e-nba2`, PR #28) grades 155 official final
scores, 139 of them with a line to compare against. This session re-derived its arithmetic from the
committed game rows rather than trusting it — `CC-BT-01…07` all pass: the counts, every published
rate over its own numerator and denominator, the tier and calibration partitions, the gate index,
and the rule that nobody is paid while a gate fails. What those numbers say:

| Measure | Our model | The naive alternative | Verdict in the report |
|---|---|---|---|
| Margin error (MAE, points) | 12.173 | 13.266 (zero-line baseline) | better, but `p = 0.348` — not significant |
| Straight-up hit rate | 62.59% (87/139) | **64.03% (89/139) for "pick the club with the better net rating"** | the baseline picks more winners; `p = 0.902` |
| Winner discrimination (AUROC) | 0.7015 | — | useful ordering, not a priced edge |
| Tier A only | 76.9% (65 games), deflated z = 2.17 | coin flip 0.5 | the one signal worth following up |
| Rewards | — | — | **0 units allocated**, because G-01 (300 settled bets) is FAIL at 46% of sample |

The honest reading for anyone deciding where to spend: **a one-line naive rule is currently as good
as the model at picking winners**, and the sample cannot tell 63% from 52% (their own `power` table:
a 1-point edge needs ~4,551 games at 80% power). That is the luck-removal requirement doing its
job — and it is the single most decision-relevant fact on the repository today, which is why F7
(it lives on an unintegrated surface) matters.

## 5. Luck removal and the leaderboard: where it honestly stands

The machinery that separates skill from luck is built and enforced: pre-registration with the
digest committed in the same change as the site, so a published line cannot be re-fitted after
tip-off; a 300-settled-bet minimum and holdout requirement inside the gate set; clustering so nine
near-identical strategies cannot take five prizes; the reward pool at 100 units with **0
allocated**; and no promotion while gates are unmeasured. The luck columns themselves are
arithmetically sound (`CC-DER-06`).

What is missing is a price. Two things changed this week: `refresh.py --finals` now
fetches official final scores into the shape `settle` expects, so the ledger can start accruing
graded results without a human in the loop — **if** the endpoint answers from a runner; and there
is still no market price, so CLV, ROI and stake sizing stay empty, and every "edge" on the site
remains measured against our own baseline. `CC-GATE-06` verifies the discipline that matters most:
no score is published while nothing has settled. That is the whole difference between a leaderboard
and a lottery.

## 6. Runner reachability: what was measured, and what was not

- **Measured here (this sandbox):** `python3 tools/ingest_official.py --probe` at 01:13 UTC,
  2026-11-14 — `cdn.nba.com`, `stats.nba.com`, `ak-static.cms.nba.com` (today's 13:00 ET injury
  PDF URL) and `www.nba.com/schedule` all fail at TLS
  (`URLError: TLS/SSL connection has been closed`). Four endpoints, four identical failures,
  no values filled, nothing inferred.
- **Not measured:** the same probe from a GitHub-hosted runner. This session cannot dispatch a
  workflow with the credentials it has (`gh workflow run` → `HTTP 403: Resource not accessible by
  integration`, 01:15 UTC), so the answer has to come from the first scheduled run of the
  `Nightly ingest + settlement` workflow (14:05 and 18:35 UTC), which is active with **zero runs so
  far** — the honest status `CC-FRESH-03` publishes as INFO rather than PASS.
- **One duplicate avoided:** this session had built its own scheduled probe workflow; on rebase it
  collided with the shipped `refresh.yml` at the *same* 18:35 UTC cron, so the workflow was deleted
  and only the probe/capture tool remains. Two nightly jobs racing the same endpoints is how you
  end up with two "official" snapshots thirty seconds apart.

Read: the blocker is now an *infrastructure policy* question (can our runner reach the league's
CDN, and are we allowed to poll it), not an ambiguity about whether the data exists.

## 7. Decision path, in order

1. **Fix F1 today (and read 4b before writing any stake)** — it is live on the deployed site, it is three lines (`nys -= filed` before the
   subtraction, or recompute both counts from the union), and it is the only finding here that is a
   wrong *number* rather than a wrong *label*. Add the "no negative counts" assertion (S-21) so the
   class dies with it.
2. **Read the first `Nightly ingest + settlement` run** (14:05 UTC). It answers reachability, and it
   decides whether the site can ever be self-refreshing.
3. **Answer Q-23/Q-24** (source policy; which injury stamp is canonical). Then F6's alias table goes
   in *before* ingestion is trusted, or every join keeps losing Washington quietly.
4. **Answer Q-26** (promotion policy) so a reward can be paid mechanically the moment bets settle.
5. **Then the labels** — F2 through F5, F7: low effort, no model change, all of them things a
   reviewer will otherwise keep re-discovering.
6. **Decide the canonical surface (Q-25).** Six surfaces now — `backtest/**` was added by PR #28
   rather than folded into the shared data, which is precisely the failure mode Q-25 was written
   about, and it is why F7 exists at all.
7. **Only after 1-4** talk about props and stakes: they need player-level and price feeds, and no
   modelling inside this repository can substitute for inputs it does not have.
