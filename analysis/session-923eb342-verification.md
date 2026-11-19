# Session `arena/923eb342-nba2` — line-by-line verification of the published repository

Date: **2026-11-19**. Branch `arena/923eb342-nba2`, based on `41cfd812` (main @ PR #133), rebased onto
`35a4111` (main @ PR #134) with the board conflict resolved by keeping both sections.

Live dashboard produced by this work: **`audit/923eb342/index.html`** (published by
`.github/workflows/verification-desk.yml`). Everything below is reproducible with the three commands at
the end of this file.

## 1. Method, and its limits

| | |
|---|---|
| Official reads | 7 sources, all fetched on 2026-11-19 and each carrying its URL + retrieval time in `audit/923eb342/capture_2026-11-19.json` |
| Transport | platform page-fetch. Direct TLS from this sandbox to `www.nba.com`, `official.nba.com`, `ak-static.cms.nba.com`, `stats.nba.com` fails (`SSL_ERROR_SYSCALL`, HTTP 000) — recorded rather than hidden |
| What was read | nba.com/standings (full 30-club table), games?date=2026-11-17 (5 finals), games?date=2026-11-18 (12 finals + the 11/19 and 11/20 slates), game 0022600259 (result), its box score (per-player MIN/PTS/REB/AST), the injury-report index, the 11/19/26 07:00 AM ET release |
| What was NOT read | runner logs (the GitHub blob endpoint returned `EOF` on three attempts), `stats.nba.com`/`cdn.nba.com` (unreachable from here), any market/odds source (none is configured), 11/18 box scores other than one game |
| Rule applied | a value is `verified` only if read from an official page this session or recomputed by running the repo's own code over a committed official snapshot. Otherwise it is blank + flagged. Nothing was inferred, repaired or rounded into agreement |
| Files edited | **new files only**: `audit/923eb342/**`, `analysis/session-923eb342-verification.md`, `.github/workflows/verification-desk.yml`, and the append-only board section. No production file, no generated tree, no shared navigation |

**Why no production file was edited.** At claim time `gh pr list` showed PRs **#130**
(`arena/6023d517-nba2`, touching `nba2/v6/**`, `nba2/v7/**`, `site/**`, `pages/**`, `README.md`,
`data/site.json`, `data/settlement.json`, the workflows) and **#131** (`arena/8c7c8828-nba2`, touching
`nba2/pipeline/settle.py`, `nba2/v6/**`, `refresh.yml`, `pages.yml`, `publish-parity.yml`), with two more
claim-only branches in flight. Every defect found below lands inside one of those scopes, so each is logged
here and on the board as a **request**, and the verified rows are published in this session's own
namespace (`audit/923eb342/verified/`) instead of in `data/raw/**`.

## 2. Result summary

| Verdict | Count | Meaning |
|---|---|---|
| PASS | 19 | published value equals the official read |
| SUPERSEDED (+1 game) | 24 | the committed 2026-11-18T19:30Z standings capture is right, and one game has been played since (12 finals on 11/18 were played after that capture was taken) |
| MISSING | 32 | the official source has the row and the publication does not (17 finals, 7 injury rows, 4 box-score lines, 4 model records) |
| STALE | 5 | publication predates the official read for a reason other than the one above |
| FAIL | 2 | the publication contradicts the official source, or an operational claim fails |

**82 checks. 19 pass, 63 do not, and none of the 63 was repaired by this session.**

## 3. Findings

| ID | Severity | Finding | Official evidence |
|---|---|---|---|
| F-923-01 | blocker | scheduled refresh failed **10/10** times (2026-11-14T14:37Z … 2026-11-18T19:29Z); capture succeeded, publish failed at `Rebuild every tree from the committed capture` | [run 44381003145](https://github.com/wingbangboozle1-lang/NBA2/actions/runs/44381003145) |
| F-923-02 | high | `data/v2/results.json` is a **2026-11-14 slice of 5 rows**; 17 games have gone final since (5 on 11/17, 12 on 11/18) and none is a row | [nba.com/games?date=2026-11-18](https://www.nba.com/games?date=2026-11-18) |
| F-923-03 | high | published lines end **2026-11-18**; today's 4-game slate has **0 lines** | [nba.com/games?date=2026-11-19](https://www.nba.com/games?date=2026-11-19) |
| F-923-04 | high | injury archive stops at **11/17 11:00 AM**; the official index lists 11/19 releases from 12:00 AM to 07:00 AM ET, none archived ⇒ no consecutive-report diff for 11/18–11/19 | [official injury index](https://official.nba.com/nba-injury-report-2026-27-season/) |
| F-923-05 | high | out-of-sample log-loss **0.7058** vs coin flip **0.6931** on the settled sample; `model_beats_coin_flip = false` | [data/v6/market_prior.json](https://github.com/wingbangboozle1-lang/NBA2/blob/main/data/v6/market_prior.json) |
| F-923-06 | high | player-log coverage of injury-report players **12/116 = 10.3%** | [data/v6/player_coverage.json](https://github.com/wingbangboozle1-lang/NBA2/blob/main/data/v6/player_coverage.json) |
| F-923-07 | medium | the publish failure is **not reproducible** locally: all 11 chain modules exit 0 and the rebuild differs from HEAD only in 4 files, each a timestamp or a digest of one | [run 44381003145](https://github.com/wingbangboozle1-lang/NBA2/actions/runs/44381003145) |
| F-923-08 | medium | published ratings come from a **2026-11-15** snapshot (188 club-games); 24 of 30 clubs differ from the 2026-11-19 table by exactly the games played since | [nba.com/standings](https://www.nba.com/standings) |
| F-923-09 | medium | two estimators exist but the **headline is still the single blend**; `est_a`/`est_b`/`agreement` are published as columns, not as the lead | [site/teams.html](https://github.com/wingbangboozle1-lang/NBA2/blob/main/site/teams.html) |
| F-923-10 | medium | the three official team-stat pages are **not readable** (stats.nba.com times out, cdn.nba.com 403, per the repo's own transport probe), so team stats are derived, not re-cut | [nba.com/stats/teams/traditional](https://www.nba.com/stats/teams/traditional) |
| F-923-11 | info | `nba2/v2/check.py` hard-codes `n_slate = 34` and "wins must sum to 188" — a gate frozen to one week's snapshot, and a plausible second cause of the publish failure | [nba2/v2/check.py](https://github.com/wingbangboozle1-lang/NBA2/blob/main/nba2/v2/check.py) |
| F-923-12 | info | sealed ledgers cover **2026-11-14…11-17 only**; there is nothing sealed for 11/18 onward, so the tamper-evident stream stops while the site keeps publishing | [data/raw/ledger](https://github.com/wingbangboozle1-lang/NBA2/tree/main/data/raw/ledger) |
| F-923-13 | high | the leaderboard's own `min_sample_to_rank` is **300** bets, yet it ranks **S4 first on n = 7** with a 100% hit rate and a −0.40 calibration gap | [data/v2/strategy_lab.json](https://github.com/wingbangboozle1-lang/NBA2/blob/main/data/v2/strategy_lab.json) |
| F-923-14 | high | the model's accuracy is **not distinguishable from a one-line prior**: on the 34 discordant games the baseline wins 20 to 14 (McNemar exact p = 0.3915); 0.6453 vs 0.6928 | [data/v2/strategy_lab.json](https://github.com/wingbangboozle1-lang/NBA2/blob/main/data/v2/strategy_lab.json) |

## 4. What was verified as correct (the 19 passes)

* Both **sealed ledger digests recompute** (`cf7dedc689597cb8…`, 22 picks; `c841e8f396dae6ca…`, 27 picks)
  and every settled 11/17 final in `data/settlement.json` matches the official game page — 5/5 exact
  (`NYK 111–102 TOR`, `DET 105–93 SAS`, `POR 105–106 MIN`, `UTA 132–107 LAC`, `CHA 114–118 LAL` OT).
* The **HCA is genuinely pinned**: `hca = 0.7679` equals `σ(2p−1) = 13.06 × (2 × 0.5294 − 1)` to the
  published rounding, with `p` measured over 99 home wins / 88 home losses.
* Six clubs' W-L and three clubs' home splits in the committed 2026-11-18 capture match the official table
  exactly, and the 24 clubs that differ differ by exactly one game — the twelve finals played after the
  capture was taken (19:30:05Z).
* The committed 2026-11-18 finals capture passes its own identity check: **50 records, 0 rows whose
  quarters fail to sum to the printed final**, including the OT game (CHA 114 @ LAL 118, 5th period).
* The capture leg of the last scheduled run **succeeded on all four surfaces**, which
  `data/raw/refresh_verdict.json` records and the committed `data/raw/capture_2026-11-18/*` corroborates.

## 5. Answers to the questions the brief asks

**Are the official results right?** Yes where published, and the coverage is the problem, not the values:
5 rows exist, 17 finals are missing.

**Is the schedule/standings refresh working?** Capture works. Publication does not. Ten consecutive
scheduled runs are red.

**Is the injury archive keeping up?** No — it stops three days behind the official index, so the
consecutive-report diff, which is the feature the brief asks for, has nothing to diff for 11/18–11/19.

**Do the two estimanda disagree, and is that published?** They are computed (`est_a`, `est_b`,
`agreement`) and shown as columns; the headline is still the blend. Presentation defect, data intact.

**Is HCA pinned?** Yes, and it verifies.

**Is luck removed?** Partly. Luck z-scores exist and 0/30 clubs sit outside |z| ≤ 1.96 in the current
snapshot, but the leaderboard ranks a 7-bet strategy first, which is luck by construction (F-923-13), and
the model's edge over a one-line prior is p = 0.39 (F-923-14).

**Are parlays priced with a measured ρ?** The register exists (7 quantities, with CIs; same-game margin vs
total r = 0.0044 [−0.145, 0.154] over 172 games). Same-player prop correlations are **unmeasured** because
the logs are missing.

**Is there an edge?** No, and it cannot be computed: no market price exists in the repository.

## 6. Full check table (all 82 rows, machine-generated)

| ID | Claim | Published | Official | Verdict | Source |
|---|---|---|---|---|---|
| R-WINDOW | date span of the published official result feed (data/v2/results.json rows) | 2026-11-14..2026-11-14 (5 rows) | 17 more games are final on the official site (5 on 11/17, 12 | STALE | https://www.nba.com/games?date=2026-11-18 |
| R-0022600253 | NYK @ TOR (2026-11-17) is in the official feed | absent | NYK 111 – TOR 102 | MISSING | https://www.nba.com/game/nyk-vs-tor-0022600253 |
| R-0022600255 | DET @ SAS (2026-11-17) is in the official feed | absent | DET 105 – SAS 93 | MISSING | https://www.nba.com/game/det-vs-sas-0022600255 |
| R-0022600254 | POR @ MIN (2026-11-17) is in the official feed | absent | POR 105 – MIN 106 | MISSING | https://www.nba.com/game/por-vs-min-0022600254 |
| R-0022600257 | UTA @ LAC (2026-11-17) is in the official feed | absent | UTA 132 – LAC 107 | MISSING | https://www.nba.com/game/uta-vs-lac-0022600257 |
| R-0022600256 | CHA @ LAL (2026-11-17) is in the official feed | absent | CHA 114 – LAL 118 | MISSING | https://www.nba.com/game/cha-vs-lal-0022600256 |
| R-0022600259 | HOU @ IND (2026-11-18) is in the official feed | absent | HOU 119 – IND 104 | MISSING | https://www.nba.com/game/{slug}-0022600259 |
| R-0022600261 | PHI @ ORL (2026-11-18) is in the official feed | absent | PHI 121 – ORL 116 | MISSING | https://www.nba.com/game/{slug}-0022600261 |
| R-0022600260 | MIL @ MIA (2026-11-18) is in the official feed | absent | MIL 130 – MIA 137 | MISSING | https://www.nba.com/game/{slug}-0022600260 |
| R-0022600258 | MEM @ CLE (2026-11-18) is in the official feed | absent | MEM 124 – CLE 121 | MISSING | https://www.nba.com/game/{slug}-0022600258 |
| R-0022600262 | CHI @ BKN (2026-11-18) is in the official feed | absent | CHI 137 – BKN 107 | MISSING | https://www.nba.com/game/{slug}-0022600262 |
| R-0022600263 | WAS @ TOR (2026-11-18) is in the official feed | absent | WAS 103 – TOR 99 | MISSING | https://www.nba.com/game/{slug}-0022600263 |
| R-0022600267 | GSW @ DAL (2026-11-18) is in the official feed | absent | GSW 94 – DAL 116 | MISSING | https://www.nba.com/game/{slug}-0022600267 |
| R-0022600265 | ATL @ OKC (2026-11-18) is in the official feed | absent | ATL 117 – OKC 112 | MISSING | https://www.nba.com/game/{slug}-0022600265 |
| R-0022600264 | DET @ NOP (2026-11-18) is in the official feed | absent | DET 122 – NOP 109 | MISSING | https://www.nba.com/game/{slug}-0022600264 |
| R-0022600266 | BOS @ DEN (2026-11-18) is in the official feed | absent | BOS 101 – DEN 105 | MISSING | https://www.nba.com/game/{slug}-0022600266 |
| R-0022600269 | PHX @ SAC (2026-11-18) is in the official feed | absent | PHX 128 – SAC 107 | MISSING | https://www.nba.com/game/{slug}-0022600269 |
| R-0022600268 | UTA @ LAL (2026-11-18) is in the official feed | absent | UTA 109 – LAL 97 | MISSING | https://www.nba.com/game/{slug}-0022600268 |
| S-SNAP-ATL | ATL W-L in data/raw/capture_2026-11-18/standings_2026-11-18.json | 8-6 | 9-6 | SUPERSEDED (+1 games since retrieval) | https://www.nba.com/standings |
| S-SNAP-BKN | BKN W-L in data/raw/capture_2026-11-18/standings_2026-11-18.json | 3-10 | 3-11 | SUPERSEDED (+1 games since retrieval) | https://www.nba.com/standings |
| S-SNAP-BOS | BOS W-L in data/raw/capture_2026-11-18/standings_2026-11-18.json | 11-3 | 11-4 | SUPERSEDED (+1 games since retrieval) | https://www.nba.com/standings |
| S-SNAP-CHA | CHA W-L in data/raw/capture_2026-11-18/standings_2026-11-18.json | 4-10 | 4-10 | PASS | https://www.nba.com/standings |
| S-SNAP-CHI | CHI W-L in data/raw/capture_2026-11-18/standings_2026-11-18.json | 3-10 | 4-10 | SUPERSEDED (+1 games since retrieval) | https://www.nba.com/standings |
| S-SNAP-CLE | CLE W-L in data/raw/capture_2026-11-18/standings_2026-11-18.json | 8-7 | 8-8 | SUPERSEDED (+1 games since retrieval) | https://www.nba.com/standings |
| S-SNAP-DAL | DAL W-L in data/raw/capture_2026-11-18/standings_2026-11-18.json | 7-7 | 8-7 | SUPERSEDED (+1 games since retrieval) | https://www.nba.com/standings |
| S-SNAP-DEN | DEN W-L in data/raw/capture_2026-11-18/standings_2026-11-18.json | 7-5 | 8-5 | SUPERSEDED (+1 games since retrieval) | https://www.nba.com/standings |
| S-SNAP-DET | DET W-L in data/raw/capture_2026-11-18/standings_2026-11-18.json | 9-4 | 10-4 | SUPERSEDED (+1 games since retrieval) | https://www.nba.com/standings |
| S-SNAP-GSW | GSW W-L in data/raw/capture_2026-11-18/standings_2026-11-18.json | 8-6 | 8-7 | SUPERSEDED (+1 games since retrieval) | https://www.nba.com/standings |
| S-SNAP-HOU | HOU W-L in data/raw/capture_2026-11-18/standings_2026-11-18.json | 11-4 | 12-4 | SUPERSEDED (+1 games since retrieval) | https://www.nba.com/standings |
| S-SNAP-IND | IND W-L in data/raw/capture_2026-11-18/standings_2026-11-18.json | 5-9 | 5-10 | SUPERSEDED (+1 games since retrieval) | https://www.nba.com/standings |
| S-SNAP-LAC | LAC W-L in data/raw/capture_2026-11-18/standings_2026-11-18.json | 4-9 | 4-9 | PASS | https://www.nba.com/standings |
| S-SNAP-LAL | LAL W-L in data/raw/capture_2026-11-18/standings_2026-11-18.json | 13-2 | 13-3 | SUPERSEDED (+1 games since retrieval) | https://www.nba.com/standings |
| S-SNAP-MEM | MEM W-L in data/raw/capture_2026-11-18/standings_2026-11-18.json | 10-4 | 11-4 | SUPERSEDED (+1 games since retrieval) | https://www.nba.com/standings |
| S-SNAP-MIA | MIA W-L in data/raw/capture_2026-11-18/standings_2026-11-18.json | 8-6 | 9-6 | SUPERSEDED (+1 games since retrieval) | https://www.nba.com/standings |
| S-SNAP-MIL | MIL W-L in data/raw/capture_2026-11-18/standings_2026-11-18.json | 1-13 | 1-14 | SUPERSEDED (+1 games since retrieval) | https://www.nba.com/standings |
| S-SNAP-MIN | MIN W-L in data/raw/capture_2026-11-18/standings_2026-11-18.json | 11-4 | 11-4 | PASS | https://www.nba.com/standings |
| S-SNAP-NOP | NOP W-L in data/raw/capture_2026-11-18/standings_2026-11-18.json | 5-10 | 5-11 | SUPERSEDED (+1 games since retrieval) | https://www.nba.com/standings |
| S-SNAP-NYK | NYK W-L in data/raw/capture_2026-11-18/standings_2026-11-18.json | 8-6 | 8-6 | PASS | https://www.nba.com/standings |
| S-SNAP-OKC | OKC W-L in data/raw/capture_2026-11-18/standings_2026-11-18.json | 9-5 | 9-6 | SUPERSEDED (+1 games since retrieval) | https://www.nba.com/standings |
| S-SNAP-ORL | ORL W-L in data/raw/capture_2026-11-18/standings_2026-11-18.json | 6-7 | 6-8 | SUPERSEDED (+1 games since retrieval) | https://www.nba.com/standings |
| S-SNAP-PHI | PHI W-L in data/raw/capture_2026-11-18/standings_2026-11-18.json | 12-3 | 13-3 | SUPERSEDED (+1 games since retrieval) | https://www.nba.com/standings |
| S-SNAP-PHX | PHX W-L in data/raw/capture_2026-11-18/standings_2026-11-18.json | 6-7 | 7-7 | SUPERSEDED (+1 games since retrieval) | https://www.nba.com/standings |
| S-SNAP-POR | POR W-L in data/raw/capture_2026-11-18/standings_2026-11-18.json | 9-5 | 9-5 | PASS | https://www.nba.com/standings |
| S-SNAP-SAC | SAC W-L in data/raw/capture_2026-11-18/standings_2026-11-18.json | 1-12 | 1-13 | SUPERSEDED (+1 games since retrieval) | https://www.nba.com/standings |
| S-SNAP-SAS | SAS W-L in data/raw/capture_2026-11-18/standings_2026-11-18.json | 12-3 | 12-3 | PASS | https://www.nba.com/standings |
| S-SNAP-TOR | TOR W-L in data/raw/capture_2026-11-18/standings_2026-11-18.json | 5-9 | 5-10 | SUPERSEDED (+1 games since retrieval) | https://www.nba.com/standings |
| S-SNAP-UTA | UTA W-L in data/raw/capture_2026-11-18/standings_2026-11-18.json | 2-13 | 3-13 | SUPERSEDED (+1 games since retrieval) | https://www.nba.com/standings |
| S-SNAP-WAS | WAS W-L in data/raw/capture_2026-11-18/standings_2026-11-18.json | 4-11 | 5-11 | SUPERSEDED (+1 games since retrieval) | https://www.nba.com/standings |
| S-MODEL-PHI | PHI W-L used by the published model | absent | [13, 3] | MISSING | https://www.nba.com/standings |
| S-MODEL-BOS | BOS W-L used by the published model | absent | [11, 4] | MISSING | https://www.nba.com/standings |
| S-MODEL-MIL | MIL W-L used by the published model | absent | [1, 14] | MISSING | https://www.nba.com/standings |
| S-MODEL-LAL | LAL W-L used by the published model | absent | [13, 3] | MISSING | https://www.nba.com/standings |
| S-HOME-PHI | PHI home record in the committed official snapshot | 6-2 | 6-2 | PASS | https://www.nba.com/standings |
| S-HOME-BOS | BOS home record in the committed official snapshot | 6-1 | 6-1 | PASS | https://www.nba.com/standings |
| S-HOME-MIA | MIA home record in the committed official snapshot | 4-3 | 5-3 | STALE | https://www.nba.com/standings |
| I-LATEST | the newest official injury release the repository holds | 11/17/26 11:00 AM (v4 index retrieved 2026-11-17T16:41:00Z) | 11/19/26 07:00 AM released 11/19/26, retrieved 2026-11-19T12 | STALE | https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-19_07_00AM.pdf |
| I-Beal-Bradley | Beal, Bradley status on the 11/19/26 07:00 AM ET report | no archived row | Out — Injury/Illness - Right Knee Injury Management | MISSING | https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-19_07_00AM.pdf |
| I-Harper-Dylan | Harper, Dylan status on the 11/19/26 07:00 AM ET report | no archived row | Out — Injury/Illness - Left Hip Soreness | MISSING | https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-19_07_00AM.pdf |
| I-Edwards-Anthony | Edwards, Anthony status on the 11/19/26 07:00 AM ET report | no archived row | Out — Injury/Illness - Right Knee Arthroscopy | MISSING | https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-19_07_00AM.pdf |
| I-Beringer-Joan | Beringer, Joan status on the 11/19/26 07:00 AM ET report | no archived row | Available — Injury/Illness - Face Mask | MISSING | https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-19_07_00AM.pdf |
| I-Avdija-Deni | Avdija, Deni status on the 11/19/26 07:00 AM ET report | no archived row | Questionable — Injury/Illness - Left Foot Inflammation / Sor | MISSING | https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-19_07_00AM.pdf |
| I-Morant-Ja | Morant, Ja status on the 11/19/26 07:00 AM ET report | no archived row | Out — Injury/Illness - Left Hamstring Strain | MISSING | https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-19_07_00AM.pdf |
| B-COVERAGE | per-player log rows published for game 0022600259 (HOU@IND, 2026-11-18) | 0 row(s) | 18 Houston + 17 Indiana player rows on the official box scor | MISSING | https://www.nba.com/game/hou-vs-ind-0022600259/box-score |
| B-ReedSheppard | Reed Sheppard line, 2026-11-18 HOU@IND | no row | 24:52 min, 20 pts, 4 reb, 2 ast | MISSING | https://www.nba.com/game/hou-vs-ind-0022600259/box-score |
| B-StevenAdams | Steven Adams line, 2026-11-18 HOU@IND | no row | 16:22 min, 2 pts, 5 reb, 2 ast | MISSING | https://www.nba.com/game/hou-vs-ind-0022600259/box-score |
| B-MarcusSmart | Marcus Smart line, 2026-11-18 HOU@IND | no row | 18:16 min, 4 pts, 4 reb, 2 ast | MISSING | https://www.nba.com/game/hou-vs-ind-0022600259/box-score |
| B-TariEason | Tari Eason line, 2026-11-18 HOU@IND | no row | 24:52 min, 4 pts, 11 reb, 3 ast | MISSING | https://www.nba.com/game/hou-vs-ind-0022600259/box-score |
| SET-0022600253 | settled final recorded for game 0022600253 | 111-102 | 111-102 | PASS | https://www.nba.com/game/nyk-vs-tor-0022600253 |
| SET-0022600255 | settled final recorded for game 0022600255 | 105-93 | 105-93 | PASS | https://www.nba.com/game/det-vs-sas-0022600255 |
| SET-0022600254 | settled final recorded for game 0022600254 | 105-106 | 105-106 | PASS | https://www.nba.com/game/por-vs-min-0022600254 |
| SET-0022600257 | settled final recorded for game 0022600257 | 132-107 | 132-107 | PASS | https://www.nba.com/game/uta-vs-lac-0022600257 |
| SET-0022600256 | settled final recorded for game 0022600256 | 114-118 | 114-118 | PASS | https://www.nba.com/game/cha-vs-lal-0022600256 |
| P-HORIZON | dates covered by the published originated lines | 2026-11-15..2026-11-18 (34 lines) | 2026-11-19 and 2026-11-20 are upcoming official slates | STALE | https://www.nba.com/games?date=2026-11-19 |
| P-SLATE-1119 | the four 2026-11-19 games appear in the published lines | 0/4 present | GSW@MEM, POR@MIL, NYK@MIN, LAC@SAS | FAIL | https://www.nba.com/games?date=2026-11-19 |
| J-REFRESH | outcome of the last ten scheduled refresh runs (gh run list --workflow=refresh.yml) | 10/10 concluded failure (2026-11-14T14:37Z … 2026-11-18T19:2 | a gate-passing scheduled refresh is what the brief requires | FAIL | https://github.com/wingbangboozle1-lang/NBA2/actions/workflows/refresh.yml |
| J-CAPTURE | did the capture leg of the last scheduled run succeed | capture: success (all four surfaces + v4), publish: failure | committed data/raw/capture_2026-11-18/* confirms the capture | PASS | https://github.com/wingbangboozle1-lang/NBA2/actions/runs/44381003145 |
| M-HCA-IDENTITY | hca equals sigma x (2p-1) for the published home-win rate | hca=0.7679 vs sigma*(2p-1)=0.7679 | p=0.5294 from 99-88 home games | PASS | https://www.nba.com/standings |
| M-HCA-SAMPLE | the home-win rate is measured over a stated sample | 187 home games = 2 x 188.0 club-games / 2 | home 99-88 = 0.5294 | PASS | https://www.nba.com/standings |
| M-HCA-PHI | PHI home split published in the model integrity block | 6-2 | 6-2 | PASS | https://www.nba.com/standings |
| M-HCA-BOS | BOS home split published in the model integrity block | 6-1 | 6-1 | PASS | https://www.nba.com/standings |
| M-HCA-MIA | MIA home split published in the model integrity block | 4-3 | 5-3 | STALE | https://www.nba.com/standings |
| Z-INPUT-DIGEST | digest over every input this audit read | 88bf3538a1efe80dcc62eab6e62cae41 | recomputed on every run; a changed digest means an input cha | PASS | https://github.com/wingbangboozle1-lang/NBA2/tree/main/audit/923eb342/verified |

## 7. Reproduce

```bash
python3 audit/923eb342/verify_published.py   # 82 checks -> audit/923eb342/report.json (deterministic)
python3 audit/923eb342/ingest.py             # verified rows -> audit/923eb342/verified/ (idempotent)
python3 audit/923eb342/build.py              # 13-page dashboard
python3 audit/923eb342/check.py              # links / per-row sources / reasoned blanks: 0 problems
```

Determinism was tested by running the audit twice and diffing `report.json`: byte-identical. The audit
digest excludes the wall clock — the only timestamps in it are the retrieval times recorded in the capture.
