# Injury PDF archive audit — session `arena/95053469-nba2` (2026-11-19 UTC)

Board tasks: **INJ-1** inventory · **INJ-2** regenerate empty extractions · **INJ-3** consecutive-report diff · **INJ-4** publish + record.

## Sources (official)

- Official index: https://official.nba.com/nba-injury-report-2026-27-season/ — fetched by this session with the platform page-fetch tool at **2026-11-19T05:46Z**. It lists only the current day's reports (at fetch time: `Injury-Report_2026-11-19_12_00AM.pdf`, `..._12_15AM.pdf`, `..._12_30AM.pdf`).
- Every archived PDF: `https://ak-static.cms.nba.com/referee/injury/<filename>` (filename in the table below). Bytes were archived by the runner (`data/v6/injury_binary_manifest.json`); the sandbox cannot reach `ak-static.cms.nba.com` (TLS reset), so bytes were **not** re-downloaded here.
- Text extraction: committed `nba2/pipeline/refresh.py::pdf_text`, run here on the committed bytes.

## INJ-1 — inventory (20 official PDFs)

Every hash below was recomputed from the committed bytes in this session.

| # | Release (ET) | PDF file | PDF bytes | PDF sha256 | Text (.txt) sha256 | Text chars | Player-status rows | Game dates with rows |
|---|---|---|---|---|---|---|---|---|
| 1 | 2026-11-13 13:00 ET | `Injury-Report_2026-11-13_01_00PM.pdf` | 98515 | `d4875b8ce4ea20a82ec1cc42553f1bf903eb55f6c31de3ff0a69a1d23027d1b1` | `3b647e860939309ef1971efe140c11a84327ae5a8470c69a946f7cc3be05b55e` | 6361 | 91 | 11/13/2026 |
| 2 | 2026-11-13 16:15 ET | `Injury-Report_2026-11-13_04_15PM.pdf` | 98738 | `3e6786fe6c4a951cae45738fd7e812ff21f264fc31615ef296133875e32df202` | `109c2b339a82e3deb3c49c0edea0dac60f486598a4f003a188e17958f35b21e9` | 6335 | 91 | 11/13/2026 |
| 3 | 2026-11-13 17:15 ET | `Injury-Report_2026-11-13_05_15PM.pdf` | 101887 | `502024cff353efce6225d48fef7516b58e8e3c2671368b7983ac3b87a4e541f6` | `c97188284d0daa96ce2e1f288b2e47062816eb76ff9feffe77837355180c64dd` | 7481 | 113 | 11/13/2026, 11/14/2026 |
| 4 | 2026-11-13 19:15 ET | `Injury-Report_2026-11-13_07_15PM.pdf` | 102349 | `20b9c2f9f3aed67b28e3f48557d94cc4db05cc2aef44773d324b9d4540f766b1` | `bc854b52435a788549132c09c7b719d93dfa8ee3bc8124567aa7e0ab1ce6d603` | 7578 | 117 | 11/13/2026, 11/14/2026 |
| 5 | 2026-11-13 19:30 ET | `Injury-Report_2026-11-13_07_30PM.pdf` | 102227 | `f5434cd9c56e7eb6b5f6f92079f33c23538dab508ad953540a7ebf6d7d037ab9` | `8829a37b76d633d6727fc4c46c43e9a1e26139a5db43b7737c5e00292decc0af` | 7578 | 117 | 11/13/2026, 11/14/2026 |
| 6 | 2026-11-14 04:30 ET | `Injury-Report_2026-11-14_04_30AM.pdf` | 87960 | `fbff5f42ec5c5510f1ecca7359eb8216db2ce56ea137493343e0944796e35054` | `934708c6cddd7a1ba1353e3acc2e020272c57c4e5589ffcd77f8035fe9761ed1` | 2692 | 26 | 11/14/2026 |
| 7 | 2026-11-14 05:00 ET | `Injury-Report_2026-11-14_05_00AM.pdf` | 87929 | `78cb966d8115b1f6de63bc8ba0d071cfb689edde1a3c5c6995f4f991446a2cbd` | `4f585126a542ce1c212a176120b9b2f3a06f176d499e85b54240785fbe0641b8` | 2692 | 26 | 11/14/2026 |
| 8 | 2026-11-14 13:30 ET | `Injury-Report_2026-11-14_01_30PM.pdf` | 92455 | `b628131492478451a5cf0c3779d43864833501c6daf30fae20630d5305023d3c` | `8fd2052fc7beaab58dd2f8dbb0aa86ed860dd9c06b6ba81c52f10381484495c4` | 4168 | 50 | 11/14/2026 |
| 9 | 2026-11-15 06:00 ET | `Injury-Report_2026-11-15_06_00AM.pdf` | 97577 | `e4d21fe109e41cc5e7a7c4bbfee5afb8669e4a3f8e3f753470883df0e49da4c4` | `b33b4a5b501199676eca0c6b6d341b577099d9c93575c538669ad94b8401643a` | 6132 | 84 | 11/15/2026 |
| 10 | 2026-11-15 06:15 ET | `Injury-Report_2026-11-15_06_15AM.pdf` | 97582 | `042868ef01ea1530c182e3253da17947dcdfae1e7075ca26e642c0b240d83f00` | `3f0ce1fa01f5ba89b11c765b3ee5e970f7a541627a30264e04435616ec6209da` | 6132 | 84 | 11/15/2026 |
| 11 | 2026-11-15 18:15 ET | `Injury-Report_2026-11-15_06_15PM.pdf` | 108297 | `17fbcb8d206fa2602a712977af9cdf854a7c8c898767c1d6ac8cd62ba4da3203` | `b6a121121c27fb65b3cf9a3f194e2f4badce529ea148daaf1828c3ce36bb35cf` | 9676 | 149 | 11/15/2026, 11/16/2026 |
| 12 | 2026-11-16 09:15 ET | `Injury-Report_2026-11-16_09_15AM.pdf` | 93402 | `2ae3cc90586e2ad45d174d4c599bcb87185f7b6c3ecf68821d3a9efc7105075b` | `e5db19c61a7a380a5e6757ab8437866c6dc5fef66fa7853606130cfa42b5b23e` | 4391 | 57 | 11/16/2026 |
| 13 | 2026-11-16 09:30 ET | `Injury-Report_2026-11-16_09_30AM.pdf` | 93435 | `8e9592936b389f74eee82306656679cd2d7cd2dc42fc7671dbb14f67465cac28` | `fed64321a1ac3c05794a3544047a995b654cd3a1933f431d2c5d7e34d63963ca` | 4391 | 57 | 11/16/2026 |
| 14 | 2026-11-16 13:00 ET | `Injury-Report_2026-11-16_01_00PM.pdf` | 95928 | `e0dbe404b34b616c0acb18427966dad7058ac3e4a743cd76ea46f7e8c7550152` | `d3e6a6129df5dd8ac7bf9001771142327501ad804720f849a9ea9bf10603961f` | 5422 | 75 | 11/16/2026 |
| 15 | 2026-11-16 14:15 ET | `Injury-Report_2026-11-16_02_15PM.pdf` | 96067 | `588d3b9697a58f1ee29f90554ee029c869f5191169615c0790f9eb25a6f58035` | `b796a7c033837714120eec9ab834deb2177a0d6868f6b447df0c0a8669d00008` | 5425 | 76 | 11/16/2026 |
| 16 | 2026-11-17 09:45 ET | `Injury-Report_2026-11-17_09_45AM.pdf` | 90373 | `e28bb978bcb099abfb132dcd852ec0fedc8b76c216f1bf569a95917ab6f4c93c` | `48d20f156ec7455dfae4baa2e05124f0d856aa7c1e763c23002db99f3bda3f59` | 24082 | 33 | 11/17/2026 |
| 17 | 2026-11-17 10:30 ET | `Injury-Report_2026-11-17_10_30AM.pdf` | 90116 | `53a42da5d122e375f5ef8b3eb513ca55024436b925fb971425b9a6e1a6822ffd` | `419a9d95e17df169368cd649ab42a28aa9f3af7468cb88878461fc488125ae29` | 24082 | 33 | 11/17/2026 |
| 18 | 2026-11-17 11:00 ET | `Injury-Report_2026-11-17_11_00AM.pdf` | 89954 | `a5ce82b8bf3b18262a4f66861ae031e2a0a5d4b838df2d8edefe3b2bf9cdaae0` | `f963f3c94421939e0190c0d71f8593490f5f10e1dbbde7d6078102dcc54a9024` | 24082 | 33 | 11/17/2026 |
| 19 | 2026-11-17 14:30 ET | `Injury-Report_2026-11-17_02_30PM.pdf` | 92769 | `2f190154e150378a0103699577608f986816db08ef84dc4e54e8e407ff1d6612` | `2b7d55f269467c45f6bc4de14e11f702aa1e8beabb91bc44a13d0e910a859ceb` | 4123 | 46 | 11/17/2026 |
| 20 | 2026-11-18 09:45 ET | `Injury-Report_2026-11-18_09_45AM.pdf` | 100919 | `3a6c66ac5276cbefb53097febde1be43d2527bd454fd2e5fbd725316b10a2842` | `8a49cfc081498b07a293cc075351df6521ec442cb92856b72d42102c6562814e` | 7059 | 102 | 11/18/2026 |

## INJ-2 — regenerated extractions

The 14 `.txt` files that were **0 bytes** and the 3 that were **missing** were regenerated by running the committed `pdf_text` on the committed PDF bytes. Nothing was typed by hand.

- Regenerated (0 bytes → text): 11-13 01:00 PM, 11-13 04:15 PM, 11-13 05:15 PM, 11-13 07:15 PM, 11-13 07:30 PM, 11-14 01:30 PM, 11-14 04:30 AM, 11-14 05:00 AM, 11-15 06:00 AM, 11-15 06:15 AM, 11-15 06:15 PM, 11-16 09:15 AM, 11-17 10:30 AM, 11-18 09:45 AM.
- Created (missing): 11-16 01:00 PM, 11-16 09:30 AM, 11-17 11:00 AM.
- Kept (already non-empty): 11-16 02:15 PM, 11-17 02:30 PM, 11-17 09:45 AM. The 11-17 09:45 AM file differs from a fresh extraction only by line-ending characters (`\r` vs `\n`); its content was not changed.
- **Result:** all 20 PDFs now have non-empty text. The earlier empty files were stale output, not an unreadable PDF.

## INJ-3 — consecutive-report diff

Method: `analysis/session-95053469-injury-diff.py` → `analysis/session-95053469-injury-diff.json`. Key = (game date, player). Game date = the nearest `MM/DD/YYYY` token before each row. Only game dates that carry rows in **both** releases are compared; the rest are counted, not diffed. Status changes only: reason-text changes are **not** diffed. Matchup and team are not part of the key.

| From (ET) | To (ET) | Comparable | Game dates compared | Rows compared (from/to) | Status changed | Added | Removed | Unchanged |
|---|---|---|---|---|---|---|---|---|
| 2026-11-13 13:00 ET | 2026-11-13 16:15 ET | yes | 11/13/2026 | 91 / 91 | 6 | 0 | 0 | 85 |
| 2026-11-13 16:15 ET | 2026-11-13 17:15 ET | yes | 11/13/2026 | 91 / 91 | 3 | 0 | 0 | 88 |
| 2026-11-13 17:15 ET | 2026-11-13 19:15 ET | yes | 11/13/2026, 11/14/2026 | 113 / 117 | 9 | 4 | 0 | 104 |
| 2026-11-13 19:15 ET | 2026-11-13 19:30 ET | yes | 11/13/2026, 11/14/2026 | 117 / 117 | 0 | 0 | 0 | 117 |
| 2026-11-13 19:30 ET | 2026-11-14 04:30 ET | yes | 11/14/2026 | 26 / 26 | 0 | 0 | 0 | 26 |
| 2026-11-14 04:30 ET | 2026-11-14 05:00 ET | yes | 11/14/2026 | 26 / 26 | 0 | 0 | 0 | 26 |
| 2026-11-14 05:00 ET | 2026-11-14 13:30 ET | yes | 11/14/2026 | 26 / 50 | 4 | 24 | 0 | 22 |
| 2026-11-14 13:30 ET | 2026-11-15 06:00 ET | no — no shared game date | — | 0 / 0 | — | — | — | — |
| 2026-11-15 06:00 ET | 2026-11-15 06:15 ET | yes | 11/15/2026 | 84 / 84 | 0 | 0 | 0 | 84 |
| 2026-11-15 06:15 ET | 2026-11-15 18:15 ET | yes | 11/15/2026 | 84 / 96 | 19 | 12 | 0 | 65 |
| 2026-11-15 18:15 ET | 2026-11-16 09:15 ET | yes | 11/16/2026 | 53 / 57 | 0 | 4 | 0 | 53 |
| 2026-11-16 09:15 ET | 2026-11-16 09:30 ET | yes | 11/16/2026 | 57 / 57 | 0 | 0 | 0 | 57 |
| 2026-11-16 09:30 ET | 2026-11-16 13:00 ET | yes | 11/16/2026 | 57 / 75 | 3 | 18 | 0 | 54 |
| 2026-11-16 13:00 ET | 2026-11-16 14:15 ET | yes | 11/16/2026 | 75 / 76 | 3 | 1 | 0 | 72 |
| 2026-11-16 14:15 ET | 2026-11-17 09:45 ET | no — no shared game date | — | 0 / 0 | — | — | — | — |
| 2026-11-17 09:45 ET | 2026-11-17 10:30 ET | yes | 11/17/2026 | 33 / 33 | 0 | 0 | 0 | 33 |
| 2026-11-17 10:30 ET | 2026-11-17 11:00 ET | yes | 11/17/2026 | 33 / 33 | 0 | 0 | 0 | 33 |
| 2026-11-17 11:00 ET | 2026-11-17 14:30 ET | yes | 11/17/2026 | 33 / 46 | 1 | 13 | 0 | 32 |
| 2026-11-17 14:30 ET | 2026-11-18 09:45 ET | no — no shared game date | — | 0 / 0 | — | — | — | — |

Three pairs have no shared game date and are marked not comparable. A pair marked comparable means a status change or an addition is observed for that game date, not that a player was ruled out for an unlisted reason.

### Cross-check against the committed transcript delta (11-15 06:15 AM → 06:15 PM)

`data/raw/capture_2026-11-15/injury_delta_0615AM_to_0615PM.json` lists 20 status changes. The script finds **19 of those 20** as status changes (the same players, same from/to status).

- The 20th, **Dieng, Ousmane**, is **Out → Out** in the PDF. Only the reason changed ("Left Finger Sprain" → "Left Finger Fracture"). The capture classifies a reason-only change as a status change.
- The script's status-change list has **no** entries missing from the capture.

Row counts reconcile exactly after the name fix:
- 06:15 AM: 84 rows with status + 17 blank-status rows = **101** (capture `records` = 101).
- 06:15 PM: 149 rows with status + 2 `NOT YET SUBMITTED` + 4 blank-status rows = **155** (capture `records` = 155). The capture file itself lists 5 blank-status rows, which is one more than the 4 above; not reconciled, flagged below.

## Irregularities (flagged for review — not corrected unless stated)

1. **Stale empty text files** (14 files, 0 bytes) plus 3 missing. Fixed in INJ-2 by regeneration from committed bytes. Cause of the empties is not established.
2. **Name over-capture in the committed pipeline regex.** `nba2/pipeline/refresh.py::PLAYER_STATUS_RE` absorbs the preceding reason/team text into player names (e.g. `Illness - Left Foot Fracture Landale, Jock`, `TOR Toronto Raptors Barnes, Scottie`, `G League - Two- Way Sarr, Alex`). It is not used by this session's diff (a narrower pattern is). Owner of `nba2/pipeline/refresh.py` should review; not edited here.
3. **Misspelled names in the 11-15 capture.** The official PDF reads `Embiid, Joel` and `Champagnie, Justin`; `data/raw/capture_2026-11-15/injury_report_2026-11-15_0615AM.json` records `Embid, Joel` and `Champagne, Justin`. The PDF text is treated as authoritative here. The capture is not edited.
4. **Reason-only change counted as status change** in the 11-15 capture delta (Dieng, Ousmane) — see cross-check above.
5. **Row-key disagreement with the capture.** For 11-15 06:15 AM → 06:15 PM the capture reports `added 67 / removed 13 / unchanged 68` (keyed on matchup, team, player). This diff reports `added 12 / removed 0 / unchanged 65` on the 11/15 game date (keyed on date, player). The keys differ, so the numbers are not comparable; the **zero removals** in this audit (across all 16 comparable pairs) is measured, not confirmed against an official source, and is flagged as a possible blind spot.
6. **Archive gap at the head of the feed.** The official index (fetched 2026-11-19T05:46Z) lists `Injury-Report_2026-11-19_12_00AM`, `_12_15AM`, `_12_30AM`. None is archived. The latest archived release is 11-18 09:45 AM. The index shows only the current day, so **whether any 11-18 afternoon/evening reports were published is not verifiable from the index** and is flagged unverified.
7. **Bytes not archivable from this sandbox.** The sandbox cannot reach `ak-static.cms.nba.com`. The runner-side archive (`nba2/v6/injury_backfill.py`) is the only byte source; the 11-19 releases above need it on the next scheduled run.
8. **Stored renderings are not PDF bytes.** `data/v4/injury/releases.json` (stored renderings, `binary_stored: false`) came from the platform page-fetch tool, not from the PDF. Its diffs (`nba2/v4/injury_diff.py`) therefore inherit that provenance. Not re-verified here.

## Not done in this session (honest scope)

- No change to `nba2/v4/*`, `nba2/v6/*`, `nba2/pipeline/refresh.py`, the site, the sealed ledgers, or the settlement files.
- The archive is not made complete for the 11-18 afternoon or 11-19 releases; that requires the runner.
- Reason-level diffs are not produced (reason text is not extracted in a keyed way).
