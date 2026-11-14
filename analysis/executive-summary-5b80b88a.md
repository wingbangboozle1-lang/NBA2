# NBA2 — executive summary and integration notes (session `arena/5b80b88a-nba2`, 2026-11-14)

Read with: [`analysis/crosscheck-5b80b88a.md`](crosscheck-5b80b88a.md) (the 76 checks this session
ran and their evidence) and [`queue-additions-5b80b88a.json`](queue-additions-5b80b88a.json)
(the suggestions/questions written so an integration session can splice them into the published
queues verbatim).

## 1. What the system is, in one paragraph

Committed official snapshots (NBA.com schedule, the referee-operations injury PDF, a
third-party ratings table) feed a Python pipeline that calibrates team ratings, originates a
spread / total / moneyline per game, prices parlays under an explicit correlation sweep, converts
the injury report into rotation-body arithmetic, runs nine validation gates per strategy, and
renders everything into a static GitHub Pages site — where a row with no source is a build error
and an unconfirmed value is blank plus a flag rather than a guess. Forward picks are
pre-registered in a sealed, hashed ledger so nothing can be quietly re-fitted after tip-off.

| What | Number | Measured by |
|---|---|---|
| Published tables / rows | 33 tables, 915 rows | `python3 -m nba2.pipeline.lint` |
| Pages on the canonical surface | 18 (landing + 17 subpages) | file count, `CC-DOC-01` |
| Games in the pick window | 31 (2026-11-13 → 11-16, as-of 11-13) | `CC-SNAP-04/06/07` |
| Injury rows transcribed | 95 (85 with a status, 10 `NOT YET SUBMITTED`) | `CC-SNAP-08` |
| Strategies × gates | 9 × 10 = 90 gate results, 0 passed | `CC-GATE-04` |
| Sealed forward predictions | 22, digest `cf7dedc689597cb8…` printed on every page | `CC-SEAL-01..06` |
| Reward pool | 100 units, 0 allocated | `CC-GATE-05` |
| Tests | 55, all passing | `python3 -m unittest discover -s nba2/tests -t .` |
| This session's independent checks | 76: 64 pass, 6 fail, 6 info | `tools/crosscheck_site.py` |

## 2. What is real, what is derived, and what is deliberately empty

**Real (read from an official document, verifiable at the cited URL):** the slate — dates, tip
times, arenas, broadcasts, Emirates NBA Cup groups, official game IDs; win-loss records; the
injury report's seven columns (date, time, matchup, team, player, status, reason); the
two-document corroboration (11 of 31 games confirmed twice, 3 matchups confirmed with the time
cell lost to a page break, 0 mismatches, 17 outside that report — verified by recomputation,
`CC-PUB-05`).

**Derived (ours, reproducible, and the point of the project):** ratings with reliability shrinkage,
spread / total / moneyline and our own fair prices, P(cover) / P(over), correlation sweeps and
parlay joint intervals, rotation-body counts and expected missing bodies, game-flow factors that
the schedule alone supports (rest, back-to-back, 3-in-4, home/away load), luck/z-scores, tiers,
gate verdicts. The identity checks that keep these honest all pass: margin↔spread sign,
total↔projected scores, P(home)↔fair price, net = PS/G − PA/G, shrunk = SRS × λ, GP = W+L,
rotation counts = a recount of the injury rows, sealed ledger = the published line table.

**Empty by policy (and that is the correct answer, not a gap to fill):** every minutes-impact,
production-impact and line-adjustment cell for all 95 injury rows (the official report has no such
field and no player-level feed is connected); every player-prop line and projection; all nine
strategy scores and every reward amount (nothing has settled, so a score would be noise dressed as
skill); every stake percentage (there is no market price to size against); the four in-game
game-flow columns (no play-by-play, lineups or foul data). A number in those cells would be the
exact failure mode this project is supposed to avoid — three of them were fabricated by an earlier
session and were deleted in review (irregularities I-01…I-03 on the Flagged for Review page).

## 3. What this session verified, and the six defects it found

`tools/crosscheck_site.py` re-derives published claims from the committed snapshots with its own
arithmetic — deliberately not by importing the model, because re-running the model is what the
build already does. First run: **64 pass, 6 fail**. Each failure is a documentation, presentation
or keying defect; **none of them changes a published line, pick, or model input.**

| # | Finding | Evidence | Consequence if left |
|---|---|---|---|
| 1 | The ratings snapshot publishes two false self-diagnosed FAILs (league-wide close/blowout balance). `sum(close_w)=99=sum(close_l)`, `sum(blowout_w)=88=sum(blowout_l)` | `data/raw/team_ratings_2026-11-13.json` → `provenance.internal_consistency_checks` vs a recount of its own `records`; `CC-SNAP-13` | `FLAG-RAT-02` accuses the site of a defect its data does not have, and is the stated reason those four columns are excluded from the model |
| 2 | The column labelled "W-L (official NBA.com)" is filled from the third-party source, so the advertised cross-check cannot ever fire | `build_site_data.py:111` (`wl_official=f"{t.wins}-{t.losses}"` — same object as `wl`); 30/30 identical; `CC-DER-05` | A guard that reads like verification and is a copy. Readers will trust the wrong thing |
| 3 | AT-RISK gates are reported as "blocked" on the leaderboard | `leaderboard.py:149` folds `"AT-RISK"` into `gates_blocked`; the matrix says 8 blocked + 2 at-risk, the row says "10 blocked"; `CC-GATE-02` | The one number that shows *what a data change could unlock* is hidden |
| 4 | Washington is keyed `WSH` on one surface and `WAS` on four others | `originated/data/teams.json` vs `nba2/data/records.json`, `data/standings-2026-11-13.csv`, the ratings snapshot, the published table; `CC-X-00` | Any join drops the club silently — invisible row loss, and a plausible root cause of "28 of 30" being read as a data defect |
| 5 | README publishes two different test counts (49 in the commands block, 55 in the table) | `README.md:82` vs `README.md:62` vs the measured 55; `CC-DOC-01` | Hand-copied counts drift; this is the third session to trip on it |
| 6 | 7 published rows are rendered on no page | `build_site_data.py:852-853` builds `parlays_xg` + `parlay_costs`; `build_site.py:260` renders only `correlation` + `parlays`; `CC-HTML-03` | Cross-game and stacking-cost analysis — both explicitly requested — is invisible while being counted in every total |

Everything else the harness could decide, it confirmed: no invented value anywhere in the published
data (no value on any blocked-source row; every blank carries a flag or note; every `official`
label points at an NBA host; no flag references nothing and nothing references a missing flag;
tip times agree across three independent surfaces; every sealed prediction is an official game in
window and equals the displayed line; every rendered row carries a source cell; every landing-page
link and every flag anchor resolves).

## 4. The `28/30` vs `30/30` dispute, resolved from row-level evidence

Two audits left this open: `data/raw/team_ratings_2026-11-13.json` says all 30 win-loss records
match the official source, while the published ratings table says the NBA.com cross-check covers
28 of 30. Both are true, because they count different things, and the evidence now sits in one
table (Appendix 1 of `crosscheck-5b80b88a.md`):

* **Agreement:** for every club that any pair of captures both contains, the W-L is identical —
  30 of 30 clubs agree across five committed captures, zero disagreements.
* **Coverage:** the "28 of 30" figure is *visibility inside one retrieved page text* — Toronto and
  Washington were not in the captured `nba.com/games` text (the caption says so), which is a
  property of that one capture, not a disagreement about any record.
* **Closure:** both clubs are covered by a second official capture — `nba2/data/records.json`
  records them from their official team pages, and `data/standings-2026-11-13.csv` cites
  `nba.com/games?date=…` rows for them. `CC-X-03` confirms no club is uncovered once both official
  captures are combined.
* **The trap that made it look like a defect:** the `WSH`/`WAS` alias (finding 4). A comparison
  that joins on tricode reports Washington as "missing" from one side, which is exactly how a
  coverage gap gets misread as a data conflict.

**Recommended wording for the site:** "30/30 clubs agree; 28/30 were visible in the 2026-11-13
22:26 UTC game-card capture; TOR and WAS are confirmed by a second official capture." Never a bare
"28/30", which reads as a failure.

## 5. Luck removal: where it honestly stands

The machinery for separating skill from luck is built and enforced: pre-registration with a hash
committed in the same change as the site, so a line cannot be re-fitted after tip-off
(`CC-SEAL-01..06`); a 300-bet minimum sample and holdout requirement in the gate set; clustering
so nine near-identical strategies cannot win five prizes at once; reward pool 100 units,
**allocated 0.0**; and no strategy is promoted (`CC-GATE-03`) while its gates are unmeasured. The
luck column itself is computed and self-consistent (`CC-DER-06`): win totals versus Pythagorean
expectation, with close/blowout records inside the season.

What is missing is not design but **history and prices**: there is no settled bet in the ledger and
no market price to settle against, so no strategy can be ranked, and the site says so instead of
showing a placeholder ranking. That is the correct state for a prototype, and the honest limit of
what this repository can claim today.

## 6. The decision path, in order

1. **Read the runner probe result** (`nba-ingest.yml`, section 7 below). It decides whether the
   staleness blocker is solvable in-repo at all, and it costs one workflow run.
2. **Answer Q-23/Q-24** (source policy; which injury stamp is canonical). Everything about daily
   picks depends on these two; neither is a code problem.
3. **Fix the six findings** (S-21…S-27 are one-line to low-effort). Do S-25 (key alias) *before*
   any ingestion automation, or the automation will drop rows forever.
4. **Answer Q-26** (promotion policy) so that when settled bets exist, paying a reward is a
   mechanical step and not an argument.
5. **Decide the canonical surface (Q-25).** Five published surfaces with five models is the second
   biggest usability risk on this site after staleness.
6. **Only then** enable the schedule trigger and talk about props or stakes: they need a
   player-level feed and a price feed, and no amount of modelling inside this repo can substitute
   for inputs it does not have.

## 7. Runner reachability probe

_(recorded after the probe run; see `COORDINATION.md` → this session's completion record.)_
