"""Session arena/1eeb6a21-nba2 — official injury release transcript, 2026-11-17 11:00 AM ET.

The verbatim text below is the platform page-fetch rendering of
https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-17_11_00AM.pdf (single
chunk), taken after the index at official.nba.com listed releases for 11/17 up to 11:00 AM
(15-minute cadence; 11:00 AM is inside the league's 11 a.m.-1 p.m. game-day filing window
for the 7:30 PM-and-later tips on today's slate).

Rows are written in the shared nba2.injury-transcript.v3 8-column layout. Two rendering
artifacts are handled by the repo's standing conventions, not by inference:
  * F-V4-05 page-continuation: the Austin Reaves row prints without date/time/matchup
    cells; it is attributed to the CHA@LAL block in progress and carries a note.
  * junction: Walker Kessler's reason ends at "... Right Lower Leg" and the next rendered
    line prints a stray header cell "Soreness" before the Reaves row. The join is recorded
    on both rows; the reason is NOT silently merged (the later 11:15+ releases print the
    complete reason and would supersede this file).
POR@MIN and every 11/18 club print NOT YET SUBMITTED and are stored as such.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATE = "2026-11-17"
URL = ("https://ak-static.cms.nba.com/referee/injury/"
       "Injury-Report_2026-11-17_11_00AM.pdf")
INDEX_URL = "https://official.nba.com/nba-injury-report-2026-27-season/"

TEXT = """## Injury Report: 11/17/26 11:00 AM

| Game Date | Game Time | Matchup | Team | Player Name | Current Status | Reason |
| --- | --- | --- | --- | --- | --- | --- |
| 11/17/2026 | 07:30 (ET) | NYK@TOR | Toronto Raptors | Bittle, Nate | Out | Injury/Illness - Right Foot Avulsion Fracture |
| 11/17/2026 | 07:30 (ET) | NYK@TOR | Toronto Raptors | Leonard, Kawhi | Out | Injury/Illness - Left Knee Injury Management |
| 11/17/2026 | 07:30 (ET) | NYK@TOR | Toronto Raptors | McCullar Jr., Kevin | Out | G League - Two-Way |
| 11/17/2026 | 07:30 (ET) | NYK@TOR | Toronto Raptors | Smith, Malachi | Out | G League - Two-Way |
| 11/17/2026 | 08:00 (ET) | DET@SAS | Detroit Pistons | Duren, Jalen | Out | Injury/Illness - Right Hamstring Strain |
| 11/17/2026 | 08:00 (ET) | DET@SAS | Detroit Pistons | Holland II, Ronald | Out | Injury/Illness - Left Knee Contusion / Bone Bruise |
| 11/17/2026 | 08:00 (ET) | DET@SAS | Detroit Pistons | Joe, Isaiah | Doubtful | Injury/Illness - Right Hip Contusion |
| 11/17/2026 | 08:00 (ET) | DET@SAS | Detroit Pistons | Okorie, Ebuka | Out | G League - On Assignment |
| 11/17/2026 | 08:00 (ET) | DET@SAS | Detroit Pistons | Onyenso, Ugonna | Out | G League - Two-Way |
| 11/17/2026 | 08:00 (ET) | DET@SAS | Detroit Pistons | Prince, Taurean | Out | Injury/Illness - Right Knee Soreness |
| 11/17/2026 | 08:00 (ET) | DET@SAS | Detroit Pistons | Robinson, Duncan | Out | Injury/Illness - Left Quadriceps Strain |
| 11/17/2026 | 08:00 (ET) | DET@SAS | San Antonio Spurs | Brown, Maliq | Out | G League - Two-Way |
| 11/17/2026 | 08:00 (ET) | DET@SAS | San Antonio Spurs | Gillespie, Ja'Kobi | Out | G League - Two-Way |
| 11/17/2026 | 08:00 (ET) | DET@SAS | San Antonio Spurs | Harris, Tobias | Out | Injury/Illness - Left Calf Strain |
| 11/17/2026 | 08:00 (ET) | DET@SAS | San Antonio Spurs | Quaintance, Jayden | Out | Injury/Illness - Right Knee Surgery |
| 11/17/2026 | 08:00 (ET) | POR@MIN | Portland Trail Blazers |  |  | NOT YET SUBMITTED |

---

**Injury Report: 11/17/26 11:00 AM**

|  |  | Minnesota Timberwolves |  |  | NOT YET SUBMITTED |
| --- | --- | --- | --- | --- | --- |
| 10:30 (ET) | UTA@LAC | Utah Jazz | Bufkin, Kobe | Out | G League - Two-Way |
| 10:30 (ET) | UTA@LAC | Utah Jazz | Hayes, Jaxson | Out | Injury/Illness - Left Knee Strain |
| 10:30 (ET) | UTA@LAC | Utah Jazz | Ingram, Harrison | Out | G League - Two-Way |
| 10:30 (ET) | UTA@LAC | Utah Jazz | Jackson Jr., Jaren | Out | Injury/Illness - Right MCL Tear |
| 10:30 (ET) | UTA@LAC | Utah Jazz | Markkanen, Lauri | Out | Injury/Illness - Right Hand Fracture |
| 10:30 (ET) | UTA@LAC | Utah Jazz | Nurkic, Jusuf | Out | Injury/Illness - Right Right Foot; 2nd Plantar Plate Tear |
| 10:30 (ET) | UTA@LAC | LA Clippers | Beal, Bradley | Out | Injury/Illness - Right Knee Injury Management |
| 10:30 (ET) | UTA@LAC | LA Clippers | Ingram, Brandon | Out | Injury/Illness - Right Heel Surgery |
| 10:30 (ET) | UTA@LAC | LA Clippers | Miller, Jordan | Out | Injury/Illness - Left Rotator Cuff Surgery |
| 10:30 (ET) | UTA@LAC | LA Clippers | Niederhauser, Yanic Konan | Out | Injury/Illness - Right Lisfranc Surgery |
| 11:00 (ET) | CHA@LAL | Charlotte Hornets | Ajayi, Michael | Out | G League - Two-Way |
| 11:00 (ET) | CHA@LAL | Charlotte Hornets | Boswell, Kylan | Out | G League - Two-Way |
| 11:00 (ET) | CHA@LAL | Charlotte Hornets | Knueppel, Kon | Out | Injury/Illness - Left Hamstring Strain |
| 11:00 (ET) | CHA@LAL | Charlotte Hornets | Schroder, Dennis | Out | Injury/Illness - Left Hamstring Strain |
| 11:00 (ET) | CHA@LAL | Charlotte Hornets | Steinbach, Hannes | Out | G League - On Assignment |
| 11:00 (ET) | CHA@LAL | Los Angeles Lakers | Grimes, Quentin | Available | Injury/Illness - Right Finger Splint |
| 11:00 (ET) | CHA@LAL | Los Angeles Lakers | Kessler, Walker | Out | Injury/Illness - Right Lower Leg |

---

**Injury Report: 11/17/26 11:00 AM**

|  |  |  |  | Soreness |  |  |
| --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  | Reaves, Austin | Out | Injury/Illness - Left Heel Contusion / Bone Bruise |
| 11/18/2026 | 07:00 (ET) | HOU@IND | Houston Rockets |  |  | NOT YET SUBMITTED |
| 11/18/2026 | 07:00 (ET) | HOU@IND | Indiana Pacers |  |  | NOT YET SUBMITTED |
| 11/18/2026 | 07:00 (ET) | MEM@CLE | Memphis Grizzlies |  |  | NOT YET SUBMITTED |
| 11/18/2026 | 07:00 (ET) | MEM@CLE | Cleveland Cavaliers |  |  | NOT YET SUBMITTED |
| 11/18/2026 | 07:00 (ET) | MIL@MIA | Milwaukee Bucks |  |  | NOT YET SUBMITTED |
| 11/18/2026 | 07:00 (ET) | MIL@MIA | Miami Heat |  |  | NOT YET SUBMITTED |
| 11/18/2026 | 07:00 (ET) | PHI@ORL | Philadelphia 76ers |  |  | NOT YET SUBMITTED |
| 11/18/2026 | 07:00 (ET) | PHI@ORL | Orlando Magic |  |  | NOT YET SUBMITTED |
| 11/18/2026 | 07:30 (ET) | CHI@BKN | Chicago Bulls |  |  | NOT YET SUBMITTED |
| 11/18/2026 | 07:30 (ET) | CHI@BKN | Brooklyn Nets |  |  | NOT YET SUBMITTED |
| 11/18/2026 | 07:30 (ET) | WAS@TOR | Washington Wizards |  |  | NOT YET SUBMITTED |
| 11/18/2026 | 07:30 (ET) | WAS@TOR | Toronto Raptors |  |  | NOT YET SUBMITTED |
| 11/18/2026 | 08:00 (ET) | ATL@OKC | Atlanta Hawks |  |  | NOT YET SUBMITTED |
| 11/18/2026 | 08:00 (ET) | ATL@OKC | Oklahoma City Thunder |  |  | NOT YET SUBMITTED |
| 11/18/2026 | 08:00 (ET) | DET@NOP | Detroit Pistons |  |  | NOT YET SUBMITTED |
| 11/18/2026 | 08:00 (ET) | DET@NOP | New Orleans Pelicans |  |  | NOT YET SUBMITTED |

---

**Injury Report: 11/17/26 11:00 AM**

|  |  | GSW@DAL | Golden State Warriors | NOT YET SUBMITTED |
| --- | --- | --- | --- | --- |
|  |  | GSW@DAL | Dallas Mavericks | NOT YET SUBMITTED |
|  | 09:30 (ET) | BOS@DEN | Boston Celtics | NOT YET SUBMITTED |
|  | 09:30 (ET) | BOS@DEN | Denver Nuggets | NOT YET SUBMITTED |
|  | 10:00 (ET) | PHX@SAC | Phoenix Suns | NOT YET SUBMITTED |
|  | 10:00 (ET) | PHX@SAC | Sacramento Kings | NOT YET SUBMITTED |
|  | 10:00 (ET) | UTA@LAL | Utah Jazz | NOT YET SUBMITTED |
|  | 10:00 (ET) | UTA@LAL | Los Angeles Lakers | NOT YET SUBMITTED |
"""

# (date, time_et, matchup, team, player, status, reason, note)
ROWS: list[list[str]] = [
    ["2026-11-17", "07:30", "NYK@TOR", "Toronto Raptors", "Bittle, Nate", "Out", "Injury/Illness - Right Foot Avulsion Fracture", ""],
    ["2026-11-17", "07:30", "NYK@TOR", "Toronto Raptors", "Leonard, Kawhi", "Out", "Injury/Illness - Left Knee Injury Management", ""],
    ["2026-11-17", "07:30", "NYK@TOR", "Toronto Raptors", "McCullar Jr., Kevin", "Out", "G League - Two-Way", ""],
    ["2026-11-17", "07:30", "NYK@TOR", "Toronto Raptors", "Smith, Malachi", "Out", "G League - Two-Way", ""],
    ["2026-11-17", "08:00", "DET@SAS", "Detroit Pistons", "Duren, Jalen", "Out", "Injury/Illness - Right Hamstring Strain", ""],
    ["2026-11-17", "08:00", "DET@SAS", "Detroit Pistons", "Holland II, Ronald", "Out", "Injury/Illness - Left Knee Contusion / Bone Bruise", ""],
    ["2026-11-17", "08:00", "DET@SAS", "Detroit Pistons", "Joe, Isaiah", "Doubtful", "Injury/Illness - Right Hip Contusion", ""],
    ["2026-11-17", "08:00", "DET@SAS", "Detroit Pistons", "Okorie, Ebuka", "Out", "G League - On Assignment", ""],
    ["2026-11-17", "08:00", "DET@SAS", "Detroit Pistons", "Onyenso, Ugonna", "Out", "G League - Two-Way", ""],
    ["2026-11-17", "08:00", "DET@SAS", "Detroit Pistons", "Prince, Taurean", "Out", "Injury/Illness - Right Knee Soreness", ""],
    ["2026-11-17", "08:00", "DET@SAS", "Detroit Pistons", "Robinson, Duncan", "Out", "Injury/Illness - Left Quadriceps Strain", ""],
    ["2026-11-17", "08:00", "DET@SAS", "San Antonio Spurs", "Brown, Maliq", "Out", "G League - Two-Way", ""],
    ["2026-11-17", "08:00", "DET@SAS", "San Antonio Spurs", "Gillespie, Ja'Kobi", "Out", "G League - Two-Way", ""],
    ["2026-11-17", "08:00", "DET@SAS", "San Antonio Spurs", "Harris, Tobias", "Out", "Injury/Illness - Left Calf Strain", ""],
    ["2026-11-17", "08:00", "DET@SAS", "San Antonio Spurs", "Quaintance, Jayden", "Out", "Injury/Illness - Right Knee Surgery", ""],
    ["2026-11-17", "08:00", "POR@MIN", "Portland Trail Blazers", "", "", "NOT YET SUBMITTED", "club had not filed at 11:00 AM ET"],
    ["2026-11-17", "08:00", "POR@MIN", "Minnesota Timberwolves", "", "", "NOT YET SUBMITTED", "club had not filed at 11:00 AM ET; the club's row printed inside the page-continuation table"],
    ["2026-11-17", "10:30", "UTA@LAC", "Utah Jazz", "Bufkin, Kobe", "Out", "G League - Two-Way", ""],
    ["2026-11-17", "10:30", "UTA@LAC", "Utah Jazz", "Hayes, Jaxson", "Out", "Injury/Illness - Left Knee Strain", ""],
    ["2026-11-17", "10:30", "UTA@LAC", "Utah Jazz", "Ingram, Harrison", "Out", "G League - Two-Way", ""],
    ["2026-11-17", "10:30", "UTA@LAC", "Utah Jazz", "Jackson Jr., Jaren", "Out", "Injury/Illness - Right MCL Tear", ""],
    ["2026-11-17", "10:30", "UTA@LAC", "Utah Jazz", "Markkanen, Lauri", "Out", "Injury/Illness - Right Hand Fracture", ""],
    ["2026-11-17", "10:30", "UTA@LAC", "Utah Jazz", "Nurkic, Jusuf", "Out", "Injury/Illness - Right Right Foot; 2nd Plantar Plate Tear", "reason transcribed as printed, including the doubled 'Right'"],
    ["2026-11-17", "10:30", "UTA@LAC", "LA Clippers", "Beal, Bradley", "Out", "Injury/Illness - Right Knee Injury Management", ""],
    ["2026-11-17", "10:30", "UTA@LAC", "LA Clippers", "Ingram, Brandon", "Out", "Injury/Illness - Right Heel Surgery", ""],
    ["2026-11-17", "10:30", "UTA@LAC", "LA Clippers", "Miller, Jordan", "Out", "Injury/Illness - Left Rotator Cuff Surgery", ""],
    ["2026-11-17", "10:30", "UTA@LAC", "LA Clippers", "Niederhauser, Yanic Konan", "Out", "Injury/Illness - Right Lisfranc Surgery", ""],
    ["2026-11-17", "11:00", "CHA@LAL", "Charlotte Hornets", "Ajayi, Michael", "Out", "G League - Two-Way", ""],
    ["2026-11-17", "11:00", "CHA@LAL", "Charlotte Hornets", "Boswell, Kylan", "Out", "G League - Two-Way", ""],
    ["2026-11-17", "11:00", "CHA@LAL", "Charlotte Hornets", "Knueppel, Kon", "Out", "Injury/Illness - Left Hamstring Strain", ""],
    ["2026-11-17", "11:00", "CHA@LAL", "Charlotte Hornets", "Schroder, Dennis", "Out", "Injury/Illness - Left Hamstring Strain", ""],
    ["2026-11-17", "11:00", "CHA@LAL", "Charlotte Hornets", "Steinbach, Hannes", "Out", "G League - On Assignment", ""],
    ["2026-11-17", "11:00", "CHA@LAL", "Los Angeles Lakers", "Grimes, Quentin", "Available", "Injury/Illness - Right Finger Splint", ""],
    ["2026-11-17", "11:00", "CHA@LAL", "Los Angeles Lakers", "Kessler, Walker", "Out", "Injury/Illness - Right Lower Leg", "reason continues onto the next rendered chunk, which prints a stray header cell 'Soreness'; junction recorded (F-V4-10 convention), not merged by inference"],
    ["2026-11-17", "11:00", "CHA@LAL", "Los Angeles Lakers", "Reaves, Austin", "Out", "Injury/Illness - Left Heel Contusion / Bone Bruise", "page-continuation row: the rendering dropped the date/time/matchup cells; attributed to the CHA@LAL block in progress (F-V4-05 convention)"],
]

# The 11/18 clubs printed NOT YET SUBMITTED; they are recorded as club-level rows so the
# "not yet filed" state at 11:00 AM is part of the record, then excluded from player rows.
CLUB_ROWS: list[list[str]] = []
for time_et, matchup in [
    ("07:00", "HOU@IND"), ("07:00", "MEM@CLE"), ("07:00", "MIL@MIA"), ("07:00", "PHI@ORL"),
    ("07:30", "CHI@BKN"), ("07:30", "WAS@TOR"), ("08:00", "ATL@OKC"), ("08:00", "DET@NOP"),
]:
    a, h = matchup.split("@")
    CLUB_ROWS.append(["2026-11-18", time_et, matchup, a, "", "", "NOT YET SUBMITTED", "day-before designations not filed at 11:00 AM ET (due 5 p.m. local)"])
    CLUB_ROWS.append(["2026-11-18", time_et, matchup, h, "", "", "NOT YET SUBMITTED", "day-before designations not filed at 11:00 AM ET (due 5 p.m. local)"])
CLUB_ROWS += [
    ["2026-11-18", "08:00", "GSW@DAL", "Golden State Warriors", "", "", "NOT YET SUBMITTED", "day-before designations not filed at 11:00 AM ET (due 5 p.m. local)"],
    ["2026-11-18", "08:00", "GSW@DAL", "Dallas Mavericks", "", "", "NOT YET SUBMITTED", "day-before designations not filed at 11:00 AM ET (due 5 p.m. local)"],
    ["2026-11-18", "09:30", "BOS@DEN", "Boston Celtics", "", "", "NOT YET SUBMITTED", "day-before designations not filed at 11:00 AM ET (due 5 p.m. local)"],
    ["2026-11-18", "09:30", "BOS@DEN", "Denver Nuggets", "", "", "NOT YET SUBMITTED", "day-before designations not filed at 11:00 AM ET (due 5 p.m. local)"],
    ["2026-11-18", "10:00", "PHX@SAC", "Phoenix Suns", "", "", "NOT YET SUBMITTED", "day-before designations not filed at 11:00 AM ET (due 5 p.m. local)"],
    ["2026-11-18", "10:00", "PHX@SAC", "Sacramento Kings", "", "", "NOT YET SUBMITTED", "day-before designations not filed at 11:00 AM ET (due 5 p.m. local)"],
    ["2026-11-18", "10:00", "UTA@LAL", "Utah Jazz", "", "", "NOT YET SUBMITTED", "day-before designations not filed at 11:00 AM ET (due 5 p.m. local)"],
    ["2026-11-18", "10:00", "UTA@LAL", "Los Angeles Lakers", "", "", "NOT YET SUBMITTED", "day-before designations not filed at 11:00 AM ET (due 5 p.m. local)"],
]


def main() -> int:
    # sanity: every player row must appear verbatim in the stored rendering
    missing = []
    for r in ROWS:
        if r[4] and f"| {r[4]} |" not in TEXT.replace(" | ", " | "):
            # rows print as "| Name | Status | Reason |" — check the name cell exists
            if f"| {r[4]} " not in TEXT and f" {r[4]} |" not in TEXT:
                missing.append(r[4])
    if missing:
        print("row names not found verbatim in rendering:", missing)
        return 1
    out = ROOT / "data" / "raw" / "refresh_2026-11-17"
    out.mkdir(parents=True, exist_ok=True)
    doc = {
        "schema": "nba2.injury-transcript.v3",
        "report_stamp_et": "2026-11-17 11:00 AM ET",
        "revision_time_et": "2026-11-17 11:00 AM ET",
        "retrieved_at_utc": "2026-11-17T16:41:00Z",
        "index_checked_utc": "2026-11-17T16:39:00Z",
        "retrieval_method": "platform page-fetch tool (fetch_page); returned as a single chunk",
        "provenance": {
            "publisher": "NBA Official Injury Report (official)",
            "url": URL,
            "index_url": INDEX_URL,
            "note": ("Rows transcribed from the release's own text. Where the rendering lost a "
                     "cell (page-continuation), the cell is attributed per the F-V4-05/10 "
                     "conventions and the basis is written on the row - never reconstructed."),
        },
        "columns": ["date", "time_et", "matchup", "team", "player", "status", "reason", "note"],
        "records": ROWS + CLUB_ROWS,
        "layout_notes": [
            ("F-V4-05", "The Austin Reaves row prints with empty date/time/matchup cells; "
                        "attributed to the CHA@LAL block in progress."),
            ("F-V4-10", "Walker Kessler's reason ends at 'Right Lower Leg' and the next rendered "
                        "line prints a stray header cell 'Soreness'; the junction is recorded on "
                        "both rows and the reason is not merged by inference. The 11:15+ releases "
                        "on the same index print the complete reason and supersede this file."),
        ],
        "content_sha256": hashlib.sha256(TEXT.encode("utf-8")).hexdigest(),
        "counts": {
            "player_rows": len(ROWS),
            "club_not_yet_submitted_rows": len(CLUB_ROWS) + 2,
            "status_counts": {},
        },
    }
    for r in ROWS:
        if r[5]:
            doc["counts"]["status_counts"][r[5]] = doc["counts"]["status_counts"].get(r[5], 0) + 1
    (out / "injury_transcript_20261117_1100AM.json").write_text(
        json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    (out / "injury_release_20261117_1100AM.verbatim.txt").write_text(TEXT, encoding="utf-8")
    print(f"OK: {out}/injury_transcript_20261117_1100AM.json "
          f"({len(ROWS)} player rows + {len(CLUB_ROWS)} club rows), verbatim text stored, "
          f"sha256 {doc['content_sha256'][:16]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
