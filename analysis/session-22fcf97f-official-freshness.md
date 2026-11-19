# Official-source freshness probe — session `arena/22fcf97f-nba2`

**Clock at start (sandbox, UTC):** 2026-11-19 12:16:48 (= 07:16 ET).
**Method:** direct reads of official NBA pages through the `fetch_page` tool. The bash sandbox
cannot reach `cdn.nba.com`, `www.nba.com`, `official.nba.com` or `ak-static.cms.nba.com`
(HTTP 000 on every probe), so nothing below was downloaded as bytes into the repo.
The fetch tool returns page text only, so no PDF bytes were archived in this session.
Retrieval times below are the sandbox clock at the time of each read (within the same minute window, 12:17–12:20 UTC).

Nothing in this file changes a model input, a sealed ledger, a settlement file, generated site data or site navigation.

## 1. Injury reports — 11/19 revisions read directly

| Revision (ET, as titled in PDF) | Source URL | Retrieved (UTC, approx.) | Result |
|---|---|---|---|
| 11/19/26 07:00 AM | https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-19_07_00AM.pdf | 12:17 | Read. Rows parsed (see §1a). |
| 11/19/26 07:15 AM | https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-19_07_15AM.pdf | 12:18 | Read. Same readable rows as 07:00; **no status change detected in the readable rows.** |

**Index page status.** The official index https://official.nba.com/nba-injury-report-2026-27-season/ (read at 12:16–12:17 UTC) listed 11/19 revisions only through **07:00 AM ET**. The 07:15 AM PDF was already live when fetched directly. The index therefore lagged by at least one revision at read time (cause unknown; the index may be cached). Flagged, not resolved.

**Diff between consecutive revisions (07:00 → 07:15), readable rows only:** no added or removed rows and no status changes. This is a text-level diff of the two fetched PDFs and is limited by the caveat in §1a.

### 1a. Extraction caveat (flagged)
The PDF text on continuation pages loses its header row and some team/matchup columns (for example rows that show only a player, status and reason, with no team name). Those rows **cannot be attributed to a team with certainty** from this read, so they are not transcribed below. The PDF also prints times without AM/PM (for example `08:00 (ET)` for games the schedule lists at 8:00 PM ET), so those times are not copied as-is.

### 1b. Readable 11/19 injury rows (07:15 AM revision, attributed only where the row shows the team)
Status and reason are copied from the PDF text. Matchup is taken from the same row.

| Matchup | Team | Player | Status | Reason (as printed) |
|---|---|---|---|---|
| LAC@SAS | LA Clippers | Beal, Bradley | Out | Injury/Illness - Right Knee Injury Management |
| LAC@SAS | LA Clippers | Ingram, Brandon | Out | Injury/Illness - Right Heel Surgery |
| LAC@SAS | LA Clippers | Martinelli, Nick | Out | G League - Two-Way |
| LAC@SAS | LA Clippers | Miller, Jordan | Out | Injury/Illness - Left Rotator Cuff Surgery |
| LAC@SAS | San Antonio Spurs | Brown, Maliq | Out | G League - Two-Way |
| LAC@SAS | San Antonio Spurs | Gillespie, Ja'Kobi | Out | G League - Two-Way |
| LAC@SAS | San Antonio Spurs | Harper, Dylan | Out | Injury/Illness - Left Hip Soreness |
| LAC@SAS | San Antonio Spurs | Harris, Tobias | Out | Injury/Illness - Left Calf Strain |
| LAC@SAS | San Antonio Spurs | Quaintance, Jayden | Out | Injury/Illness - Right Knee Surgery |
| NYK@MIN | Minnesota Timberwolves | Beringer, Joan | Available | Injury/Illness - Face Mask |
| NYK@MIN | Minnesota Timberwolves | Clark, Jaylen | Out | Injury/Illness - Right Hamstring Strain |
| NYK@MIN | Minnesota Timberwolves | DiVincenzo, Donte | Out | Injury/Illness - Right Achilles Tendon Repair / Surgery |
| NYK@MIN | Minnesota Timberwolves | Edwards, Anthony | Out | Injury/Illness - Right Knee Arthroscopy |
| POR@MIL | Portland Trail Blazers | Avdija, Deni | Questionable | Injury/Illness - Left Foot Inflammation / Soreness |
| POR@MIL | Portland Trail Blazers | Camara, Toumani | Questionable | Injury/Illness - Abdominal Soreness |
| POR@MIL | Portland Trail Blazers | Carlson, Branden | Available | Injury/Illness - Face Mask |
| POR@MIL | Portland Trail Blazers | Krejci, Vit | Out | Injury/Illness - Left Ankle Fracture |
| POR@MIL | Portland Trail Blazers | Morant, Ja | Out | Injury/Illness - Left Hamstring Strain |
| POR@MIL | Portland Trail Blazers | Sharpe, Shaedon | Out | Injury/Illness - Right Meniscus Surgery |
| POR@MIL | Portland Trail Blazers | Williams III, Robert | Out | Rest |
| POR@MIL | Portland Trail Blazers | Youngblood, Chris | Out | Injury/Illness - Right Heel Contusion / Bone Bruise |
| POR@MIL | (team unreadable) | Kuminga, Jonathan | Questionable | Injury/Illness - Right Shoulder Contusion — **team unverified** (row has no team column) |
| POR@MIL | (team unreadable) | Pullin, Zyon | Questionable | Injury/Illness - Right Quadriceps Contusion — **team unverified** |

GSW@MEM: both teams show **NOT YET SUBMITTED** in the 07:15 revision. No player rows are readable for this game. Left blank, flagged unverified.

## 2. Official schedule — rolling window 11/19 → 11/21 (3 days)

Source: https://www.nba.com/schedule (read 12:18–12:20 UTC, "Week 5 (Nov 16 - Nov 22)" and "Week 6" sections).
Per-game links are the "Preview" links on that page. Times are as printed (ET).

**Thu 11/19 — 4 games (headline on page: "4 Games")**
- GSW @ MEM — 8:00 PM ET — https://www.nba.com/game/gsw-vs-mem-0022600270
- POR @ MIL — 8:00 PM ET — https://www.nba.com/game/por-vs-mil-0022600271
- NYK @ MIN — 8:00 PM ET — https://www.nba.com/game/nyk-vs-min-0022600272
- LAC @ SAS — 8:00 PM ET — https://www.nba.com/game/lac-vs-sas-0022600273

**Fri 11/20 — 9 games (headline: "9 Games")**
- CHA @ ATL — 7:00 PM ET — https://www.nba.com/game/cha-vs-atl-0022600043
- ORL @ BKN — 7:30 PM ET — https://www.nba.com/game/orl-vs-bkn-0022600044
- IND @ CLE — 7:30 PM ET — https://www.nba.com/game/ind-vs-cle-0022600045
- TOR @ DET — 7:30 PM ET — https://www.nba.com/game/tor-vs-det-0022600046
- WAS @ CHI — 8:00 PM ET — https://www.nba.com/game/was-vs-chi-0022600047
- NOP @ OKC — 8:00 PM ET — https://www.nba.com/game/nop-vs-okc-0022600048
- PHX @ UTA — 9:30 PM ET — https://www.nba.com/game/phx-vs-uta-0022600049
- HOU @ DEN — 10:00 PM ET — https://www.nba.com/game/hou-vs-den-0022600050
- SAC @ LAL — 10:00 PM ET — https://www.nba.com/game/sac-vs-lal-0022600051

**Sat 11/21 — 6 games (headline: "6 Games")**
- MIL @ PHI — 1:00 PM ET — https://www.nba.com/game/mil-vs-phi-0022600274
- POR @ NYK — 7:30 PM ET — https://www.nba.com/game/por-vs-nyk-0022600275
- LAC @ DAL — 8:00 PM ET — https://www.nba.com/game/lac-vs-dal-0022600276
- MEM @ MIN — 8:00 PM ET — https://www.nba.com/game/mem-vs-min-0022600277
- NOP @ SAS — 8:00 PM ET — https://www.nba.com/game/nop-vs-sas-0022600278
- BOS @ SAC — 10:00 PM ET — https://www.nba.com/game/bos-vs-sac-0022600279

Total in the 3-day window: **19 games**. Note the schedule page labels each game "away-vs-home" in its URL slug; the "@" form above follows the page's venue listing (for example, GSW@MEM is played at FedExForum, Memphis).

## 3. Official finals on the schedule page — 11/18 (12 games)

Source: https://www.nba.com/schedule (read 12:18 UTC). Final scores as printed, **away first**. Quarter scores are **not on this page** and are left blank.

| Game ID | Away | Away pts | Home | Home pts | Venue (as printed) | Official game page |
|---|---|---|---|---|---|---|
| 0022600258 | MEM | 124 | CLE | 121 | Rocket Arena, Cleveland, OH | https://www.nba.com/game/mem-vs-cle-0022600258 |
| 0022600259 | HOU | 119 | IND | 104 | Gainbridge Fieldhouse, Indianapolis, IN | https://www.nba.com/game/hou-vs-ind-0022600259 |
| 0022600260 | MIL | 130 | MIA | 137 | Kaseya Center, Miami, FL | https://www.nba.com/game/mil-vs-mia-0022600260 |
| 0022600261 | PHI | 121 | ORL | 116 | Kia Center, Orlando, FL | https://www.nba.com/game/phi-vs-orl-0022600261 |
| 0022600262 | CHI | 137 | BKN | 107 | Barclays Center, Brooklyn, NY | https://www.nba.com/game/chi-vs-bkn-0022600262 |
| 0022600263 | WAS | 103 | TOR | 99 | Scotiabank Arena, Toronto, ON | https://www.nba.com/game/was-vs-tor-0022600263 |
| 0022600264 | DET | 122 | NOP | 109 | Smoothie King Center, New Orleans, LA | https://www.nba.com/game/det-vs-nop-0022600264 |
| 0022600265 | ATL | 117 | OKC | 112 | Paycom Center, Oklahoma City, OK | https://www.nba.com/game/atl-vs-okc-0022600265 |
| 0022600267 | GSW | 94 | DAL | 116 | American Airlines Center, Dallas, TX | https://www.nba.com/game/gsw-vs-dal-0022600267 |
| 0022600266 | BOS | 101 | DEN | 105 | Ball Arena, Denver, CO | https://www.nba.com/game/bos-vs-den-0022600266 |
| 0022600268 | UTA | 109 | LAL | 97 | Crypto.com Arena, Los Angeles, CA | https://www.nba.com/game/uta-vs-lal-0022600268 |
| 0022600269 | PHX | 128 | SAC | 107 | Golden 1 Center, Sacramento, CA | https://www.nba.com/game/phx-vs-sac-0022600269 |

Away/home assignment is taken from the page's game-URL slug (`away-vs-home`) and cross-checked against the venue city for each row (for example, Cleveland venue for MEM–CLE, so CLE is home). The "Venue" column is the page's own text.

## 4. Repo comparison (what the committed data says)

- `data/raw/capture_2026-11-18/finals_2026-11-18.json` is named for 11/18 and retrieved `2026-11-18T19:30:20Z`, but **contains 0 rows dated 2026-11-18**. Its records are 11/17 games. The file name does not match its contents.
- Consequence: the committed official per-game result feed does **not** contain the 12 final 11/18 games in §3. The 11/18 finals are therefore **not settled** in the repo. This session did not settle anything (settlement is outside this probe's scope and the sealed ledgers were not touched).
- `data/raw/pdf/` holds 37 files, the latest injury PDFs are 11/17 and 11/18. **No 11/19 PDF is archived in the repo.** Archiving bytes needs a network path the sandbox does not have; the nightly workflow is the intended path.

## 5. Irregularities flagged for review

1. **Index lag** — the official injury index read at 12:16–12:17 UTC stopped at 07:00 AM ET 11/19; the 07:15 AM PDF was already published. Source: https://official.nba.com/nba-injury-report-2026-27-season/
2. **PDF time format** — PDF rows print `08:00 (ET)` where the schedule says `8:00 PM ET`. Times are not copied from the PDF. Sources: https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-19_07_15AM.pdf and https://www.nba.com/schedule
3. **PDF column loss** — continuation-page rows lack team/header columns (for example Kuminga, Jonathan and Pullin, Zyon). Team attribution unverified; not transcribed as a team fact.
4. **Repo file-name mismatch** — `data/raw/capture_2026-11-18/finals_2026-11-18.json` contains 11/17 rows only (0 rows for 11/18). The 12 official 11/18 finals in §3 are missing from the repo's result feed.
5. **Missing 11/19 PDF archive** — no 11/19 injury PDF bytes in `data/raw/pdf/`.
6. **Quarter scores absent** for 11/18 on the schedule page; left blank.

## 6. What this does not do

- It does not compute a model, a line, a pick, a strategy result or a bet.
- It does not change any file the other open PRs own (#130 `arena/6023d517-nba2`, #131 `arena/8c7c8828-nba2`).
- It does not write any PDF bytes into the repo.
- It does not claim a full re-read of standings, team stats or the other official pages; those are outside this probe.

## 7. Review links

- NBA schedule — https://www.nba.com/schedule
- Official injury-report index — https://official.nba.com/nba-injury-report-2026-27-season/
- 11/19 07:00 AM injury PDF — https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-19_07_00AM.pdf
- 11/19 07:15 AM injury PDF — https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-19_07_15AM.pdf
- NBA standings — https://www.nba.com/standings
