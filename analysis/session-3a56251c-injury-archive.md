# Session `arena/3a56251c-nba2` — official injury-report archive (task 3A-03)

Built by `python -m nba2.injury_archive` from the four official PDFs in `data/raw/pdf/`. Nothing was fetched over the network. Machine-readable output: `data/injuries/archive/archive.json`. Parser: `nba2/injury_archive/parse.py`. Checks and diffs: `archive.py`. Tests: `nba2/tests/test_injury_archive.py` (13 tests; 11 run without `pypdf`, all 13 with it).

## Sources (official)

- NBA Official Injury Report index: https://official.nba.com/nba-injury-report-2026-27-season/ (the filing rules and release list)
- 11/16/26 09:30 AM ET release: https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-16_09_30AM.pdf  (stored bytes: `data/raw/pdf/Injury-Report_2026-11-16_09_30AM.pdf`, sha256 `8e9592936b389f74eee82306656679cd2d7cd2dc42fc7671dbb14f67465cac28`)
- 11/16/26 01:00 PM ET release: https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-16_01_00PM.pdf  (stored bytes: `data/raw/pdf/Injury-Report_2026-11-16_01_00PM.pdf`, sha256 `e0dbe404b34b616c0acb18427966dad7058ac3e4a743cd76ea46f7e8c7550152`)
- 11/16/26 02:15 PM ET release: https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-16_02_15PM.pdf  (stored bytes: `data/raw/pdf/Injury-Report_2026-11-16_02_15PM.pdf`, sha256 `588d3b9697a58f1ee29f90554ee029c869f5191169615c0790f9eb25a6f58035`)
- 11/17/26 09:45 AM ET release: https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-17_09_45AM.pdf  (stored bytes: `data/raw/pdf/Injury-Report_2026-11-17_09_45AM.pdf`, sha256 `e28bb978bcb099abfb132dcd852ec0fedc8b76c216f1bf569a95917ab6f4c93c`)

## Releases

| Release | Revision (ET) | PDF creation (ET) | Retrieved (UTC) | Retrieval record | Player rows | Teams NOT YET SUBMITTED | Parse problems |
|---|---|---|---|---|---|---|---|
| 11/16/26 09:30 AM | 2026-11-16T09:30:00-05:00 | 2026-11-16T09:30:03-05:00 | 2026-11-16T14:52:00Z | data/raw/refresh_2026-11-16/injury_transcript_20261116_0930AM_superseded.json | 57 | 15 | 0 |
| 11/16/26 01:00 PM | 2026-11-16T13:00:00-05:00 | 2026-11-16T13:00:04-05:00 | 2026-11-16T18:38:00Z | data/raw/refresh_2026-11-16/injury_transcript_20261116_0100PM.json | 75 | 12 | 0 |
| 11/16/26 02:15 PM | 2026-11-16T14:15:00-05:00 | 2026-11-16T14:15:04-05:00 | not recorded | not recorded in the repository | 76 | 11 | 0 |
| 11/17/26 09:45 AM | 2026-11-17T09:45:00-05:00 | 2026-11-17T09:45:02-05:00 | not recorded | not recorded in the repository | 33 | 26 | 0 |

## Checks per release

| Release | Status words in PDF text = parsed rows | NOT YET SUBMITTED in PDF text = parsed | Player names in PDF text | Stored .txt agrees | PDF creation = header (±1 min) | Blocks with no printed time | One-team games |
|---|---|---|---|---|---|---|---|
| 11/16/26 09:30 AM | 57 = 57 | 15 = 15 | all | n/a (no .txt) | yes | MEM@WAS, ORL@BOS, PHI@BKN, POR@MIN | — |
| 11/16/26 01:00 PM | 75 = 75 | 12 = 12 | all | n/a (no .txt) | yes | MEM@WAS, ORL@BOS, PHI@BKN, POR@MIN | — |
| 11/16/26 02:15 PM | 76 = 76 | 11 = 11 | all | yes | yes | MEM@WAS, ORL@BOS, PHI@BKN, POR@MIN | — |
| 11/17/26 09:45 AM | 33 = 33 | 26 = 26 | all | yes | yes | DET@NOP, GSW@DAL, MEM@CLE, MIL@MIA, PHI@ORL, POR@MIN, UTA@LAL, WAS@TOR | NYK@TOR |

## Consecutive diffs

Keyed by (game date, matchup, team, player). A player absent from a later release is listed as *absent*; the PDF prints no reason, and for a game dated before the later release that reflects the game date passing.

### 2026-11-16_0930AM → 2026-11-16_0100PM

Added 18 · absent 0 · status changed 3 · reason changed 1 · team newly NOT YET SUBMITTED 0 · team newly submitted 3.

- Status: **Tyson, Jaylon** (Cleveland Cavaliers, CHI@CLE, 11/16/2026): Questionable → Doubtful; reason as printed after: Injury/Illness - Right Ankle Injury Management
- Status: **Larsson, Pelle** (Miami Heat, HOU@MIA, 11/16/2026): Questionable → Doubtful; reason as printed after: Injury/Illness - Illness
- Status: **Stewart, Isaiah** (Memphis Grizzlies, MEM@WAS, 11/16/2026): Questionable → Out; reason as printed after: Injury/Illness - Illness
- Reason: **Jackson, GG** (Memphis Grizzlies, MEM@WAS, 11/16/2026): "Injury/Illness - Left Foot Injury" → "Injury/Illness - Left 5th Metatarsal Fracture" (status Out)
- Team newly submitted: 11/16/2026 HOU@MIA Houston Rockets; 11/16/2026 MEM@WAS Washington Wizards; 11/16/2026 PHI@BKN Philadelphia 76ers

### 2026-11-16_0100PM → 2026-11-16_0215PM

Added 1 · absent 0 · status changed 3 · reason changed 0 · team newly NOT YET SUBMITTED 0 · team newly submitted 1.

- Status: **Dia, Malik** (New Orleans Pelicans, GSW@NOP, 11/16/2026): Questionable → Probable; reason as printed after: G League - Two- Way
- Status: **Pierre Jr., Jaron** (New Orleans Pelicans, GSW@NOP, 11/16/2026): Questionable → Probable; reason as printed after: G League - Two- Way
- Status: **Reese, Julian** (New Orleans Pelicans, GSW@NOP, 11/16/2026): Questionable → Probable; reason as printed after: G League - Two- Way
- Team newly submitted: 11/16/2026 ORL@BOS Boston Celtics

### 2026-11-16_0215PM → 2026-11-17_0945AM

Added 33 · absent 76 · status changed 0 · reason changed 0 · team newly NOT YET SUBMITTED 24 · team newly submitted 9.

- Team newly submitted: 11/16/2026 PHX@DEN Phoenix Suns; 11/17/2026 CHA@LAL Charlotte Hornets; 11/17/2026 CHA@LAL Los Angeles Lakers; 11/17/2026 DET@SAS Detroit Pistons; 11/17/2026 DET@SAS San Antonio Spurs; 11/17/2026 NYK@TOR New York Knicks; 11/17/2026 NYK@TOR Toronto Raptors; 11/17/2026 UTA@LAC LA Clippers; 11/17/2026 UTA@LAC Utah Jazz

## Irregularities flagged (also on the Injuries page and the Flagged for Review page)

1. **11/17 09:45 AM, NYK@TOR:** Toronto Raptors rows only. No New York Knicks row or NOT YET SUBMITTED line appears in the PDF text or the stored .txt. Not inferred. (F-066)
2. **Missing time cells:** the PDF prints a start time once per time group. Blocks with no time are left blank, never borrowed from another game. (F-067)
3. **Date carry:** the PDF prints each date once per date group. Rows below a date cell inherit that date and are marked `date_carried` in the JSON. Checked: each date string appears once per release in the PDF text.
4. **Verbatim wording:** the 11/17 release prints "Injury/Illness - Right Right Foot; 2nd Plantar Plate Tear" for Nurkic, Jusuf. Shown as printed.
5. **Newest release not stored:** the 2026-11-17 capture index names `Injury-Report_2026-11-17_10_30AM.pdf`. It is not in the repository and cannot be fetched from this sandbox. (F-063)
6. **Retrieval times:** recorded for 09:30 AM and 01:00 PM only. The 02:15 PM and 11/17 09:45 AM retrieval times are shown as not recorded. A git commit time is not a retrieval time. (F-068)
7. **Table still on the 11/15 capture:** the Injuries table and the picks' availability read the 11/15 06:15 AM capture. The picks caption said "newest" and is corrected to say table release. (F-064)

## Method notes

- Each glyph's position is taken from the PDF text matrix with the page's current transformation matrix applied. These PDFs flip the y-axis, so the visual top is the page's high y-value after the transform.
- Reason text that wraps onto the line above or below its row is attached to the nearest row on the same page. A reason that crosses a page break is attached to the last row of the previous page and marked `reason_crossed_page_break`. Such cases: Jackson, GG (01:00 PM and 02:15 PM releases, 11/16) and Kessler, Walker (09:45 AM, 11/17). The 09:30 AM release has none. Both attributions were confirmed against the flattened text of the same PDF.
- A fragment that cannot be placed unambiguously is recorded in `problems`. Zero problems were recorded in all four releases.

## Reproduce

```
pip install pypdf==7.1.0
python -m nba2.injury_archive          # rewrites data/injuries/archive/archive.json
python -m nba2.injury_archive --check  # fails if the committed JSON differs
python -m unittest nba2.tests.test_injury_archive -v
```
