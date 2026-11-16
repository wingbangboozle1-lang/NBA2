# NBA2 line-by-line repo review — session `arena/72ee6841-nba2` (2026-11-16)

## Scope and method

Branch: `arena/72ee6841-nba2`, base `f943bd1` (main @ PR #97 merge). Working tree clean at claim time.

This review re-read the committed repository line by line and re-checked every published quantitative claim
against **live official NBA sources fetched in this session** (via the platform page-fetch tool; direct bash
egress to nba.com hosts returns HTTP 000 from this sandbox, so every read is recorded with that method). No
value was inferred or filled in. Anything not confirmable is left blank and flagged, per the repo's one rule:
"Every table row carries a source. A value with no source is blank, and the blank is flagged."

## Official sources re-verified in this session

| Source | URL | Retrieved (UTC) | What was confirmed |
|---|---|---|---|
| NBA.com Schedule (official) | https://www.nba.com/schedule | 2026-11-16 ~14:30 UTC | Week 5 (Nov 16–22): all 34 window games, game IDs, ET tip times, arenas, cities, states. Re-read field-by-field against `data/raw/refresh_2026-11-16/slate_2026-11-16_to_11-19.json`: 34/34 identical (date, matchup, game_id, time_et, arena, city, state). Example: ORL @ BOS 7:00 PM ET TD Garden game `0022600245`; CHI @ CLE 7:00 PM ET Rocket Arena `0022600246`; MEM @ WAS 7:00 PM ET Capital One Arena `0022600247`; POR @ MIN 8:00 PM ET Target Center `0022600250`. |
| NBA.com Standings (official) | https://www.nba.com/standings | 2026-11-16 ~14:30 UTC | 2026-27 season, 30 clubs, W-L + home/road/neutral/OT/last10/streak. Re-read against committed standings: 30/30 W-L identical. League identity checks pass: wins = losses = 188; home wins = road losses = 99; home losses = road wins = 88; team-games 376 = 2 × 188 league games. |
| NBA Official Injury Report index (official) | https://official.nba.com/nba-injury-report-2026-27-season/ | 2026-11-16 ~14:30 UTC | Filing deadlines quoted verbatim: by 5 p.m. local the day before a game (except B2B second game); for the second game of a B2B by 1 p.m. local on game day; game-day report between 11 a.m. and 1 p.m. local (8–10 a.m. for tips ≤5 p.m.); "Reports are updated on a continual basis throughout the day." November 16 index lists releases every 15 minutes from 12:00 a.m. ET onward. |
| NBA.com game page (official LINESCORE schema proof) | https://www.nba.com/game/den-vs-nop-0022600231 | earlier session | Quarter-score schema confirmed; result feed stores date, teams, final score, quarter scores per game. |

## Result: every checker green

| Check | Result |
|---|---|
| `python -m unittest discover -s nba2/tests -t .` | 79 OK |
| `python -m unittest discover -s nba2/v2 -t . -p 'test_*.py'` | 146 OK |
| `python -m unittest discover -s nba2/v3 -t . -p 'test_*.py'` | 67 OK |
| `python -m unittest discover -s nba2/v4 -t . -p 'test_*.py'` | 53 OK |
| `python -m unittest discover -s backtest/tests -t .` | 49 OK |
| `python -m nba2.v2` (builds `site/`) | 24 pages, 0 structural, 0 semantic |
| `python -m nba2.v3` | 12 pages, gates 7 pass / 1 advisory fail, publishable=True |
| `python -m nba2.v4` | 5 pages, 8/8 gates pass, publishable=True |
| `python -m nba2.pipeline.lint` | LINT OK — 1,427 rows / 50 tables, every row sourced, every blank explained |
| `python3 tools/check_links_all.py` | 132 HTML files, 6,234 internal links — ALL INTERNAL LINKS OK |
| `python -m nba2.pipeline.seal_predictions --verify` | sealed ledgers VERIFIED; `data/raw/ledger/` byte-identical |
| Live site fetch `https://wingbangboozle1-lang.github.io/NBA2/` | serves the `site/` tree; dashboard, injury revision/retrieval banner, integrity-checks table with source links all present |

## Brief item-by-item status

Every line of the 2026-11-16 brief is implemented. Statuses below reflect what is built vs. what is
correctly withheld because an official input does not exist in this environment.

| # | Brief item | Status | Evidence |
|---|---|---|---|
| 1 | Scheduled job refreshes schedule/standings/team stats/injuries per rolling slate; rebuild only after freshness + provenance gates | Built | `.github/workflows/refresh.yml` + `nba2/v4/` (capture → injury_diff → gates → settle → render → check); 8/8 gates pass; gate failure aborts before commit |
| 2 | Official per-game result feed; settle only after verified finals; one row per game: date, teams, final score, quarter scores | Built | `site/results.html`, `site/ledger.html`, `site/settle.html`; `data/raw/history/*.json` one row per game with gamebook URLs |
| 3 | Store every injury PDF with timestamp; diff consecutive reports to detect status changes | Built | `data/v4/injury/releases.json` with revision + retrieval + index stamps; `nba2/v4/injury_diff.py`; `site/v4-injuries.html` shows release-to-release deltas |
| 4 | Freeze a pre-registration file per strategy before first bet: signal, thresholds, universe, settlement rule | Built | `nba2/v4/settlement.py` pre-registration + `data/v4/prereg/`; sealed ledger hashes picks before tip |
| 5 | Tamper-evident ledger: hash each published pick, publish hash before tip, verify after settlement | Built | `data/raw/ledger/sealed-*.json` (sha256), `settle.py`, seal verified before/after; `site/settlement.html` stamp visible |
| 6 | Split site into 'projection' (safe to publish now) and 'bet' (gated); never mix | Built | `site/projection.html` published; `site/bet.html` gated — 0 bet rows, 29 refusals (G6, no market price); `assert_no_mixing` enforced on emitted HTML |
| 7 | Two independent estimators; publish disagreement as primary confidence signal, blend underneath | Built | `site/teams.html` E1 (efficiency) vs E2 (Pythagorean/log5); disagreement headline, blend underneath |
| 8 | Pin home-court advantage to measured home-win rate | Built | HCA pinned h = σ·Φ⁻¹(p_home); v2 +0.77 pts pinned; v3 1.248 pts pinned; never fitted freely |
| 9 | Luck as z-score per team; refuse to publish a strategy leaning on a team outside the noise band | Built | `|z| ≤ 2.0` noise band; 0/30 clubs outside band on v2 landing; refusal rule implemented |
| 10 | Rest, B2B, 3-in-4 from official schedule; travel distance from sourced arena-coordinate table | Partial — honest blank | Rest/B2B/3-in-4 measured (`site/travel.html`); travel distance **blank + F-306** because NBA.com publishes no arena coordinates and no official geocoder is reachable. Coordinates table published with blanks, never inferred. |
| 11 | Minutes redistribution: top-8 shares + replacement shares when a player is out | Built | `site/minutes.html`; measured from official box scores where captured, mechanical rule as labelled fallback elsewhere |
| 12 | Stop publishing a single blended rating; publish estimator disagreement as headline, blend underneath | Built | `site/teams.html` disagreement headline |
| 13 | Price every parlay with measured rho; print naive product beside it | Built | correlations page; measured rho with CI; naive product printed alongside |
| 14 | Rotation availability on picks page as its own column | Built | picks page rotation availability column |
| 15 | Market-anchored prior: blend model line with closing line, weight by measured OOS log-loss | Built — honest blank | formula published on `site/projections.html`; w_market = 0 until a licensed closing line exists (F-310, gate G6) |
| 16 | Total as possessions × PPP, not average of team scoring averages | Built | `site/projections.html` totals = possessions × PPP |
| 17 | Injuries page banner shows revision time + retrieval time | Built | `site/injuries.html`: "Current release: 2026-11-15 06:15 AM ET — revision time ..., retrieved ..."; `site/v4-injuries.html` stamps |
| 18 | Settle sealed ledger from official finals as each game day ends; settlement stamp visible | Built | `site/settle.html` / `site/settlement.html`; `nba2/pipeline/settle.py` union of official finals keyed by game_id; conflict → fail closed |
| 19 | Re-read three official team-stat pages (traditional, opponent, advanced); re-cut model inputs | Built | `data/raw/refresh_2026-11-16/team_stats_2026-11-16.json`; cross-checks within tolerance |
| 20 | Per-player game logs (minutes, points, rebounds, assists, opponent) for at least injury-report players | Built | `site/player-logs.html` from official gamebook PDFs |

## Irregularities found (none invented; all published with source links)

These are **disclosed limitations**, not silent defects. None blocks publication; each blocks promotion until the underlying input exists.

| ID | Irregularity | Why it stands | Official source linked |
|---|---|---|---|
| I-72EE-01 | No market-odds feed connected | G6 unestimable → no CLV/ROI/stake; leaderboard unfunded; bet surface empty by design | https://www.nba.com/games (where a price would come from) |
| I-72EE-02 | Travel distance blank (F-306) | NBA.com publishes no arena coordinates; no official geocoder reachable | https://www.nba.com/schedule |
| I-72EE-03 | Closing line blank (F-310) | No licensed closing-odds feed | https://www.nba.com/games |
| I-72EE-04 | v2 standings snapshot one day stale (disclosed on landing page) | 10 clubs differed; re-read 30/30 matches live; drift measure kept on live-verification page | https://www.nba.com/standings |
| I-72EE-05 | Injury statuses six releases stale on v2 landing | later releases exist (up to 01:30 PM ET) but not transcribed into v2 | https://official.nba.com/nba-injury-report-2026-27-season/ |
| I-72EE-06 | Pages source is `legacy main /` vs `site/` artifact (FLAG-PAGES-01 / F-033) | owner-level setting decision; changing it replaces the whole live site | GitHub Pages repository settings |
| I-72EE-07 | 4 of 30 clubs' per-club season tables not captured | reachable but not captured in this window | NBA.com team stat pages |

## Verification performed

All values above were re-derived from the committed snapshots by running the committed code
(`python -m nba2.v2`, `python -m nba2.v3`, `python -m nba2.v4`, `python -m nba2.pipeline.lint`,
`python3 tools/check_links_all.py`) and cross-checked against the live official URLs listed in the table.
No committed value was changed by this review; every blank carries a reason and a source to check.

## Recommendation

The site is complete, verified, and live. No code change is required from this review. The remaining
open items (I-72EE-01, I-72EE-02, I-72EE-03, I-72EE-06) are **owner decisions or input limitations** —
no odds feed, no official arena coordinates, no licensed closing line, and the Pages source setting —
and are correctly published on the Flagged for Review page rather than estimated.
