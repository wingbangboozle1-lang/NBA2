"""Capture script for data/raw/injury_report_2026-11-13_1830ET.json.

Source: the official NBA injury report PDF, 11/13/26 06:30 PM revision:
    https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_06_30PM.pdf
Retrieved 2026-11-14 ~01:00 UTC (2026-11-13 21:00 ET), read end-to-end.

This is the **18:30 ET revision**, later than the 16:15 ET revision already committed as
`injury_report_2026-11-13.json`. It is captured separately rather than overwriting that
file so the two revisions can be diffed and the status churn between them published.

Transcription rules (identical to the prior capture, so the two files are comparable):

* `reason` is copied **character for character** from the PDF text, including the
  extraction artefacts the PDF's own spacing produces ("Right High AnkleSprain" with no
  space, "Left Great Toe - Sprain", "Left Knee Contusion / Bone Bruise"). The prior
  snapshot preserved the same artefacts, so a diff of the two files shows only real
  status changes.
* `attribution` is "E" where the row carries an explicit team cell, and "C" where the
  PDF table breaks across a page and the team cell is therefore blank (the team is then
  read from document order). See FLAG-INJ-01 in the prior snapshot.
* A team that has not yet submitted for a future game day is carried as a single row
  with an empty player name and status "NOT YET SUBMITTED" - the literal text printed
  in the report. It is not a statement about any player.
* Rows are NOT de-duplicated, sorted, or completed. Where the PDF did not print a team
  roster, no roster is invented (see FLAG-INJ-03: the report prints no rows at all for
  the New York Knicks or the Milwaukee Bucks on 11/13).
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "injury_report_2026-11-13_1830ET.json"

COLUMNS = ["game_date", "time_et", "matchup", "team", "player", "status", "reason",
           "attribution"]


def R(game_date, time_et, matchup, team, player, status, reason, attribution="E"):
    return [game_date, time_et, matchup, team, player, status, reason, attribution]


ROWS = [
    # ============================ 2026-11-13 games =============================
    # MIL@ORL 07:00 - Orlando Magic
    R("2026-11-13", "07:00", "MIL@ORL", "Orlando Magic", "Banchero, Paolo", "Out",
      "Injury/Illness - Right High AnkleSprain"),
    R("2026-11-13", "07:00", "MIL@ORL", "Orlando Magic", "Cain, Jamal", "Available",
      "Injury/Illness - Left ShoulderContusion"),
    R("2026-11-13", "07:00", "MIL@ORL", "Orlando Magic", "da Silva, Tristan", "Available",
      "Injury/Illness - Left Calf Strain"),
    R("2026-11-13", "07:00", "MIL@ORL", "Orlando Magic", "Isaac, Jonathan", "Out",
      "Injury/Illness - Left Knee InjuryManagement"),
    R("2026-11-13", "07:00", "MIL@ORL", "Orlando Magic", "Nelson, Izaiyah", "Out",
      "Injury/Illness - Left Ankle InjuryRecovery"),
    R("2026-11-13", "07:00", "MIL@ORL", "Orlando Magic", "Penda, Noah", "Out",
      "Injury/Illness - Right Partially Torn Hamstring"),
    R("2026-11-13", "07:00", "MIL@ORL", "Orlando Magic", "Suggs, Jalen", "Available",
      "Injury/Illness - Right Knee Contusion/Bone Bruise"),
    # NYK@IND 07:00 - Indiana Pacers
    R("2026-11-13", "07:00", "NYK@IND", "Indiana Pacers", "Furphy, Johnny", "Out",
      "Injury/Illness - Right ACL Repair/Surgery"),
    R("2026-11-13", "07:00", "NYK@IND", "Indiana Pacers", "Haliburton, Tyrese", "Out",
      "Injury/Illness - Left Hamstring Strain"),
    R("2026-11-13", "07:00", "NYK@IND", "Indiana Pacers", "McConnell, T.J.", "Available",
      "Injury/Illness - Right Hamstring Strain"),
    R("2026-11-13", "07:00", "NYK@IND", "Indiana Pacers", "Nesmith, Aaron", "Available",
      "Injury/Illness - Right Knee Soreness"),
    R("2026-11-13", "07:00", "NYK@IND", "Indiana Pacers", "Sheppard, Ben", "Out",
      "Injury/Illness - Left Meniscus Surgery"),
    # ATL@CHI 08:00 - Atlanta Hawks
    R("2026-11-13", "08:00", "ATL@CHI", "Atlanta Hawks", "Dennis, RayJ", "Available",
      "G League - Two-Way"),
    R("2026-11-13", "08:00", "ATL@CHI", "Atlanta Hawks", "Flemings, Kingston", "Available",
      "Injury/Illness - Lumbar Spasm", "C"),
    R("2026-11-13", "08:00", "ATL@CHI", "Atlanta Hawks", "Gilbert, Keshon", "Out",
      "Injury/Illness - Left Knee Inflammation; Non-Surgical Procedure", "C"),
    R("2026-11-13", "08:00", "ATL@CHI", "Atlanta Hawks", "Gueye, Mouhamed", "Out",
      "Injury/Illness - Left Foot Fracture", "C"),
    R("2026-11-13", "08:00", "ATL@CHI", "Atlanta Hawks", "Landale, Jock", "Available",
      "Injury/Illness - Face Mask", "C"),
    R("2026-11-13", "08:00", "ATL@CHI", "Atlanta Hawks", "Newell, Asa", "Out",
      "Injury/Illness - Left Great Toe Hyperextension", "C"),
    R("2026-11-13", "08:00", "ATL@CHI", "Atlanta Hawks", "Veesaar, Henri", "Out",
      "Injury/Illness - Right ACL Tear", "C"),
    R("2026-11-13", "08:00", "ATL@CHI", "Atlanta Hawks", "Wilson, Jalen", "Out",
      "G League - Two-Way", "C"),
    # ATL@CHI 08:00 - Chicago Bulls
    R("2026-11-13", "08:00", "ATL@CHI", "Chicago Bulls", "Awaka, Tobe", "Out",
      "Injury/Illness - Disc Irritation"),
    R("2026-11-13", "08:00", "ATL@CHI", "Chicago Bulls", "Powell, Norman", "Questionable",
      "Injury/Illness - Low Back Spasms"),
    R("2026-11-13", "08:00", "ATL@CHI", "Chicago Bulls", "Sellers, Jaylin", "Out",
      "G League - Two-Way"),
    R("2026-11-13", "08:00", "ATL@CHI", "Chicago Bulls", "Swain, Dailyn", "Questionable",
      "Injury/Illness - Right Disc Irritation"),
    R("2026-11-13", "08:00", "ATL@CHI", "Chicago Bulls", "Wilson, Caleb", "Out",
      "Injury/Illness - Right Metacarpal Fracture"),
    # CLE@MIA 08:00 - Cleveland Cavaliers
    R("2026-11-13", "08:00", "CLE@MIA", "Cleveland Cavaliers", "Diop, Khalifa", "Out",
      "G League - On Assignment"),
    R("2026-11-13", "08:00", "CLE@MIA", "Cleveland Cavaliers", "Merrill, Sam", "Out",
      "Injury/Illness - Right Elbow Injury Management"),
    R("2026-11-13", "08:00", "CLE@MIA", "Cleveland Cavaliers", "Mobley, Evan", "Out",
      "Injury/Illness - Left Great Toe - Sprain"),
    R("2026-11-13", "08:00", "CLE@MIA", "Cleveland Cavaliers", "Tomlin, Nae'Qwan", "Out",
      "Injury/Illness - Low Back Stress Reaction"),
    R("2026-11-13", "08:00", "CLE@MIA", "Cleveland Cavaliers", "Udeh, Jr., Ernest", "Out",
      "G League - Two-Way", "C"),
    # CLE@MIA 08:00 - Miami Heat
    R("2026-11-13", "08:00", "CLE@MIA", "Miami Heat", "Antetokounmpo, Giannis", "Available",
      "Injury/Illness - Right Wrist Sprain"),
    R("2026-11-13", "08:00", "CLE@MIA", "Miami Heat", "Goldin, Vladislav", "Out",
      "G League - Two-Way"),
    R("2026-11-13", "08:00", "CLE@MIA", "Miami Heat", "Larsson, Pelle", "Out",
      "Injury/Illness - Illness"),
    R("2026-11-13", "08:00", "CLE@MIA", "Miami Heat", "Thompson, Klay", "Out",
      "Injury/Illness - Left Ankle Soreness"),
    # MEM@NOP 08:00 - Memphis Grizzlies
    R("2026-11-13", "08:00", "MEM@NOP", "Memphis Grizzlies", "Edey, Zach", "Out",
      "Injury/Illness - Left Ankle Injury Management"),
    R("2026-11-13", "08:00", "MEM@NOP", "Memphis Grizzlies", "Lopez, Karim", "Out",
      "G League - On Assignment"),
    R("2026-11-13", "08:00", "MEM@NOP", "Memphis Grizzlies", "Mashack, Jahmai", "Out",
      "G League - Two-Way"),
    R("2026-11-13", "08:00", "MEM@NOP", "Memphis Grizzlies", "Pippen Jr., Scotty", "Out",
      "Injury/Illness - Lumbar Disc Herniation"),
    R("2026-11-13", "08:00", "MEM@NOP", "Memphis Grizzlies", "Post, Quinten", "Out",
      "Injury/Illness - Concussion Protocol"),
    R("2026-11-13", "08:00", "MEM@NOP", "Memphis Grizzlies", "Saunders, Richie", "Out",
      "Injury/Illness - Right Knee Surgery"),
    # MEM@NOP 08:00 - New Orleans Pelicans
    R("2026-11-13", "08:00", "MEM@NOP", "New Orleans Pelicans", "Dia, Malik", "Available",
      "G League - Two-Way"),
    R("2026-11-13", "08:00", "MEM@NOP", "New Orleans Pelicans", "Mathurin, Bennedict",
      "Questionable", "Injury/Illness - Right Thumb Sprain"),
    R("2026-11-13", "08:00", "MEM@NOP", "New Orleans Pelicans", "McGowens, Bryce", "Out",
      "Injury/Illness - Left Elbow Infection"),
    R("2026-11-13", "08:00", "MEM@NOP", "New Orleans Pelicans", "Missi, Yves", "Out",
      "Injury/Illness - Left Knee Contusion / Bone Bruise"),
    R("2026-11-13", "08:00", "MEM@NOP", "New Orleans Pelicans", "Murphy III, Trey", "Out",
      "Injury/Illness - Bilateral Patellar Tendinopathy"),
    R("2026-11-13", "08:00", "MEM@NOP", "New Orleans Pelicans", "Murray, Dejounte", "Doubtful",
      "Injury/Illness - Left Ankle Sprain"),
    R("2026-11-13", "08:00", "MEM@NOP", "New Orleans Pelicans", "Pierre Jr., Jaron",
      "Available", "G League - Two-Way", "C"),
    R("2026-11-13", "08:00", "MEM@NOP", "New Orleans Pelicans", "Watford, Trendon", "Out",
      "Injury/Illness - Right Ankle Sprain", "C"),
    # UTA@HOU 08:30 - Utah Jazz
    R("2026-11-13", "08:30", "UTA@HOU", "Utah Jazz", "Alexander, Trey", "Out",
      "G League - Two-Way"),
    R("2026-11-13", "08:30", "UTA@HOU", "Utah Jazz", "Bufkin, Kobe", "Out",
      "G League - Two-Way"),
    R("2026-11-13", "08:30", "UTA@HOU", "Utah Jazz", "Ingram, Harrison", "Out",
      "G League - Two-Way"),
    R("2026-11-13", "08:30", "UTA@HOU", "Utah Jazz", "Jackson Jr., Jaren", "Out",
      "Injury/Illness - Right MCL Tear"),
    R("2026-11-13", "08:30", "UTA@HOU", "Utah Jazz", "Markkanen, Lauri", "Out",
      "Injury/Illness - Right Hand Fracture"),
    R("2026-11-13", "08:30", "UTA@HOU", "Utah Jazz", "Nurkic, Jusuf", "Out",
      "Injury/Illness - Right 2nd Plantar Plate Tear"),
    # UTA@HOU 08:30 - Houston Rockets
    R("2026-11-13", "08:30", "UTA@HOU", "Houston Rockets", "Adams, Steven", "Out",
      "Injury/Illness - Right Soleus Strain"),
    R("2026-11-13", "08:30", "UTA@HOU", "Houston Rockets", "Capela, Clint", "Out",
      "Injury/Illness - Right Ankle Sprain"),
    R("2026-11-13", "08:30", "UTA@HOU", "Houston Rockets", "Copeland, Quadir", "Out",
      "G League - Two-Way"),
    R("2026-11-13", "08:30", "UTA@HOU", "Houston Rockets", "Phillips, Julian", "Out",
      "G League - Two-Way"),
    R("2026-11-13", "08:30", "UTA@HOU", "Houston Rockets", "Smart, Marcus", "Out",
      "League Suspension"),
    # GSW@SAS 09:30 - Golden State Warriors
    R("2026-11-13", "09:30", "GSW@SAS", "Golden State Warriors", "Bassey, Charles", "Probable",
      "Injury/Illness - Left Toe Soreness"),
    R("2026-11-13", "09:30", "GSW@SAS", "Golden State Warriors", "Butler III, Jimmy", "Out",
      "Injury/Illness - Right ACL Repair / Surgery"),
    R("2026-11-13", "09:30", "GSW@SAS", "Golden State Warriors", "Curry, Stephen", "Out",
      "Injury/Illness - Right Oblique Tear"),
    R("2026-11-13", "09:30", "GSW@SAS", "Golden State Warriors", "Moody, Moses", "Out",
      "Injury/Illness - Left Patellar Tendon Repair / Surgery"),
    R("2026-11-13", "09:30", "GSW@SAS", "Golden State Warriors", "Porzingis, Kristaps", "Out",
      "Not With Team"),
    R("2026-11-13", "09:30", "GSW@SAS", "Golden State Warriors", "Williams, Brandon", "Out",
      "Injury/Illness - Left Hamstring Strain", "C"),
    # GSW@SAS 09:30 - San Antonio Spurs
    R("2026-11-13", "09:30", "GSW@SAS", "San Antonio Spurs", "Fox, De'Aaron", "Questionable",
      "Injury/Illness - Left Hip Soreness"),
    R("2026-11-13", "09:30", "GSW@SAS", "San Antonio Spurs", "Harris, Tobias", "Out",
      "Injury/Illness - Left Calf Strain"),
    R("2026-11-13", "09:30", "GSW@SAS", "San Antonio Spurs", "Quaintance, Jayden", "Out",
      "Injury/Illness - Right Knee Surgery"),
    R("2026-11-13", "09:30", "GSW@SAS", "San Antonio Spurs", "Vassell, Devin", "Questionable",
      "Injury/Illness - Left Adductor Tightness"),
    # POR@SAC 10:00 - Portland Trail Blazers
    R("2026-11-13", "10:00", "POR@SAC", "Portland Trail Blazers", "Krejci, Vit", "Out",
      "Injury/Illness - Left Ankle Fracture"),
    R("2026-11-13", "10:00", "POR@SAC", "Portland Trail Blazers", "Morant, Ja", "Out",
      "Injury/Illness - Left Hamstring Strain"),
    R("2026-11-13", "10:00", "POR@SAC", "Portland Trail Blazers", "Sharpe, Shaedon", "Out",
      "Injury/Illness - Right Meniscus Surgery"),
    R("2026-11-13", "10:00", "POR@SAC", "Portland Trail Blazers", "Youngblood, Chris", "Out",
      "Injury/Illness - Right Bone Bruise"),
    # POR@SAC 10:00 - Sacramento Kings
    R("2026-11-13", "10:00", "POR@SAC", "Sacramento Kings", "Achiuwa, Precious", "Out",
      "Injury/Illness - Left Ankle Soreness"),
    R("2026-11-13", "10:00", "POR@SAC", "Sacramento Kings", "Karaban, Alex", "Out",
      "G League - On Assignment"),
    R("2026-11-13", "10:00", "POR@SAC", "Sacramento Kings", "Mogbo, Jonathan", "Out",
      "G League - Two-Way"),
    R("2026-11-13", "10:00", "POR@SAC", "Sacramento Kings", "Pedulla, Sean", "Out",
      "G League - Two-Way"),
    R("2026-11-13", "10:00", "POR@SAC", "Sacramento Kings", "Raynaud, Maxime", "Out",
      "Injury/Illness - Right Patella Subluxation"),
    R("2026-11-13", "10:00", "POR@SAC", "Sacramento Kings", "Simmons, Ben", "Out",
      "Injury/Illness - Right Achilles Tendon Repair / Surgery"),
    # OKC@LAC 10:30 - Oklahoma City Thunder
    R("2026-11-13", "10:30", "OKC@LAC", "Oklahoma City Thunder", "Holmgren, Chet", "Out",
      "Injury/Illness - Right Knee/ Injury Recovery"),
    R("2026-11-13", "10:30", "OKC@LAC", "Oklahoma City Thunder", "Mitchell, Ajay",
      "Questionable", "Injury/Illness - Left Ankle Sprain", "C"),
    R("2026-11-13", "10:30", "OKC@LAC", "Oklahoma City Thunder", "Sorber, Thomas", "Out",
      "Injury/Illness - Right Knee Surgery", "C"),
    R("2026-11-13", "10:30", "OKC@LAC", "Oklahoma City Thunder", "Topic, Nikola", "Available",
      "-", "C"),
    R("2026-11-13", "10:30", "OKC@LAC", "Oklahoma City Thunder", "Wallace, Cason", "Out",
      "Injury/Illness - Left Shoulder Surgery", "C"),
    R("2026-11-13", "10:30", "OKC@LAC", "Oklahoma City Thunder", "Williams, Jalen", "Out",
      "Injury/Illness - Left Ankle Surgery", "C"),
    R("2026-11-13", "10:30", "OKC@LAC", "Oklahoma City Thunder", "Williams, Jaylin", "Out",
      "Injury/Illness - Low Back Spasms", "C"),
    # OKC@LAC 10:30 - LA Clippers
    R("2026-11-13", "10:30", "OKC@LAC", "LA Clippers", "Beal, Bradley", "Out",
      "Injury/Illness - Right Knee Injury Management"),
    R("2026-11-13", "10:30", "OKC@LAC", "LA Clippers", "Ingram, Brandon", "Out",
      "Injury/Illness - Right Heel Surgery"),
    R("2026-11-13", "10:30", "OKC@LAC", "LA Clippers", "Martinelli, Nick", "Out",
      "G League - Two-Way"),
    R("2026-11-13", "10:30", "OKC@LAC", "LA Clippers", "Miller, Jordan", "Out",
      "Injury/Illness - Left Rotator Cuff Surgery"),
    R("2026-11-13", "10:30", "OKC@LAC", "LA Clippers", "Niederhauser, Yanic Konan", "Out",
      "Injury/Illness - Right Lisfranc Surgery"),

    # ============================ 2026-11-14 games =============================
    # DEN@NOP 07:00
    R("2026-11-14", "07:00", "DEN@NOP", "Denver Nuggets", "Holmes II, DaRon", "Out",
      "G League - On Assignment"),
    R("2026-11-14", "07:00", "DEN@NOP", "Denver Nuggets", "Nembhard, Ryan", "Out",
      "G League - Two-Way"),
    R("2026-11-14", "07:00", "DEN@NOP", "Denver Nuggets", "Strawther, Julian", "Out",
      "Injury/Illness - Left Knee Sprain"),
    R("2026-11-14", "07:00", "DEN@NOP", "Denver Nuggets", "Whitmore, Cam", "Out",
      "G League - Two-Way"),
    R("2026-11-14", "07:00", "DEN@NOP", "New Orleans Pelicans", "", "NOT YET SUBMITTED",
      "Team submission outstanding at report time"),
    # DAL@CLE 07:30
    R("2026-11-14", "07:30", "DAL@CLE", "Dallas Mavericks", "Biberovic, Tarik", "Out",
      "Injury/Illness - Right Heel Bursitis"),
    R("2026-11-14", "07:30", "DAL@CLE", "Dallas Mavericks", "Christie, Max", "Questionable",
      "Injury/Illness - Left Ankle Sprain"),
    R("2026-11-14", "07:30", "DAL@CLE", "Dallas Mavericks", "de Larrea, Sergio", "Out",
      "Injury/Illness - Right Knee Sprain", "C"),
    R("2026-11-14", "07:30", "DAL@CLE", "Dallas Mavericks", "Johnson Jr., Morez", "Probable",
      "Injury/Illness - Left Shin / Tibia Contusion", "C"),
    R("2026-11-14", "07:30", "DAL@CLE", "Dallas Mavericks", "Lively II, Dereck", "Out",
      "Injury/Illness - Right Foot Surgery", "C"),
    R("2026-11-14", "07:30", "DAL@CLE", "Dallas Mavericks", "Martin, Caleb", "Available",
      "Injury/Illness - Right Thumb Splint", "C"),
    R("2026-11-14", "07:30", "DAL@CLE", "Cleveland Cavaliers", "", "NOT YET SUBMITTED",
      "Team submission outstanding at report time"),
    # BKN@MEM 08:00
    R("2026-11-14", "08:00", "BKN@MEM", "Brooklyn Nets", "Bilodeau, Tyler", "Out",
      "G League - Two-Way"),
    R("2026-11-14", "08:00", "BKN@MEM", "Brooklyn Nets", "Brown Jr., Mikel", "Questionable",
      "Injury/Illness - Illness"),
    R("2026-11-14", "08:00", "BKN@MEM", "Brooklyn Nets", "Jefferson, Joshua", "Out",
      "G League - On Assignment"),
    R("2026-11-14", "08:00", "BKN@MEM", "Brooklyn Nets", "Nelson, Grant", "Out",
      "G League - Two-Way"),
    R("2026-11-14", "08:00", "BKN@MEM", "Brooklyn Nets", "Saraf, Ben", "Out",
      "G League - On Assignment"),
    R("2026-11-14", "08:00", "BKN@MEM", "Brooklyn Nets", "Traore, Nolan", "Probable",
      "Injury/Illness - Right Calf Tightness / Soreness"),
    R("2026-11-14", "08:00", "BKN@MEM", "Memphis Grizzlies", "", "NOT YET SUBMITTED",
      "Team submission outstanding at report time"),
    # CHI@MIN 08:00
    R("2026-11-14", "08:00", "CHI@MIN", "Chicago Bulls", "", "NOT YET SUBMITTED",
      "Team submission outstanding at report time"),
    R("2026-11-14", "08:00", "CHI@MIN", "Minnesota Timberwolves", "Beringer, Joan",
      "Available", "Injury/Illness - Face Mask"),
    R("2026-11-14", "08:00", "CHI@MIN", "Minnesota Timberwolves", "DiVincenzo, Donte", "Out",
      "Injury/Illness - Right Achilles Tendon Repair / Surgery"),
    R("2026-11-14", "08:00", "CHI@MIN", "Minnesota Timberwolves", "Edwards, Anthony", "Out",
      "Injury/Illness - Right Knee Arthroscopy"),
    # DET@MIA 08:00
    R("2026-11-14", "08:00", "DET@MIA", "Detroit Pistons", "Duren, Jalen", "Out",
      "Injury/Illness - Right Hamstring Strain"),
    R("2026-11-14", "08:00", "DET@MIA", "Detroit Pistons", "Harkless, Elijah", "Questionable",
      "G League - Two-Way", "C"),
    R("2026-11-14", "08:00", "DET@MIA", "Detroit Pistons", "Joe, Isaiah", "Out",
      "Injury/Illness - Right Hip Contusion", "C"),
    R("2026-11-14", "08:00", "DET@MIA", "Detroit Pistons", "Jones, Isaac", "Questionable",
      "G League - Two-Way", "C"),
    R("2026-11-14", "08:00", "DET@MIA", "Detroit Pistons", "Lanier, Chaz", "Out",
      "G League - On Assignment", "C"),
    R("2026-11-14", "08:00", "DET@MIA", "Detroit Pistons", "Okorie, Ebuka", "Out",
      "G League - On Assignment", "C"),
    R("2026-11-14", "08:00", "DET@MIA", "Detroit Pistons", "Onyenso, Ugonna", "Out",
      "G League - Two-Way", "C"),
    R("2026-11-14", "08:00", "DET@MIA", "Miami Heat", "", "NOT YET SUBMITTED",
      "Team submission outstanding at report time"),
]


def main() -> None:
    doc = {
        "dataset": "official_injury_report",
        "report_stamp_et": "2026-11-13 18:30",
        "retrieved_at_utc": "2026-11-14T01:00:00Z",
        "supersedes": None,
        "revision_of": "injury_report_2026-11-13.json (16:15 ET revision)",
        "provenance": {
            "publisher": "NBA Referee Operations (official NBA injury report, published on the NBA's own CDN)",
            "official_nba_source": True,
            "url": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_06_30PM.pdf",
            "document_title": "Injury Report: 11/13/26 06:30 PM",
            "cadence_note": (
                "The report is issued per game day (typically one AM release and one "
                "pre-tip release). This 18:30 ET revision is the last revision of the "
                "11/13 game day and is the only official document that carries any "
                "status for the 2026-11-14 games at this retrieval time."
            ),
            "transcription_rules": (
                "Reason strings are copied character for character from the PDF text, "
                "including its own spacing artefacts; attribution E = explicit team "
                "cell, C = page-break continuation row with a blank team cell."
            ),
        },
        "attribution_key": {
            "E": "explicit team cell printed on the row",
            "C": "team cell blank (the PDF table broke across a page); team read from document order",
        },
        "flags": [
            {
                "id": "FLAG-INJ-05",
                "severity": "medium",
                "field": "attribution=C rows",
                "issue": ("The NBA injury-report PDF repeats team labels only once per block. When the table "
                          "breaks across pages the continuation rows carry no team cell, so their team "
                          "attribution comes from document order rather than an explicit label."),
                "action_required": "Confirm the attribution=C rows against the PDF image at the source URL.",
            },
            {
                "id": "FLAG-INJ-06",
                "severity": "high",
                "field": "rotation_minutes_impact,production_impact,line_adjustment_pts",
                "issue": ("No numeric injury impact is produced in this snapshot. Quantifying a status change "
                          "requires player-level minutes and production data; the injury report contains "
                          "neither. The impact columns are blank by design, not omitted."),
                "action_required": ("Attach official per-player minutes and production to the pipeline "
                                    "(see requirements R-102) before any injury adjustment is applied to a line."),
            },
            {
                "id": "FLAG-INJ-07",
                "severity": "medium",
                "field": "teams_not_present",
                "issue": ("The report prints no rows at all for the New York Knicks or the Milwaukee Bucks, "
                          "both of whom played on 2026-11-13. Absence of a row is NOT evidence of availability."),
                "action_required": "Treat a team with no printed roster as UNKNOWN, never as clean.",
            },
            {
                "id": "FLAG-INJ-08",
                "severity": "medium",
                "field": "teams_not_present",
                "issue": (
                    "The 18:30 ET revision still prints no rows at all for the New York "
                    "Knicks or the Milwaukee Bucks, both of whom played on 2026-11-13. "
                    "Absence of a row is not evidence of availability."
                ),
                "action_required": (
                    "Treat a team with no printed roster as UNKNOWN, never as clean. "
                    "Re-check the next revision before any game-day use."
                ),
            },
            {
                "id": "FLAG-INJ-09",
                "severity": "high",
                "field": "game_date=2026-11-14 rows",
                "issue": (
                    "Only 5 of the 10 teams playing on 2026-11-14 have submitted "
                    "statuses in this revision (DEN, DAL, BKN, MIN, DET). The other 5 "
                    "(NOP, CLE, MEM, CHI, MIA) are printed as 'NOT YET SUBMITTED'. No "
                    "report exists yet for the 2026-11-15, 11-16 or 11-17 games."
                ),
                "action_required": (
                    "A line for a game whose teams have not submitted is availability-"
                    "blind by construction. Do not promote such a game above Tier B, and "
                    "re-read the report on game day before acting."
                ),
            },
        ],
        "columns": COLUMNS,
        "records": [list(r) for r in ROWS],
        "record_counts": {
            "total_rows": len(ROWS),
            "rows_2026_11_13": sum(1 for r in ROWS if r[0] == "2026-11-13"),
            "rows_2026_11_14": sum(1 for r in ROWS if r[0] == "2026-11-14"),
            "not_yet_submitted_placeholders": sum(1 for r in ROWS if r[5] == "NOT YET SUBMITTED"),
            "attribution_explicit": sum(1 for r in ROWS if r[7] == "E"),
            "attribution_continuation": sum(1 for r in ROWS if r[7] == "C"),
        },
    }
    OUT.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"wrote {OUT}: {len(ROWS)} rows")
    print(json.dumps(doc["record_counts"], indent=1))


if __name__ == "__main__":
    main()
