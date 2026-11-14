# Session `arena/766d0269-nba2` — repo review, line by line (2026-11-14)

Branch `arena/766d0269-nba2`, base `b3ed44d`. Every claim below was checked against a file in
this repository or an official page fetched in this session; the check that produced it is
named. Nothing here is inferred.

## 0. Baseline measured before any edit

| Check | Command | Result |
|---|---|---|
| v1 unit tests | `python -m unittest discover -s nba2/tests -t .` | 64 OK |
| v2 model + site tests | `python -m unittest discover -s nba2/v2 -t .` | 80 OK |
| backtest tests | `python -m unittest discover -s backtest/tests -t .` | 49 OK |
| v2 structural/semantic check | `python -m nba2.v2.check` | OK — 0 / 0 |
| v1 provenance lint | `python -m nba2.pipeline.lint` | 1,409 rows / 50 tables OK |
| semantic crosschecks | `python tools/crosscheck_site.py` | 97 checks: **88 pass, 2 fail**, 7 info |
| site links | `python tools/check_links_all.py` | 110 files / 4,914 links, all OK |

The two pre-existing crosscheck failures were **CC-BT-03** and **CC-DOC-01**. Both are now
fixed at their source (§2, §3) and the same command reports **90 pass, 0 fail**.

## 1. Defects found and fixed

### N-03 (high) — a spread bet was priced with the moneyline probability

`nba2/v2/report.py::t_picks` selected `p_lean = p_home if p_home >= 0.5 else 1 - p_home` — the
probability the lean **wins the game** — and then printed `1/p_lean` as the break-even price for a
**spread** lean.

Why that is wrong, in the model's own terms (`nba2/v2/model.py`): `spread = -round_0.5(margin)` and
`p_home_cover = Φ((margin + spread)/σ)`. The spread is the median of the model's own margin
distribution, so `p_home_cover` is ≈0.50 on **every** game by construction — measured range across
the 27-game window: 0.4926 to 0.5070. The moneyline probability ranges 0.074 to 0.952. Pricing a
spread with it produced break-even triggers as short as **−1246**.

Measured on the published artefact (`data/v2/lines.json`) before the fix:

| Game | Our spread | P(lean) printed | Actual P(cover at our line) | Trigger printed | Correct trigger |
|---|---|---|---|---|---|
| DEN @ NOP | +7.0 | 0.711 | 0.507 | 1.406 (−247) | 1.973 (−103) |
| BKN @ MEM | −11.0 | 0.801 | 0.498 | 1.248 (−403) | 2.006 (+101) |
| CHI @ MIN | −21.5 | 0.952 | 0.503 | 1.050 (−1992) | 1.989 (+101) |

**Fix.** Both probabilities are now published per row (`P(lean) win`, `P(lean) cover`) with both
triggers (`Spread trigger`, `ML trigger`), and the page states that the spread trigger is the
break-even for covering our own number. **Four regression tests** in `nba2/v2/test_v2.py::
TestPicksProbabilityIsTheRightMarket` fail if the two are ever conflated again.

**What I checked before calling it a defect, and what I ruled out.** `p_home_cover` itself is
correct: recomputing `Φ((margin + spread)/σ)` independently reproduces all 27 published values
(0/27 disagreement). The error was in the *reporting* layer, not the model.

### N-04 (high) — the accuracy figure could not be read as skill

`nba2/v2/strategy_lab.py` scored seven strategies and published `S1 hit rate = 64.7% (n = 167)`
with `p = 0.0002` against a coin flip. A p-value against a coin flip is not the test the brief
asks for: the model backs the side its own ratings favour, and those ratings are built from the
same results a reader can see, so the hit rate inherits the favourite's base rate.

Added `naive_baselines()` and `skill_attribution()` (Walk-forward, priors only, identical game set,
published tie counts, exact McNemar on the discordant games). Result:

| Rule | Games | Hits | Rate | 95% CI |
|---|---|---|---|---|
| Always home | 167 | 86 | 51.5% | 44.0–59.0% |
| **Better prior win %** | **148** (19 ties skipped) | **104** | **70.3%** | 62.5–77.0% |
| Better prior point differential | 165 (2 ties) | 104 | 63.0% | 55.5–70.0% |
| Originated model (S1) | 167 | 108 | 64.7% | 58.7–70.2% |

Paired test on the 33 games where the model and the win-% rule disagreed: **model 13, naive rule
20**, exact two-sided McNemar **p = 0.2962**. Against the point-differential rule: 23 v 19, p = 0.644.

**Independently recomputed** with a separate implementation (different rating code, different tie
handling, cumulative W-L instead of the lab's structures): 167 predictions, model 108/167 =
0.6467, baseline 104/148 = 0.7027, discordant 13 v 20, p ≈ 0.2962 — identical.

This is published as finding **F-053** and on the new **Skill vs luck** page. It is not "fixed",
because it is a measurement, not a bug.

### N-05 (medium) — the injury page was six releases stale and said otherwise

The site is built from the official **11/14 04:30 AM ET** injury release. Its own prose said the
05:30 AM release "returned AccessDenied ... so the freshest reachable release is 04:30 AM ET".

Checked in this session: the league index (`official.nba.com/nba-injury-report-2026-27-season/`)
lists releases hourly through **01:30 PM ET**, and
`Injury-Report_2026-11-14_01_30PM.pdf` downloads without error. The 01:30 PM release was captured
verbatim (`audit/2026-11-14-766d/injury_2026-11-14_0130PM_766d.md`) and diffed player by player
(`verify_injuries.py`):

| Movement | Count | Detail |
|---|---|---|
| Status changed on a shared row | **4** | Brown Jr. Q→Probable · Christie Q→Doubtful · Harkless Q→Available · Jones Q→Available |
| New rows in the later release | 24 | Cleveland (7 more) and Chicago (7) filed after 04:30, plus 10 |
| Rows withdrawn | 0 | — |

The page now publishes the diff and the staleness; refreshing the snapshot is logged as **S-46 /
D-07** rather than done silently (the v2 model is availability-blind, so a swap would move no
number while breaking the build's parity check).

### N-06 (high) — the nightly ingest on `main` is failing

`gh run list --workflow=refresh.yml` → one run, **failure** (43605830665, 2026-11-14T14:37Z).
Step 6 `Fetch official finals for arrived window dates` exited 3; steps 7–12 were skipped, so
settlement and the rebuild never ran. Exit 3 from `cmd_finals` means *every official endpoint was
unreachable at the network level* — this sandbox measures exactly that (`curl` to `cdn.nba.com`
and `www.nba.com` → HTTP 000). Published as **F-055**; the workflow and `nba2/pipeline/refresh.py`
are outside this session's scope (two open PRs own those paths).

## 2. Pre-existing crosscheck failures, fixed at the source

### CC-BT-03 — "ats.hit_rate and accuracy.straight_up_accuracy disagree"

Real, and it was an unexplained discrepancy rather than a wrong number. `backtest/engine/skill.py`
drops any game whose originated line is exactly a pick'em from the ATS denominator (166) while
`accuracy_block` keeps it (167), so 105/166 = 0.6325 and 105/167 = 0.6287 — same picks, different
denominator, with the reason nowhere on the page.

Fixed at the source: `ats_block()` now takes the straight-up totals, publishes
`pickem_games_excluded`, `straight_up_for_comparison` and the reason, and the backtest page renders
a reconciliation card. The crosscheck was tightened, not loosened: it now fails unless the exclusion
count reconciles the two denominators **and** both blocks select the same winning games.

### CC-DOC-01 — README row count 1,404 vs 1,409 measured

The README figure was stale before this session and moved again when the registers grew. Rebuilt
and synced to **1,415** after the generators reached a fixed point. The failure is a count that
was hand-copied in three earlier sessions; it is now correct at commit time, and the suggestion to
generate it (rather than copy it) is already on the register.

## 3. Published data re-verified against the live official pages

| Artefact | Official source | Result |
|---|---|---|
| 30 club records (W-L, home/road) | `nba.com/standings`, fetched 19:40Z | **30/30 identical**, 0 unverified |
| 27 window games × 6 fields | `nba.com/schedule?date=2026-11-14`, fetched 19:45Z | **27/27 identical** (date, tip time, away, home, game id, venue) |
| Injury rows | `Injury-Report_2026-11-14_01_30PM.pdf`, fetched 19:50Z | later release is 50 rows / 9 clubs; diff vs published 04:30 snapshot: 4 changes, 24 additions, 0 withdrawals |
| Injury filing rules | `official.nba.com` injury index | quoted verbatim and unchanged |

Scripts and raw captures: `audit/2026-11-14-766d/`. Each script is re-runnable and returns a
non-zero exit if a comparison fails.

## 4. Irregularities logged and not fixed (out of scope)

| ID | Finding | Why not fixed |
|---|---|---|
| F-055 | Nightly ingest failing on `main` | `.github/workflows/**` and `nba2/pipeline/refresh.py` are claimed by open PRs #57/#50 |
| F-054 | Injury snapshot six releases stale | needs a build-input decision (D-07); disclosed instead |
| F-056 | "AccessDenied" reported as a property of the source | corrected in place, original wording preserved |
| S-48 | The README describes the nightly workflow as running | depends on F-055 |

## 5. Things I checked and found sound

- `nba2/v2/model.py` arithmetic: `p_home = Φ(margin/σ)`, `spread = −round_0.5(margin)`,
  `p_home_cover = Φ((margin+spread)/σ)`, totals from two estimators. Re-derived independently.
- The 183-game history: unique game ids, dates 2026-10-20 → 2026-11-13, home win rate 52.5%
  (96/183), mean margin +1.72, sd 16.98, mean total 227.0, sd 19.21 — all plausible for the league
  and mutually consistent with the 30-team records.
- Walk-forward leakage: `leakage_audit` recomputes the prior-game count per date and reports 0
  violations across 167 predictions; I re-derived the same structure independently.
- The sealed ledgers are untouched by this session (`git diff -- data/raw/ledger` empty).
- `nba2/v2.check`, `tools/check_links_all.py`, `tools/verify_site.py` all pass on the final tree.

## 6. One self-correction, recorded

While drafting the standings capture I wrote a duplicated Dallas row and a "16 rows for 15 clubs"
irregularity **before** fetching the second half of the page. Neither existed — the page is
returned in two chunks and the table simply continued. The fabricated content was deleted and the
correction recorded in the capture file (**F-057**). It affected no published number, and it is
recorded because a verification trail that hides its own mistakes is not a verification trail.
