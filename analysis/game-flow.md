# Injury Impact, Rotation Minutes & Game Flow Analysis

Snapshot basis: [official NBA injury report, 2026-11-13 5:15 p.m. ET](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_05_15PM.pdf)
(via [official.nba.com](https://official.nba.com/nba-injury-report-2026-27-season/)).
Full table: [`data/injury-report-2026-11-13.csv`](data/injury-report-2026-11-13.csv) — every row sourced.
Analyst flow notes are **judgments built on verified facts**; each fact is linked.

> **Tonight is an injury avalanche.** Out tonight: Curry (GSW), Haliburton (IND),
> Banchero (ORL), Mobley (CLE), Caleb Wilson (CHI's leading scorer), Morant (POR),
> plus long-term outs across UTA/HOU/OKC/LAC. All 9 games are Emirates NBA Cup
> group games.

## Friday 2026-11-13 (9 games)

| Game (source) | Injury/rotation impact (official) | Game flow read |
|---|---|---|
| [NYK @ IND](https://www.nba.com/game/nyk-vs-ind-0022600034) | IND: **Haliburton OUT** (hamstring), Nesmith Q, McConnell P, Furphy/Sheppard OUT. NYK: no listed absences | IND's creation collapses to Siakam isolations; pace drops, half-court grind. NYK (KAT 20.9/13.5) owns the glass. Projected total 223.0 (below 228.1 mean) → Under lean. Model: NYK −9.5 |
| [MIL @ ORL](https://www.nba.com/game/mil-vs-orl-0022600035) | ORL: **Banchero OUT** (high ankle), Isaac/Penda/Nelson OUT; Suggs available (knee bone bruise). MIL: clean report | Franz Wagner (23.5/6.5/7.9) becomes the entire offense against the league's 2nd-worst record (MIL 1-11). Blowout risk on the Magic side (−7.5); watch Suggs minutes in his return |
| [CLE @ MIA](https://www.nba.com/game/cle-vs-mia-0022600036) | CLE: **Mobley OUT** (toe), Merrill/Tomlin OUT. MIA: **Giannis Available** (wrist), Klay Probable, Larsson Doubtful | Giannis (27.7/12.6) vs a Mobley-less CLE frontcourt is the paint mismatch of the night. MIA lean but model margin only 1.5 — **no pick** (selectivity gate). Cup group B 1-0 vs 1-0 |
| [ATL @ CHI](https://www.nba.com/game/atl-vs-chi-0022600037) | CHI: **Caleb Wilson OUT** (hand fracture) — their leading scorer (18.9) — Powell Q, Swain Q. ATL: depth outs (Veesaar, Gueye, Newell) core intact | CHI (1-9, league-worst adj. defense) is a blowout-profile game: teammate correlations rise in blowouts (empirical +0.03…+0.07) but star-prop legs are banned there (r −0.2…−0.4). Model: ATL −12.5 |
| [MEM @ NOP](https://www.nba.com/game/mem-vs-nop-0022600038) | NOP: **Murray, Murphy III, Missi, Watford OUT**, Mathurin Q. MEM: Edey/Pippen/Post OUT | NOP (worst adj. defense 122.24) is running on fumes; Zion (21.7) vs a Memphis frontcourt without Edey. Both teams play again tomorrow — **B2B both sides**, minutes management risk. Model: MEM −12.0 |
| [UTA @ HOU](https://www.nba.com/game/uta-vs-hou-0022600039) | UTA: **Jackson Jr., Markkanen, Nurkic OUT** (entire frontcourt). HOU: **Smart OUT (3-game league suspension — [official release](https://official.nba.com/rockets-smart-suspended))**, Adams/Capela OUT | Largest model margin of the slate (HOU −23.0): #1 adj. rating (HOU +13.22) vs UTA's G-League shell (1-11). Both frontcourts thin → small-ball variance, garbage-time prop distortion. Under 222.5 lean |
| [GSW @ SAS](https://www.nba.com/game/gsw-vs-sas-0022600040) | GSW: **Curry OUT** (oblique tear), Butler/Porzingis/Moody/Williams OUT. SAS: Fox Q, Vassell Q, Harris OUT | Wembanyama (30.3/11.7) vs a Curry-less GSW (loses 27.8 PPG of creation). If Fox sits, SAS leans even harder on Wemby usage → his props strengthen, game flow slows. Model: SAS −8.0 |
| [POR @ SAC](https://www.nba.com/game/por-vs-sac-0022600041) | POR: **Morant OUT** (hamstring), Sharpe/Krejci OUT. SAC: Achiuwa/Raynaud/Simmons OUT | Avdija (23.0/6.1/6.5) vs the Acuff Jr. show (26.2/3.8/7.3 as a rookie on a 1-10 team — usage is empty-calorie). POR −17.5; SAC's garbage-time points make team-total unders dangerous |
| [OKC @ LAC](https://www.nba.com/game/okc-vs-lac-0022600042) | OKC: **Holmgren, J. Williams, Wallace, Sorber, J. Williams OUT** (5-man hole). LAC: Beal/Ingram/Miller OUT | SGA (29.7) alone vs a skeleton LAC (2-8). OKC's elite adj. defense (105.15) drives Under 220.0 lean. Depth-chart minutes for OKC role players are the prop angle |

## Saturday 2026-11-14 (5 games) — report partial at snapshot

| Game (source) | Verified status | Flow / rest read |
|---|---|---|
| [DEN @ NOP](https://www.nba.com/game/den-vs-nop-0022600231) | NOP report pending (was decimated Nov 13); DEN clean | NOP **B2B** + worst adj. defense vs Jokić (23.5/10.8/9.0). Over 234.0 lean — offense vs matador defense. Model: DEN −10.0 |
| [DAL @ CLE](https://www.nba.com/game/dal-vs-cle-0022600232) | DAL: **Lively II OUT** (foot), Christie Q. CLE: Martin available | Both teams **B2B** (DAL off a 39-point loss at MIN on Nov 12 — [box](https://www.cbssports.com/nba/gametracker/boxscore/NBA_20261112_DAL@MIN/)). Model margin < 1 → no pick; watch fatigue |
| [DET @ MIA](https://www.nba.com/game/det-vs-mia-0022600233) | DET: Duren/Isaiah Joe OUT. MIA report pending | Both **B2B** (DET off 144-140 OT at WAS — massive minutes). Cade (25.0/5.2/7.9) vs Giannis. Model: DET −4.0 |
| [BKN @ MEM](https://www.nba.com/game/bkn-vs-mem-0022600234) | BKN: Traore P, Brown Q. MEM pending | MEM **B2B** but home vs Randle-led BKN (3-8). Model: MEM −14.5 |
| [CHI @ MIN](https://www.nba.com/game/chi-vs-min-0022600235) | MIN: **Edwards OUT (knee arthroscopy)**, DiVincenzo OUT. CHI pending | ⚠️→✓ **Model flag raised and resolved during build:** the first run priced Edwards as "rotation" (uncollected baseline) and produced MIN −28.0. After pulling verified baselines (Edwards 33.3 PPG — [BRef](https://www.basketball-reference.com/leagues/NBA_2027_per_game.html)), the re-run gives **MIN −25.0**, Edwards charged at star tier. Residual caution: CHI also **B2B**, and MIN has played only 4 games with Edwards |

## Sunday–Monday (15th–16th) — situational only (official reports due day-of)

Injury-unadjusted by design (`PENDING` in [`data/picks.csv`](data/picks.csv)).

* **SUN:** DAL plays its 3rd game in 4 days (at CLE → at BOS, road B2B) — Boston
  (10-2, +6.18 adj.) is the rested side; POR @ MIN, SAS @ UTA (both teams 1-day
  rest), LAL (league-best 11-2) at PHX.
* **MON:** four B2B teams: **PHI** (at BKN, road), **HOU** (at MIA, road + 3-in-4),
  **WAS** (vs MEM, home), **PHX** (at DEN with travel). PHI's record (10-3) is
  +4.2 wins ahead of its rating expectation ([luck ledger](data/luck-table.csv)) —
  fade-the-public spot at BKN. NOP plays its 3rd game in 4 days vs GSW.

## Rotation-minutes tracking method (going forward)

1. Pull the day's latest official report (they refresh every 15 min on game days —
   [report index](https://official.nba.com/nba-injury-report-2026-11-13/)).
2. Recompute team injury impact (status × tier) and re-run [`scripts/model.py`](scripts/model.py).
3. Compare minutes consequences: Out star → usage redistribution to the team's
   verified next options (only leader production is currently verified — full
   rotation production data is Q-4).
4. Flag any line move > 2 pts from the prior snapshot as **line-stability risk**
   (gate G3 context).

## Verified cross-cutting facts used above

* Marcus Smart (HOU) suspended 3 games w/o pay, starts Nov 13 — [official.nba.com](https://official.nba.com/rockets-smart-suspended).
* Nov 12 results (rest context): TOR 112 @ PHI 123 ([CBS/AP](https://www.cbssports.com/nba/gametracker/boxscore/NBA_20261112_TOR@PHI/)); DAL 94 @ MIN 133 ([CBS/AP](https://www.cbssports.com/nba/gametracker/boxscore/NBA_20261112_DAL@MIN/)); DET 144 @ WAS 140 OT; CHA 96 @ PHX 101 ([nba-grid](https://nba-grid.com/nba-today/), trusted secondary).
* PHI played Nov 12 without LeBron James (back, 3rd straight absence) — [CBS/AP](https://www.cbssports.com/nba/gametracker/boxscore/NBA_20261112_TOR@PHI/). TOR without Kawhi Leonard (knee) and Scottie Barnes (groin). Statuses for Nov 15–16 pending official reports.
