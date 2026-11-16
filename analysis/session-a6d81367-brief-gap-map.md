# Brief gap map — session `arena/a6d81367-nba2` (2026-11-15, UTC)

Line-by-line status of the 2026-11-15 brief against the repository **as committed at `main` @ `8ab2476`**
(PR #74). Every status below is backed by a file path or a command that was actually run in this
session. Nothing here re-states a value that was not checked.

## 0. What this session could and could not verify

* **Egress.** This sandbox can reach `github.com`, `api.github.com`, `registry.npmjs.org`,
  `pypi.org` and the files hosts. `cdn.nba.com` and `stats.nba.com` fail at TLS
  (`curl` → `SSL_ERROR_SYSCALL`, 2026-11-15 ~23:3x UTC). `ak-static.cms.nba.com`,
  `official.nba.com` and `www.nba.com` were not reachable for this session either.
  **No official NBA value was re-fetched here.** Official values below are cited from the committed
  captures, each of which records its own retrieval time and source URL.
* **GitHub Actions logs and artifacts.** `gh run view --log(-failed)`, `gh api …/logs` and
  `gh run download` all return `EOF` from the blob host, so the runner-side root cause of the
  nightly failure is **not** verified here (matches open item F-043).
* **Official sources used (from the committed captures):**
  * Injury index — https://official.nba.com/nba-injury-report-2026-27-season/
  * Injury PDF (11/15 06:15 AM ET, the one the 11/15 capture cites) — https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15AM.pdf
  * Results page — https://www.nba.com/games?date=2026-11-14 (capture `source_page`)
  * Game book (11/14 DEN@NOP) — https://statsdmz.nba.com/pdfs/20261114/20261114_DENNOP_book.pdf
  * Game page — https://www.nba.com/game/den-vs-nop-0022600231/box-score
  * Scheduled-run history — https://github.com/wingbangboozle1-lang/NBA2/actions (workflow "Nightly ingest + settlement")

## 1. Brief line items

Status key: **MET** = implemented and checked here · **PARTIAL** = code or data exists but a stated
requirement is not fully met · **BLOCKED** = cannot be done with the repo's current inputs · **NOT MET**
= required and absent.

| # | Brief item | Status | Evidence in the repo (checked this session) | Gap / note |
|---|---|---|---|---|
| 1 | Scheduled job refreshes schedule, standings, team stats, injuries per rolling slate | **PARTIAL** | `nba2/v2/refresh.py` + `refresh.yml` step "Rolling-window ingest". Last committed capture `data/raw/capture_2026-11-15/` (slate 34 games, standings 30, team stats 3 pages, injury 101 rows). | Scheduled runs **failed 4 of 4** (`gh run list --workflow "Nightly ingest + settlement"`: 2026-11-14 14:37Z, 2026-11-14 19:18Z, 2026-11-15 14:38Z, 2026-11-15 19:17Z). The failing step is *Fetch official finals*, which **skips** the rolling-ingest step (step 10). Owned by open PR #70 (`arena/d09f8d1e-nba2`). |
| 2 | Rebuild only after freshness and provenance gates pass | **MET in code, not reached in CI** | `nba2/v2/refresh.py` `run_gates` (5 gates, fail-closed, exit 4). `python -m nba2.v2.check` = OK (0 structural, 0 semantic) run here. | No scheduled run has reached the gate step since 11/14. |
| 3 | Official per-game result feed: date, teams, final score, quarter scores | **PARTIAL** | `data/raw/capture_2026-11-15/results_2026-11-14.json`: 5 finals, `away_quarters`/`home_quarters` present, `source_page` above. `data/raw/finals_2026-11-13.json`: 9 games with `periods` (quarter field not confirmed as quarter scores). | Only 2 dates committed. No automatic feed (see #1). |
| 4 | Settle only after final scores verified | **PARTIAL — defect** | `nba2/pipeline/settle.py` `find_finals()` = newest `data/raw/finals_*.json` **by name** → returns `finals_all.json`. `finals_all.json` holds 9 **11/13** games and **0** game IDs from either sealed ledger (checked). | Irregularity IR-1 below. |
| 5 | Store every injury PDF with its timestamp | **NOT MET** | `data/raw/pdf/` is empty; `find . -name '*.pdf'` = 0 files. The 11/15 capture records URL + `revision_time_et` + `retrieved_at_utc` but **no SHA-256**. | The nightly *Archive* step downloads PDFs, but the commit step is skipped when any earlier step fails, so downloads are discarded (IR-2). |
| 6 | Diff consecutive injury reports to detect status changes | **PARTIAL** | Older pairs exist: `audit/injury_delta_0415_to_0715.json`, `audit/2026-11-14-766d/injury_diff_2026-11-14_766d.json`. No committed diff for the 11/14 → 11/15 pair. | Diff is not produced by the scheduled job. |
| 7 | Pre-registration file per strategy, frozen before first bet | **MET** | `data/v2/prereg/S1.json`…`S7.json`; `data/v3/prereg/` (5 files, S1–S5). No bet has been placed (site: "stakes 0"). | Freeze timestamps should be re-checked against the first-bet date when one exists. |
| 8 | Tamper-evident ledger: hash each pick, publish hash before tip, verify after settlement | **PARTIAL** | Seals: `data/raw/ledger/sealed-2026-11-13.json` (22 rows), `sealed-2026-11-14.json` (27), `data/v3/ledger/sealed-2026-11-15.json`. CI verifies seals (`ci.yml`). | Post-settlement verification is incomplete (IR-1): 0 of 22 / 0 of 27 rows settled in `data/settlement.json`. |
| 9 | Split site into *projection* (publish now) and *bet* (gated) surfaces | **MET** | `site/projections.html` (v3) and `site/picks.html` / `site/lines.html`; both state stakes = 0. | — |
| 10 | Two independent estimators; disagreement is the primary confidence signal | **MET** | `site/teams.html` (per completion record `arena/98b0eae9-nba2`); v3 `nba2/v3/model.py` two estimators. | — |
| 11 | Pin home-court advantage to measured home-win rate, not fitted | **PARTIAL — conflict** | `nba2/v3/model.py` lines 11–12, 133–152: `h = sd × Φ⁻¹(measured home win rate)` (pinned). **But** the published v2 index (`site/index.html`) reads "+0.77 home-court (fitted, pts)". | Irregularity IR-4: two HCA labels in the published site. |
| 12 | Luck as z-score per team; refuse strategies that lean on a team outside the noise band | **MET** | `site/index.html`: "0/30 teams outside luck noise"; `data/v2/teams.json` luck z; strategy gate in `nba2/v2/strategy_lab.py`. | — |
| 13 | Rest, back-to-back, 3-in-4 from official schedule; travel distance from sourced arena coordinates | **MET (coords THIRD-PARTY)** | `site/travel.html`; `data/raw/capture_2026-11-15/arenas_2026-11-15.json` (30/30). | Geocodes are third-party because official pages publish none (labelled). |
| 14 | Minutes redistribution: top-8 shares and replacement shares when a player is out | **PARTIAL** | `site/rotation.html`; `nba2/v2/minutes.py`. | Inputs are one game of player logs (see #23); the redistribution rule is mechanical, not fitted. |
| 15 | Stop publishing one blended rating as headline; disagreement is the headline | **MET** | `site/teams.html` (completion record). | — |
| 16 | Price every parlay with measured ρ; print naive product beside it | **MET** | `site/correlations.html` (completion record). | ρ measurement scope should be re-checked against the sample size before any use. |
| 17 | Rotation availability as its own column on the picks page | **MET** | `site/picks.html` (completion record). | — |
| 18 | Market-anchored prior: blend model with closing line, weight by OOS log-loss | **BLOCKED** | Framework present; `market_prior` blank by policy. | No licensed odds feed (open item G6). Cannot be computed. |
| 19 | Model the total as possessions × points-per-possession | **MET** | `site/lines.html` / `site/projections.html` (completion record). | — |
| 20 | Injuries page banner shows injury-report revision time and retrieval time | **MET** | `site/injuries.html`: "Current release: 2026-11-15 06:15 AM ET — revision time 2026-11-15 06:15 AM ET, retrieved 2026-11-15T12:05:00Z". | — |
| 21 | Settle sealed ledger as each game day ends; keep settlement stamp visible | **PARTIAL — conflict** | `site/official-results.html` says "5 official finals of 2026-11-14 settled … read 2026-11-15T12:00:00Z" (stamp visible). `data/settlement.json` says `PARTIAL — 22 game(s) have no official final score` (games_settled 0) and `27` for the 14th. | Two published/committed settlement views disagree (IR-1). Pick-level settlement for the 11/14 ledger is not shown. |
| 22 | Re-read the three official team-stat pages (traditional, opponent, advanced); re-cut inputs | **PARTIAL** | `data/raw/capture_2026-11-15/team_stats_2026-11-15.json` (3 pages, 21 cross-checks per completion record). | One capture date only; the scheduled job cannot refresh it (#1). |
| 23 | Per-player game logs (minutes, points, rebounds, assists, opponent) for at least players on an injury report | **PARTIAL — coverage gap** | `data/raw/capture_2026-11-15/gamelogs_2026-11-14_DEN_NOP.json` and `data/v2/gamelogs.json`: 19 rows, **1 of 5** games from 11/14. Source `https://www.nba.com/game/den-vs-nop-0022600231/box-score`. | Injury-report players outside DEN/NOP have no logs. IR-5. |
| 24 | Originate own lines (spread, total, win probability) | **MET** | `site/lines.html` (34 games over 11/15–11/18). | Derived, not official; labelled as such. |
| 25 | Strategy leaderboard with validation gates, correlations, rewards | **MET** | `site/strategies.html`, `site/strategy-lab.html`, `site/skill-attribution.html`. | — |
| 26 | Generate picks for every slate up to 3 days ahead using originated lines | **PARTIAL** | Window 11/15 → 11/18 (= today … today+3) in `data/raw/capture_2026-11-15/slate_2026-11-15_to_11-18.json`. | Generated by hand-run capture, not the scheduled job (#1). |
| 27 | Track injury impact on rotation/production; game-flow analysis | **PARTIAL** | `site/rotation.html`, `site/gameflow.html`. | In-game columns are blank by policy (`README.md` game-flow row). |
| 28 | Executive summary | **MET** | `site/executive-summary.html`. | — |
| 29 | Suggestions section for review before any change | **MET** | `site/suggestions.html`; `suggestions/SUGGESTIONS.json` (50 entries: 37 "awaiting owner decision"). | — |
| 30 | Questions register: what is known, unknown, and what discovers the gap | **MET** | `site/questions.html`; `requirements/QUESTIONS.json` (39 entries). | The questions file has no `status` field on any entry. |
| 31 | Every table row carries an official source link; blanks flagged, never inferred | **MET (enforced)** | `nba2/pipeline/lint.py`, `nba2/v2/check.py`, `nba2/v3/gates.py` G-P1…G-P3 (7/8 pass; see IR-3). | — |
| 32 | Player props and combos priced | **BLOCKED** | `site/props.html`: every row blank by policy. | No prop-line feed, no player-level pricing inputs. |
| 33 | GitHub Pages live site | **MET** | `pages.yml` run 43717038321 on `main`: success (PR #74 merge). | Deploys only the `site/` tree. |
| 34 | Coordination board and parallel-session rules | **MET** | `COORDINATION.md`. | Open claims: `arena/d09f8d1e-nba2` (PR #70), `arena/04a61ac0-nba2` (PR #72). |

## 2. Irregularities (for the Flagged for Review page)

* **IR-1 — Settlement reads the wrong finals file, and two settlement views disagree.**
  `nba2/pipeline/settle.py::find_finals` picks the lexicographically last `data/raw/finals_*.json`,
  which is `finals_all.json` (9 games, all 11/13, 0 overlap with either sealed ledger). The five official
  11/14 finals (`data/raw/capture_2026-11-15/results_2026-11-14.json`, `source_page`
  https://www.nba.com/games?date=2026-11-14) overlap 5 of the ledger's 11/14 game IDs but are never read.
  Result: `data/settlement.json` = 0 settled, while `site/official-results.html` shows 5 settled.
  *Not fixed in this session* — the fix touches the v1 chain (settlement → site.json → index/pages → CI parity).
* **IR-2 — Injury PDFs are downloaded and then discarded.** The nightly *Archive* step writes to
  `data/raw/pdf/`, but the commit step is skipped when a later step fails (all 4 scheduled runs). The
  committed tree has 0 PDFs. The completion record for `arena/98b0eae9-nba2` says "PDF archived + SHA-256'd";
  neither the PDF nor a SHA-256 for the 11/15 release exists in the repository. *Corrected here.*
* **IR-3 — v3 gate G-F3 fails (advisory).** `data/v3/verification.json`: used the 11/15 06:00 AM release,
  newest indexed at retrieval was 06:15 AM. `nba2/v3/official.py` lines 28, 79–80, 324–325 use 06:00.
  The gate is advisory by its own policy, so the site still publishes. The 06:15 release is the one the
  v2 banner shows. The two surfaces therefore show different release stamps.
* **IR-4 — Home-court advantage has two labels on the published site.** v2 index: "+0.77 home-court
  (fitted, pts)". v3 model: pinned to the measured home-win rate. Requirement #11 says pinned. The v2
  label has not been reconciled.
* **IR-5 — Player-log coverage is 1 of 5 games** (19 rows, DEN@NOP 11/14). The brief asks for at least
  the players on an injury report.
* **IR-6 — Injury transcript provenance.** `data/raw/capture_2026-11-15/injury_report_2026-11-15_0615AM.json`
  was taken with "platform page-fetch tool (fetch_page)", i.e. transcribed from a rendered page. The
  machine recall check (`refresh --verify-transcript`) needs the archived PDF text, which is absent (IR-2),
  so the transcript is **unverified against the PDF**. Continuation rows are attributed by block position
  and flagged. A "Utah Jazz under LAL@PHX" block is flagged in the file.
* **IR-7 — Scheduled job failing 4 of 4 runs** (see #1). Root cause unverified (F-043); logs unreachable from this sandbox.
* **IR-8 — Test side effect (fixed in this session, A6-1).** `nba2/v2/test_v2.py::test_site_builds_and_passes_its_own_check`
  rebuilt the published tree, dropping the v3 navigation links; a local `unittest` run left `site/` dirty.
  Fixed by snapshot/restore in the test (commit on `arena/a6d81367-nba2`); v2 suite 129/129 green and tree clean after the run.
* **IR-9 — Sealed-ledger file names do not match game dates.** `sealed-2026-11-13.json` holds predictions
  dated 2026-11-14 / 15 / 16 (its name is the seal date). Readers may assume 11/13 games.

## 3. Questions that must be answered before any decision (and how to find each answer)

| Q | Question | Answer today | How to discover it |
|---|---|---|---|
| Q-A | Why do scheduled runs fail at "Fetch official finals"? | Unknown (F-043) | Re-run the probe from a GitHub runner with logs captured in the repo (open PR #70). |
| Q-B | Are `cdn.nba.com` / `stats.nba.com` reachable from GitHub-hosted runners? | Unknown from this sandbox | Probe workflow on Actions (PR #70); record status + bytes per URL in the repo. |
| Q-C | Does the 11/15 06:15 AM PDF text match the 101-row transcript? | Not verified (no PDF stored) | Store the PDF (IR-2), run the recall check. |
| Q-D | Which HCA value is the published one? | Conflict (IR-4) | Single source of truth in `nba2/v3/model.py`; regenerate v2 label. |
| Q-E | What is the official per-game quarter score for every game 11/13–11/18? | 11/14: 5 games with quarter arrays (capture). 11/13: 9 finals, quarter fields not confirmed. 11/15–11/18: no finals yet. | Finals capture for each date (rolling job). |
| Q-F | Is there a licensed closing-line feed? | No | Owner decision (suggestion queue); required for #18 and #32. |
| Q-G | How many games of player logs are needed for minutes and injury effects? | 1 of 5 | Capture every 11/14 box score (one per game URL). |

## 4. Suggestions (for the owner queue; nothing implemented here without approval)

1. Make the commit step of the nightly job `if: always()` after the archive step, so PDFs and
   transcripts are kept even when finals fail (IR-2). Owner: `arena/d09f8d1e-nba2`.
2. Change `settle.find_finals` to read the union of `data/raw/finals_*.json` and the official
   `capture_*/results_*.json` feeds, keyed by game ID, and fail on conflicting scores (IR-1). Owner: integration session (touches v1 chain).
3. Reconcile the two HCA labels and the two release stamps before the next publish (IR-3, IR-4).
4. Add `status` to every entry in `requirements/QUESTIONS.json` so the questions page can show
   answered vs open without hand-written text.
