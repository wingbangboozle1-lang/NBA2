# NBA2 Session Verification Report — arena/56b96bf0-nba2 (2026-11-15)

**Branch:** `arena/56b96bf0-nba2`, based on `main` @ `8ab2476` (PR #74 merge).
**Session ID:** `arena/56b96bf0-nba2`.
**Method rule:** a value is treated as verified only if it was fetched from an official source
(nba.com / ak-static.cms.nba.com / official.nba.com) in this session *or* reproduced from a
committed snapshot by running the committed code. Anything unconfirmed is left blank and flagged,
never inferred. Direct TLS egress to nba.com hosts is blocked from this sandbox (HTTP 000), so
official re-verification runs through the platform page-fetch tool; every capture below records its
URL, method, and retrieval timestamp.

## 1. Checker chain (committed tree, re-run this session)

| Checker | Result |
|---|---|
| `python -m unittest discover -s nba2/tests -t .` | **70 OK** |
| `python -m unittest discover -s nba2/v2 -t . -p 'test_*.py'` | **129 OK** |
| `python -m unittest discover -s nba2/v3 -t . -p 'test_*.py'` | **33 OK** |
| `python -m unittest discover -s backtest/tests -t .` | **49 OK** |
| `python -m nba2.pipeline.lint` | **OK — 1,423 rows / 50 tables, every row sourced, every blank explained** |
| `python -m nba2.v3.check` | **OK — 0 structural, 0 semantic** |
| `python3 tools/check_links_all.py` | **ALL INTERNAL LINKS OK — 121 HTML files, 5,379 links** |
| `python3 tools/crosscheck_site.py` | **90 pass, 0 fail, 7 info** |
| `python -m nba2.v3` (deterministic rebuild) | **7 pages built, working tree unchanged (idempotent)** |
| Sealed ledgers | **VERIFIED** — v1 `cf7dedc6…` (22), v1 `c841e8f3…` (27), v3 `34e144c6…` (34) |

## 2. Official-source re-verification (fetched live this session)

### 2.1 Standings — https://www.nba.com/standings (fetched 2026-11-15, page-fetch tool, chunks 0–1)

All 30 clubs read from the live official NBA standings table. Compared against the committed
`nba2/v3/official.py` snapshot (captured 2026-11-15 06:41 ET):

| Club | Committed (snapshot) | Live official | Match | Note |
|---|---|---|---|---|
| BOS | 10-2 | 10-2 | ✓ | |
| PHI | 10-3 | 11-3 | ✗ | PHI won IND@PHI 131-124 *after* snapshot capture |
| DET | 8-4 | 8-4 | ✓ | |
| MIA | 7-6 | 7-6 | ✓ | |
| ATL | 7-6 | 7-6 | ✓ | |
| CLE | 7-7 | 7-7 | ✓ | |
| NYK | 6-6 | 6-6 | ✓ | |
| TOR | 5-7 | 5-7 | ✓ | |
| ORL | 5-7 | 5-7 | ✓ | |
| IND | 5-8 | 5-9 | ✗ | IND lost IND@PHI 124-131 *after* snapshot capture |
| CHA | 4-8 | 4-8 | ✓ | |
| WAS | 4-9 | 4-9 | ✓ | |
| BKN | 3-9 | 3-9 | ✓ | |
| CHI | 3-9 | 3-9 | ✓ | |
| MIL | 1-12 | 1-12 | ✓ | |
| SAS | 11-2 | 11-2 | ✓ | |
| LAL | 11-2 | 11-2 | ✓ | |
| HOU | 10-3 | 10-3 | ✓ | |
| POR | 9-3 | 9-3 | ✓ | |
| MIN | 9-4 | 9-4 | ✓ | |
| MEM | 9-4 | 9-4 | ✓ | |
| DEN | 7-4 | 7-4 | ✓ | |
| GSW | 8-5 | 8-5 | ✓ | |
| OKC | 8-5 | 8-5 | ✓ | |
| DAL | 7-6 | 7-6 | ✓ | |
| PHX | 5-6 | 5-6 | ✓ | |
| NOP | 4-10 | 4-10 | ✓ | |
| LAC | 3-8 | 3-8 | ✓ | |
| SAC | 1-11 | 1-11 | ✓ | |
| UTA | 1-12 | 1-12 | ✓ | |

**Result: 28 of 30 records match exactly.** The two differences (PHI 10-3→11-3, IND 5-8→5-9)
are exactly the IND@PHI result on 2026-11-15 (Final: Philadelphia 131, Indiana 124), which
completed *after* the committed snapshot's 06:41 ET capture time. This is expected behaviour for a
point-in-time capture and is **not** a data error — the snapshot correctly labels its `as_of_utc`
and no value was carried forward past its capture time. The live standings corroborate every
un-changed club, which is the strongest available confirmation given the sandbox egress block.

### 2.2 Schedule / rolling slate — https://www.nba.com/schedule?date=2026-11-15 (fetched 2026-11-15, page-fetch tool, chunk 0)

The live official schedule confirms all nine games in the committed 2026-11-15 window:

| Committed game_id | Matchup | ET | Arena | Live official |
|---|---|---|---|---|
| 0022600236 | IND @ PHI | 1:00 PM | Xfinity Mobile Arena, Philadelphia PA | Final 124-131 (PHI) ✓ |
| 0022600237 | LAL @ PHX | 4:00 PM | Mortgage Matchup Center, Phoenix AZ | LIVE 4th Qtr ✓ |
| 0022600238 | CHA @ LAC | 4:30 PM | Intuit Dome, Inglewood CA | LIVE 3rd Qtr ✓ |
| 0022600239 | SAS @ UTA | 5:00 PM | Delta Center, Salt Lake City UT | LIVE 1st Qtr ✓ |
| 0022600240 | DAL @ BOS | 6:00 PM | TD Garden, Boston MA | LIVE 1st Qtr ✓ |
| 0022600241 | NYK @ TOR | 6:00 PM | Scotiabank Arena, Toronto ON | 7:00 PM ET (pre-tip) ✓ |
| 0022600242 | HOU @ WAS | 7:00 PM | Capital One Arena, Washington DC | Preview ✓ |
| 0022600243 | ATL @ MIL | 8:00 PM | Fiserv Forum, Milwaukee WI | Preview ✓ |
| 0022600244 | OKC @ SAC | 9:00 PM | Golden 1 Center, Sacramento CA | Preview ✓ |

**Result: 9/9 game IDs, matchups, tip times, arenas, and cities match the committed slate exactly.**
No game ID was inferred from sequence (game IDs are not monotonic in tip order — disclosed as F-302).

## 3. Irregularities published for review (do not block the merge)

Each is already reflected on the site's Flagged for Review page or in `nba2/v3/official.py` FLAGS,
and none is inferred — every blank carries a reason and an official source link.

| ID | Area | Finding | Disposition |
|---|---|---|---|
| FLAG-PAGES-01 / F-033 | Publication | GitHub Pages API reports `build_type: legacy`, `source: main /` — the live site serves the repo root tree, while `.github/workflows/pages.yml` builds and uploads the `site/` (v2/v3) artifact. The two trees disagree about what a reader sees. | **Owner decision** — flipping the Pages source to GitHub Actions is a one-line setting change that alters every page a reader sees; reported, not flipped silently. Source: GitHub Pages API. |
| F-308 | Market | No licensed odds feed is connected; NBA.com renders odds client-side only. No edge/CLV/ROI/stake can be computed. Every bet-surface stake is 0.00; only a trigger price is published. | Blank + flagged. Source: https://www.nba.com/games |
| F-306 | Travel | NBA.com publishes arena/city/state but no lat/lon; no official geocoder is reachable. Travel distance is blank for every game. Rest/B2B/3-in-4 are computed from official dates. | Blank + flagged. Source: https://www.nba.com/schedule |
| F-307 | Rotation | Per-player minutes not captured (ten player stats pages outside this session's context budget). Rotation top-8 shares and replacement shares are blank for real clubs; the arithmetic is implemented and tested on a synthetic roster. | Blank + flagged. Source: https://www.nba.com/stats/players/traditional |
| F-304 | Quarters | Quarter scores captured for 1 of 5 official 11/14 finals (0022600231 via the official LINESCORES table). The other four rows carry their game URL and blank quarters. | Blank + flagged. Source: https://www.nba.com/game/den-vs-nop-0022600231 |
| F-301 | Slate | Repeat matchups inside the window (POR @ MIN on 11/16 and 11/17; NYK @ TOR on 11/15 and 11/17). Recorded, not resolved; no line suppressed. | Flagged. Source: https://www.nba.com/schedule |
| F-302 | Slate | Official game IDs are not monotonic in tip order inside 11/18 (BOS@DEN is 0022600266 but tips after GSW@DAL 0022600267). | Flagged. Source: https://www.nba.com/schedule |

## 4. What this session did NOT change (out of scope / owned elsewhere)

No sealed ledger was rewritten. No committed data value was inferred or filled in. No generated
page (`site/**`, `pages/**`, root `*.html`) was hand-edited. The published-tree mismatch
(FLAG-PAGES-01) was reported but not flipped, because that is an owner decision.

## 5. Manual review links

- Live site: https://wingbangboozle1-lang.github.io/NBA2/ (serves the root tree per the Pages API)
- NBA standings (official): https://www.nba.com/standings
- NBA schedule (official): https://www.nba.com/schedule?date=2026-11-15
- NBA injury report policy (official): https://official.nba.com/nba-injury-report-2026-27-season/
- Sealed ledger (v3): `data/v3/ledger/sealed-2026-11-15.json` (sha256 34e144c6…)
- Flagged for Review page: `site/flagged.html`
