#!/usr/bin/env python3
"""Session arena/f8f8f2b8-nba2 — 2026-11-15 06:15 PM ET official injury release.

Transcribes the newest official release indexed on
https://official.nba.com/nba-injury-report-2026-27-season/ at retrieval time and diffs it
against the 06:15 AM ET release already committed in this repo.

Nothing here is inferred. Every row is copied from the fetched PDF text. Rows whose *team*
cell is empty in the extraction (page-continuation rows) inherit the team of the block in
progress and carry an 8th field saying so — exactly the convention the 06:15 AM transcript
uses, so the two files diff cleanly.

Run:  python3 analysis/session-f8f8f2b8-injury-capture.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAP = ROOT / "data" / "raw" / "capture_2026-11-15"
AM_FILE = CAP / "injury_report_2026-11-15_0615AM.json"
PM_FILE = CAP / "injury_report_2026-11-15_0615PM.json"
DELTA_FILE = CAP / "injury_delta_0615AM_to_0615PM.json"

PM_PDF_URL = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15PM.pdf"
AM_PDF_URL = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15AM.pdf"
INDEX_URL = "https://official.nba.com/nba-injury-report-2026-27-season/"

RETRIEVED_AT_UTC = "2026-11-15T23:41:00Z"

# Continuation-row note (team cell empty in the PDF extraction).
_CONT = (
    "team cell blank in the PDF extraction (continuation row); attributed to the {blk} block "
    "in progress by table position. Layout attribution, flagged for reviewer confirmation "
    "(I-F8F-01)."
)
_INHERIT = (
    "date/time/matchup cell blank in the PDF extraction (continuation row); inherited from the "
    "{blk} block in progress by table position. Layout attribution, flagged for reviewer "
    "confirmation (I-F8F-01)."
)

# (date, time_et, matchup, team, player, status, reason)  — verbatim from the PDF.
# Blocks are in the order the PDF prints them.
ROWS: list[list[str]] = [
    # ---------------- 2026-11-15 ----------------
    ["2026-11-15", "01:00", "IND@PHI", "Indiana Pacers", "Furphy, Johnny", "Out",
     "Injury/Illness - Right ACL Repair / Surgery"],
    ["2026-11-15", "01:00", "IND@PHI", "Indiana Pacers", "Haliburton, Tyrese", "Out",
     "Injury/Illness - Left Hamstring Strain"],
    ["2026-11-15", "01:00", "IND@PHI", "Indiana Pacers", "McConnell, T.J.", "Available",
     "Injury/Illness - Right Hamstring Strain"],
    ["2026-11-15", "01:00", "IND@PHI", "Indiana Pacers", "Nembhard, Andrew", "Out",
     "Injury/Illness - Left Hip Soreness / Tightness"],
    ["2026-11-15", "01:00", "IND@PHI", "Indiana Pacers", "Nesmith, Aaron", "Available",
     "Injury/Illness - Left Hand Sprain"],
    ["2026-11-15", "01:00", "IND@PHI", "Indiana Pacers", "Sheppard, Ben", "Out",
     "Injury/Illness - Left Meniscus Tear"],
    ["2026-11-15", "01:00", "IND@PHI", "Philadelphia 76ers", "Barlow, Dominick", "Out",
     "Injury/Illness - Low Back Stress Reaction"],
    ["2026-11-15", "01:00", "IND@PHI", "Philadelphia 76ers", "Bona, Adem", "Out",
     "Injury/Illness - Cervical Spine Sprain"],
    ["2026-11-15", "01:00", "IND@PHI", "Philadelphia 76ers", "Embiid, Joel", "Out",
     "Injury/Illness - Right Foot Plantar Fascia Injury Management"],
    ["2026-11-15", "01:00", "IND@PHI", "Philadelphia 76ers", "Hukporti, Ariel", "Out",
     "Injury/Illness - Right Achilles Tendon Rupture / Tear"],

    ["2026-11-15", "04:00", "LAL@PHX", "Los Angeles Lakers", "Carr, Cameron", "Out",
     "Injury/Illness - Illness"],
    ["2026-11-15", "04:00", "LAL@PHX", "Los Angeles Lakers", "Grimes, Quentin", "Available",
     "Injury/Illness - Right Finger Splint"],
    ["2026-11-15", "04:00", "LAL@PHX", "Los Angeles Lakers", "James, Bronny", "Available",
     "Injury/Illness - Illness"],
    ["2026-11-15", "04:00", "LAL@PHX", "Los Angeles Lakers", "Reaves, Austin", "Out",
     "Injury/Illness - Left Heel Contusion / Bone Bruise"],
    ["2026-11-15", "04:00", "LAL@PHX", "Los Angeles Lakers", "Sexton, Collin", "Available",
     "Injury/Illness - Right Orbital Laceration", _CONT.format(blk="LAL@PHX")],
    ["2026-11-15", "04:00", "LAL@PHX", "Los Angeles Lakers", "Thiero, Adou", "Available",
     "Injury/Illness - Left Ankle Sprain", _CONT.format(blk="LAL@PHX")],
    ["2026-11-15", "04:00", "LAL@PHX", "Phoenix Suns", "Timme, Drew", "Out",
     "G League - Two-Way"],
    ["2026-11-15", "04:00", "LAL@PHX", "Phoenix Suns", "Williams, Mark", "Out",
     "Injury/Illness - Left Shoulder Surgery"],

    ["2026-11-15", "04:30", "CHA@LAC", "Charlotte Hornets", "Ajayi, Michael", "Out",
     "G League - Two-Way"],
    ["2026-11-15", "04:30", "CHA@LAC", "Charlotte Hornets", "Boswell, Kylan", "Out",
     "G League - Two-Way"],
    ["2026-11-15", "04:30", "CHA@LAC", "Charlotte Hornets", "Knueppel, Kon", "Out",
     "Injury/Illness - Left Hamstring Strain"],
    ["2026-11-15", "04:30", "CHA@LAC", "Charlotte Hornets", "Schroder, Dennis", "Out",
     "Injury/Illness - Left Hamstring Strain"],
    ["2026-11-15", "04:30", "CHA@LAC", "Charlotte Hornets", "Steinbach, Hannes", "Out",
     "G League - On Assignment"],
    ["2026-11-15", "04:30", "CHA@LAC", "LA Clippers", "Beal, Bradley", "Out",
     "Injury/Illness - Right Knee Injury Management"],
    ["2026-11-15", "04:30", "CHA@LAC", "LA Clippers", "Ingram, Brandon", "Out",
     "Injury/Illness - Right Heel Surgery"],
    ["2026-11-15", "04:30", "CHA@LAC", "LA Clippers", "Martinelli, Nick", "Out",
     "G League - Two-Way"],
    ["2026-11-15", "04:30", "CHA@LAC", "LA Clippers", "Miller, Jordan", "Out",
     "Injury/Illness - Left Rotator Cuff Surgery"],
    ["2026-11-15", "04:30", "CHA@LAC", "LA Clippers", "Niederhauser, Yanic Konan", "Out",
     "Injury/Illness - Right Lisfranc Surgery"],

    ["2026-11-15", "05:00", "SAS@UTA", "San Antonio Spurs", "Brown, Maliq", "Out",
     "G League - Two-Way"],
    ["2026-11-15", "05:00", "SAS@UTA", "San Antonio Spurs", "Fox, De'Aaron", "Out",
     "Injury/Illness - Left Hip Tightness"],
    ["2026-11-15", "05:00", "SAS@UTA", "San Antonio Spurs", "Gillespie, Ja'Kobi", "Out",
     "G League - Two-Way"],
    ["2026-11-15", "05:00", "SAS@UTA", "San Antonio Spurs", "Harris, Tobias", "Out",
     "Injury/Illness - Left Calf Strain"],
    ["2026-11-15", "05:00", "SAS@UTA", "San Antonio Spurs", "Quaintance, Jayden", "Out",
     "Injury/Illness - Right Knee Surgery", _CONT.format(blk="SAS@UTA")],
    ["2026-11-15", "05:00", "SAS@UTA", "Utah Jazz", "Alexander, Trey", "Out",
     "G League - Two-Way"],
    ["2026-11-15", "05:00", "SAS@UTA", "Utah Jazz", "Bufkin, Kobe", "Out",
     "G League - Two-Way"],
    ["2026-11-15", "05:00", "SAS@UTA", "Utah Jazz", "Hayes, Jaxson", "Out",
     "Injury/Illness - Left Knee Strain"],
    ["2026-11-15", "05:00", "SAS@UTA", "Utah Jazz", "Ingram, Harrison", "Out",
     "G League - Two-Way"],
    ["2026-11-15", "05:00", "SAS@UTA", "Utah Jazz", "Jackson Jr., Jaren", "Out",
     "Injury/Illness - Right MCL Tear"],
    ["2026-11-15", "05:00", "SAS@UTA", "Utah Jazz", "Markkanen, Lauri", "Out",
     "Injury/Illness - Right Hand Fracture"],
    ["2026-11-15", "05:00", "SAS@UTA", "Utah Jazz", "Nurkic, Jusuf", "Out",
     "Injury/Illness - Right 2nd Plantar Plate Tear"],

    ["2026-11-15", "06:00", "DAL@BOS", "Dallas Mavericks", "Aldama, Santi", "Out",
     "Injury/Illness - Left Ankle Sprain"],
    ["2026-11-15", "06:00", "DAL@BOS", "Dallas Mavericks", "Biberovic, Tarik", "Out",
     "Injury/Illness - Right Heel Bursitis"],
    ["2026-11-15", "06:00", "DAL@BOS", "Dallas Mavericks", "Christie, Max", "Out",
     "Injury/Illness - Left Ankle Sprain"],
    ["2026-11-15", "06:00", "DAL@BOS", "Dallas Mavericks", "de Larrea, Sergio", "Out",
     "Injury/Illness - Right Knee Sprain"],
    ["2026-11-15", "06:00", "DAL@BOS", "Dallas Mavericks", "Gafford, Daniel", "Available",
     "Injury/Illness - Right Shoulder Stinger"],
    ["2026-11-15", "06:00", "DAL@BOS", "Dallas Mavericks", "Irving, Kyrie", "Out",
     "Injury/Illness - Left Knee Injury Management"],
    ["2026-11-15", "06:00", "DAL@BOS", "Dallas Mavericks", "Lively II, Dereck", "Out",
     "Injury/Illness - Right Foot Surgery"],
    ["2026-11-15", "06:00", "DAL@BOS", "Dallas Mavericks", "Martin, Caleb", "Available",
     "Injury/Illness - Right Thumb Splint"],
    ["2026-11-15", "06:00", "DAL@BOS", "Boston Celtics", "Carter, Devin", "Available",
     "G League - Two-Way"],
    ["2026-11-15", "06:00", "DAL@BOS", "Boston Celtics", "Cenac Jr., Christopher", "Available",
     "G League - On Assignment"],
    ["2026-11-15", "06:00", "DAL@BOS", "Boston Celtics", "Mitchell, Dillon", "Available",
     "G League - Two-Way", _CONT.format(blk="DAL@BOS")],
    ["2026-11-15", "06:00", "DAL@BOS", "Boston Celtics", "Williams, Amari", "Available",
     "G League - Two-Way", _CONT.format(blk="DAL@BOS")],

    # NOTE: the PDF prints no New York Knicks block at all under NYK@TOR — not even a
    # "NOT YET SUBMITTED" placeholder. Flagged, not filled in.
    ["2026-11-15", "06:00", "NYK@TOR", "Toronto Raptors", "Barnes, Scottie", "Available",
     "Injury/Illness - Left Groin Strain", _INHERIT.format(blk="NYK@TOR")],
    ["2026-11-15", "06:00", "NYK@TOR", "Toronto Raptors", "Bittle, Nate", "Out",
     "Injury/Illness - Right Foot Avulsion Fracture", _INHERIT.format(blk="NYK@TOR")],
    ["2026-11-15", "06:00", "NYK@TOR", "Toronto Raptors", "Leonard, Kawhi", "Out",
     "Injury/Illness - Left Knee Injury Management", _INHERIT.format(blk="NYK@TOR")],
    ["2026-11-15", "06:00", "NYK@TOR", "Toronto Raptors", "McCullar Jr., Kevin", "Out",
     "G League - Two-Way", _INHERIT.format(blk="NYK@TOR")],
    ["2026-11-15", "06:00", "NYK@TOR", "Toronto Raptors", "Smith, Malachi", "Out",
     "G League - Two-Way", _INHERIT.format(blk="NYK@TOR")],

    ["2026-11-15", "07:00", "HOU@WAS", "Houston Rockets", "Adams, Steven", "Available",
     "Injury/Illness - Right Soleus Strain"],
    ["2026-11-15", "07:00", "HOU@WAS", "Houston Rockets", "Capela, Clint", "Out",
     "Injury/Illness - Right Ankle Sprain"],
    ["2026-11-15", "07:00", "HOU@WAS", "Houston Rockets", "Copeland, Quadir", "Out",
     "G League - Two-Way"],
    ["2026-11-15", "07:00", "HOU@WAS", "Houston Rockets", "Phillips, Julian", "Out",
     "G League - Two-Way"],
    ["2026-11-15", "07:00", "HOU@WAS", "Houston Rockets", "Smart, Marcus", "Out",
     "League Suspension"],
    ["2026-11-15", "07:00", "HOU@WAS", "Houston Rockets", "VanVleet, Fred", "Out",
     "Injury/Illness - Right Knee Injury Management"],
    ["2026-11-15", "07:00", "HOU@WAS", "Washington Wizards", "Beekman, Reece", "Out",
     "Injury/Illness - Right AC Joint Injury"],
    ["2026-11-15", "07:00", "HOU@WAS", "Washington Wizards", "Carrington, Bub", "Available",
     "Injury/Illness - Chest / Sternum Contusion"],
    ["2026-11-15", "07:00", "HOU@WAS", "Washington Wizards", "Champagne, Justin", "Out",
     "Injury/Illness - Right Foot Surgery"],
    ["2026-11-15", "07:00", "HOU@WAS", "Washington Wizards", "Johnson, Tre", "Out",
     "Injury/Illness - Low Back Soreness"],
    ["2026-11-15", "07:00", "HOU@WAS", "Washington Wizards", "Okpara, Felix", "Out",
     "G League - Two-Way", _CONT.format(blk="HOU@WAS")],
    ["2026-11-15", "07:00", "HOU@WAS", "Washington Wizards", "Sarr, Alex", "Available",
     "Injury/Illness - Illness", _CONT.format(blk="HOU@WAS")],
    ["2026-11-15", "07:00", "HOU@WAS", "Washington Wizards", "Vukcevic, Tristan", "Out",
     "Injury/Illness - Left Hip Impingement", _CONT.format(blk="HOU@WAS")],
    ["2026-11-15", "07:00", "HOU@WAS", "Washington Wizards", "Watkins, Jamir", "Out",
     "Injury/Illness - Left ACL Repair / Surgery", _CONT.format(blk="HOU@WAS")],

    ["2026-11-15", "08:00", "ATL@MIL", "Atlanta Hawks", "Flemings, Kingston", "Out",
     "Injury/Illness - Lumbar Strain"],
    ["2026-11-15", "08:00", "ATL@MIL", "Atlanta Hawks", "Gilbert, Keshon", "Out",
     "Injury/Illness - Left Knee Inflammation; Non-Surgical Procedure"],
    ["2026-11-15", "08:00", "ATL@MIL", "Atlanta Hawks", "Gueye, Mouhamed", "Out",
     "Injury/Illness - Left Foot Fracture"],
    ["2026-11-15", "08:00", "ATL@MIL", "Atlanta Hawks", "Landale, Jock", "Out",
     "Injury/Illness - Right Hip Inflammation", _CONT.format(blk="ATL@MIL")],
    ["2026-11-15", "08:00", "ATL@MIL", "Atlanta Hawks", "Newell, Asa", "Out",
     "Injury/Illness - Left Great Toe Hyperextension"],
    ["2026-11-15", "08:00", "ATL@MIL", "Atlanta Hawks", "Veesaar, Henri", "Out",
     "Injury/Illness - Right ACL Tear"],
    ["2026-11-15", "08:00", "ATL@MIL", "Atlanta Hawks", "Wilson, Jalen", "Out",
     "G League - Two-Way"],
    ["2026-11-15", "08:00", "ATL@MIL", "Milwaukee Bucks", "Dieng, Ousmane", "Out",
     "Injury/Illness - Left Finger Fracture"],
    ["2026-11-15", "08:00", "ATL@MIL", "Milwaukee Bucks", "Jones, Kam", "Out",
     "G League - Two-Way"],
    ["2026-11-15", "08:00", "ATL@MIL", "Milwaukee Bucks", "Markovic, Bogoljub", "Out",
     "G League - On Assignment"],
    ["2026-11-15", "08:00", "ATL@MIL", "Milwaukee Bucks", "Nance, Pete", "Out",
     "G League - Two-Way"],
    ["2026-11-15", "08:00", "ATL@MIL", "Milwaukee Bucks", "Rollins, Ryan", "Out",
     "Injury/Illness - Illness"],
    ["2026-11-15", "08:00", "ATL@MIL", "Milwaukee Bucks", "Ryan, Cormac", "Out",
     "G League - Two-Way", _CONT.format(blk="ATL@MIL")],

    ["2026-11-15", "09:00", "OKC@SAC", "Oklahoma City Thunder", "Holmgren, Chet", "Out",
     "Injury/Illness - Right Knee/ Injury Recovery"],
    ["2026-11-15", "09:00", "OKC@SAC", "Oklahoma City Thunder", "Mitchell, Ajay", "Questionable",
     "Injury/Illness - Left Ankle Sprain"],
    ["2026-11-15", "09:00", "OKC@SAC", "Oklahoma City Thunder", "Sorber, Thomas", "Out",
     "Injury/Illness - Right Knee Surgery"],
    ["2026-11-15", "09:00", "OKC@SAC", "Oklahoma City Thunder", "Wallace, Cason", "Out",
     "Injury/Illness - Left Shoulder Surgery"],
    ["2026-11-15", "09:00", "OKC@SAC", "Oklahoma City Thunder", "Williams, Jalen", "Out",
     "Injury/Illness - Left Ankle Surgery"],
    ["2026-11-15", "09:00", "OKC@SAC", "Oklahoma City Thunder", "Williams, Jaylin", "Out",
     "Injury/Illness - Low Back Spasms"],
    ["2026-11-15", "09:00", "OKC@SAC", "Sacramento Kings", "Achiuwa, Precious", "Questionable",
     "Injury/Illness - Left Ankle Soreness"],
    ["2026-11-15", "09:00", "OKC@SAC", "Sacramento Kings", "Mogbo, Jonathan", "Out",
     "G League - Two-Way"],
    ["2026-11-15", "09:00", "OKC@SAC", "Sacramento Kings", "Murray, Keegan", "Available", "-"],
    ["2026-11-15", "09:00", "OKC@SAC", "Sacramento Kings", "Pedulla, Sean", "Out",
     "G League - Two-Way"],
    ["2026-11-15", "09:00", "OKC@SAC", "Sacramento Kings", "Raynaud, Maxime", "Out",
     "Injury/Illness - Right Patella Subluxation"],
    ["2026-11-15", "09:00", "OKC@SAC", "Sacramento Kings", "Simmons, Ben", "Out",
     "Injury/Illness - Right Achilles Tendon Repair / Surgery"],

    # ---------------- 2026-11-16 ----------------
    ["2026-11-16", "07:00", "CHI@CLE", "Chicago Bulls", "Awaka, Tobe", "Out",
     "Injury/Illness - Disc Irritation"],
    ["2026-11-16", "07:00", "CHI@CLE", "Chicago Bulls", "Robinson, Orlando", "Out",
     "G League - On Assignment"],
    ["2026-11-16", "07:00", "CHI@CLE", "Chicago Bulls", "Sellers, Jaylin", "Out",
     "G League - Two-Way"],
    ["2026-11-16", "07:00", "CHI@CLE", "Chicago Bulls", "Smith, Jalen", "Questionable",
     "Injury/Illness - Left Finger Sprain"],
    ["2026-11-16", "07:00", "CHI@CLE", "Chicago Bulls", "Wilson, Caleb", "Out",
     "Injury/Illness - Right Metacarpal Fracture"],
    ["2026-11-16", "07:00", "CHI@CLE", "Cleveland Cavaliers", "Diop, Khalifa", "Out",
     "G League - On Assignment", _INHERIT.format(blk="CHI@CLE")],
    ["2026-11-16", "07:00", "CHI@CLE", "Cleveland Cavaliers", "Merrill, Sam", "Out",
     "Injury/Illness - Right Elbow Injury Management", _INHERIT.format(blk="CHI@CLE")],
    ["2026-11-16", "07:00", "CHI@CLE", "Cleveland Cavaliers", "Mobley, Evan", "Out",
     "Injury/Illness - Left Great Toe Sprain", _INHERIT.format(blk="CHI@CLE")],
    ["2026-11-16", "07:00", "CHI@CLE", "Cleveland Cavaliers", "Tomlin, Nae'Qwan", "Out",
     "Injury/Illness - Low Back Stress Reaction", _INHERIT.format(blk="CHI@CLE")],
    ["2026-11-16", "07:00", "CHI@CLE", "Cleveland Cavaliers", "Tyson, Jaylon", "Questionable",
     "Injury/Illness - Right Ankle Injury Management", _INHERIT.format(blk="CHI@CLE")],
    ["2026-11-16", "07:00", "CHI@CLE", "Cleveland Cavaliers", "Udeh, Jr., Ernest", "Out",
     "G League - Two-Way", _INHERIT.format(blk="CHI@CLE")],
    ["2026-11-16", "07:00", "CHI@CLE", "Cleveland Cavaliers", "Watson, Peyton", "Questionable",
     "Injury/Illness - Right Abdominal Soreness", _INHERIT.format(blk="CHI@CLE")],

    ["2026-11-16", "07:00", "MEM@WAS", "Memphis Grizzlies", "Edey, Zach", "Questionable",
     "Injury/Illness - Left Ankle Injury Management", _INHERIT.format(blk="MEM@WAS")],
    ["2026-11-16", "07:00", "MEM@WAS", "Memphis Grizzlies", "Jackson, GG", "Out",
     "Injury/Illness - Left Foot Injury", _INHERIT.format(blk="MEM@WAS")],
    ["2026-11-16", "07:00", "MEM@WAS", "Memphis Grizzlies", "Jerome, Ty", "Out",
     "Injury/Illness - Right Hip Soreness", _INHERIT.format(blk="MEM@WAS")],
    ["2026-11-16", "07:00", "MEM@WAS", "Memphis Grizzlies", "Pippen Jr., Scotty", "Out",
     "Injury/Illness - Lumbar Disc Herniation", _INHERIT.format(blk="MEM@WAS")],
    ["2026-11-16", "07:00", "MEM@WAS", "Memphis Grizzlies", "Post, Quinten", "Questionable",
     "Injury/Illness - Concussion Protocol", _INHERIT.format(blk="MEM@WAS")],
    ["2026-11-16", "07:00", "MEM@WAS", "Memphis Grizzlies", "Saunders, Richie", "Out",
     "Injury/Illness - Right Knee Surgery", _INHERIT.format(blk="MEM@WAS")],
    ["2026-11-16", "07:00", "MEM@WAS", "Memphis Grizzlies", "Stewart, Isaiah", "Questionable",
     "Injury/Illness - Illness", _INHERIT.format(blk="MEM@WAS")],
    ["2026-11-16", "07:00", "MEM@WAS", "Washington Wizards", "", "",
     "NOT YET SUBMITTED", _INHERIT.format(blk="MEM@WAS")],

    ["2026-11-16", "07:00", "ORL@BOS", "Orlando Magic", "Banchero, Paolo", "Out",
     "Injury/Illness - Right High Ankle Sprain", _INHERIT.format(blk="ORL@BOS")],
    ["2026-11-16", "07:00", "ORL@BOS", "Orlando Magic", "Isaac, Jonathan", "Out",
     "Injury/Illness - Left Knee Injury Management", _INHERIT.format(blk="ORL@BOS")],
    ["2026-11-16", "07:00", "ORL@BOS", "Orlando Magic", "Nelson, Izaiyah", "Out",
     "Injury/Illness - Left Ankle Injury Recovery", _INHERIT.format(blk="ORL@BOS")],
    ["2026-11-16", "07:00", "ORL@BOS", "Orlando Magic", "Penda, Noah", "Out",
     "Injury/Illness - Right Partially Torn Hamstring", _INHERIT.format(blk="ORL@BOS")],
    # PDF prints a second "Penda, Noah" row under the *Boston Celtics* team cell. Copied
    # verbatim; flagged as I-F8F-02 (the name is the Orlando player's).
    ["2026-11-16", "07:00", "ORL@BOS", "Boston Celtics", "Penda, Noah", "Out",
     "NOT YET SUBMITTED", _INHERIT.format(blk="ORL@BOS")],

    ["2026-11-16", "07:30", "HOU@MIA", "Houston Rockets", "", "", "NOT YET SUBMITTED"],
    ["2026-11-16", "07:30", "HOU@MIA", "Miami Heat", "Goldin, Vladislav", "Out",
     "G League - Two-Way"],
    ["2026-11-16", "07:30", "HOU@MIA", "Miami Heat", "Larsson, Pelle", "Questionable",
     "Injury/Illness - Illness"],
    ["2026-11-16", "07:30", "HOU@MIA", "Miami Heat", "Thompson, Klay", "Available",
     "Injury/Illness - Left Ankle Sprain"],

    ["2026-11-16", "07:30", "PHI@BKN", "Philadelphia 76ers", "", "", "NOT YET SUBMITTED"],
    ["2026-11-16", "07:30", "PHI@BKN", "Brooklyn Nets", "Bilodeau, Tyler", "Out",
     "G League - Two-Way"],
    ["2026-11-16", "07:30", "PHI@BKN", "Brooklyn Nets", "Jefferson, Joshua", "Out",
     "G League - On Assignment"],
    ["2026-11-16", "07:30", "PHI@BKN", "Brooklyn Nets", "Nelson, Grant", "Out",
     "G League - Two-Way"],
    ["2026-11-16", "07:30", "PHI@BKN", "Brooklyn Nets", "Powell, Drake", "Out",
     "G League - On Assignment"],
    ["2026-11-16", "07:30", "PHI@BKN", "Brooklyn Nets", "Saraf, Ben", "Out",
     "G League - On Assignment"],

    ["2026-11-16", "08:00", "GSW@NOP", "Golden State Warriors", "Butler III, Jimmy", "Out",
     "Injury/Illness - Right ACL Repair / Surgery"],
    ["2026-11-16", "08:00", "GSW@NOP", "Golden State Warriors", "Curry, Stephen", "Out",
     "Injury/Illness - Right Oblique Tear", _CONT.format(blk="GSW@NOP")],
    ["2026-11-16", "08:00", "GSW@NOP", "Golden State Warriors", "Moody, Moses", "Out",
     "Injury/Illness - Left Patellar Tendon Repair / Surgery", _CONT.format(blk="GSW@NOP")],
    ["2026-11-16", "08:00", "GSW@NOP", "Golden State Warriors", "Porzingis, Kristaps", "Out",
     "Not With Team", _CONT.format(blk="GSW@NOP")],
    ["2026-11-16", "08:00", "GSW@NOP", "Golden State Warriors", "Santos, Gui", "Questionable",
     "Injury/Illness - Right Ankle Inflammation", _CONT.format(blk="GSW@NOP")],
    ["2026-11-16", "08:00", "GSW@NOP", "Golden State Warriors", "Williams, Brandon", "Out",
     "Injury/Illness - Left Hamstring Strain", _CONT.format(blk="GSW@NOP")],
    ["2026-11-16", "08:00", "GSW@NOP", "New Orleans Pelicans", "Dia, Malik", "Questionable",
     "G League - Two-Way"],
    ["2026-11-16", "08:00", "GSW@NOP", "New Orleans Pelicans", "Mathurin, Bennedict", "Out",
     "Injury/Illness - Left Plantar Fasciitis"],
    ["2026-11-16", "08:00", "GSW@NOP", "New Orleans Pelicans", "McGowens, Bryce", "Out",
     "Injury/Illness - Left Elbow Infection"],
    ["2026-11-16", "08:00", "GSW@NOP", "New Orleans Pelicans", "Murphy III, Trey", "Out",
     "Injury/Illness - Bilateral Patellar Tendinopathy"],
    ["2026-11-16", "08:00", "GSW@NOP", "New Orleans Pelicans", "Murray, Dejounte", "Out",
     "Injury/Illness - Left Ankle Sprain"],
    ["2026-11-16", "08:00", "GSW@NOP", "New Orleans Pelicans", "Pierre Jr., Jaron", "Questionable",
     "G League - Two-Way"],
    ["2026-11-16", "08:00", "GSW@NOP", "New Orleans Pelicans", "Reese, Julian", "Questionable",
     "G League - Two-Way"],
    ["2026-11-16", "08:00", "GSW@NOP", "New Orleans Pelicans", "Watford, Trendon", "Out",
     "Injury/Illness - Right Ankle Sprain"],

    ["2026-11-16", "08:00", "POR@MIN", "Portland Trail Blazers", "Krejci, Vit", "Out",
     "Injury/Illness - Left Ankle Fracture"],
    ["2026-11-16", "08:00", "POR@MIN", "Portland Trail Blazers", "Morant, Ja", "Out",
     "Injury/Illness - Left Hamstring Strain"],
    ["2026-11-16", "08:00", "POR@MIN", "Portland Trail Blazers", "Sharpe, Shaedon", "Out",
     "Injury/Illness - Right Knee Surgery"],
    ["2026-11-16", "08:00", "POR@MIN", "Portland Trail Blazers", "Youngblood, Chris", "Out",
     "Injury/Illness - Right Heel Contusion / Bone Bruise"],
    ["2026-11-16", "08:00", "POR@MIN", "Minnesota Timberwolves", "Beringer, Joan", "Available",
     "Injury/Illness - Face Mask", _INHERIT.format(blk="POR@MIN")],
    ["2026-11-16", "08:00", "POR@MIN", "Minnesota Timberwolves", "Clark, Jaylen", "Out",
     "Injury/Illness - Right Hamstring Strain", _INHERIT.format(blk="POR@MIN")],
    ["2026-11-16", "08:00", "POR@MIN", "Minnesota Timberwolves", "DiVincenzo, Donte", "Out",
     "Injury/Illness - Right Achilles Tendon Repair / Surgery", _INHERIT.format(blk="POR@MIN")],
    ["2026-11-16", "08:00", "POR@MIN", "Minnesota Timberwolves", "Edwards, Anthony", "Out",
     "Injury/Illness - Right Knee Arthroscopy", _INHERIT.format(blk="POR@MIN")],

    ["2026-11-16", "09:00", "PHX@DEN", "Phoenix Suns", "", "", "NOT YET SUBMITTED"],
    ["2026-11-16", "09:00", "PHX@DEN", "Denver Nuggets", "", "", "NOT YET SUBMITTED"],
]


def main() -> None:
    am = json.loads(AM_FILE.read_text())
    am_rows = am["records"]

    for r in ROWS:
        if len(r) not in (7, 8):
            raise SystemExit(f"bad row width {len(r)}: {r}")
        if r[2] and not r[3]:
            raise SystemExit(f"matchup without team: {r}")

    doc = {
        "schema": "nba2.injury-transcript.v1",
        "report_stamp_et": "2026-11-15 06:15 PM ET",
        "revision_time_et": "2026-11-15 06:15 PM ET",
        "retrieved_at_utc": RETRIEVED_AT_UTC,
        "retrieval_method": "platform page-fetch tool (fetch_page) against the official PDF",
        "provenance": {
            "publisher": "NBA Official Injury Report (official)",
            "url": PM_PDF_URL,
            "index_url": INDEX_URL,
            "prior_release_url": AM_PDF_URL,
            "note": (
                "Newest 2026-11-15 release listed on the league's official index at retrieval "
                "time (the index rendered links through the 06:15 PM ET stamp). Rows "
                "transcribed verbatim from the PDF text. Three layout quirks of the PDF itself "
                "are recorded, not corrected: (I-F8F-01) page-continuation rows print with an "
                "empty team / date / time / matchup cell and are attributed by table position; "
                "(I-F8F-02) the ORL@BOS block prints a second 'Penda, Noah' row under the "
                "Boston Celtics team cell; (I-F8F-03) the NYK@TOR block contains no New York "
                "Knicks rows at all in this release, not even a 'NOT YET SUBMITTED' "
                "placeholder. (I-F8F-04) the PDF prints game times in 12-hour form with no "
                "AM/PM marker; the 24-hour ET times in slate_2026-11-15_to_11-18.json (read "
                "from nba.com) are the authoritative clock."
            ),
        },
        "columns": ["date", "time_et", "matchup", "team", "player", "status", "reason"],
        "records": ROWS,
    }
    PM_FILE.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")

    # ---- diff ----
    def key(r):
        return (r[0], r[2], r[3], r[4])

    am_map = {}
    for r in am_rows:
        am_map.setdefault(key(r), []).append(r)
    pm_map = {}
    for r in ROWS:
        pm_map.setdefault(key(r), []).append(r)

    changed, added, removed, unchanged = [], [], [], []
    for k in sorted(set(am_map) | set(pm_map)):
        a = am_map.get(k, [None])[0]
        p = pm_map.get(k, [None])[0]
        if a is None:
            added.append(k + (p[5], p[6]))
        elif p is None:
            removed.append(k + (a[5], a[6]))
        elif a[5] != p[5] or a[6] != p[6]:
            changed.append(k + (a[5], a[6], p[5], p[6]))
        else:
            unchanged.append(k)

    delta = {
        "schema": "nba2.injury-delta.v1",
        "from_release": {"stamp_et": am["report_stamp_et"], "url": AM_PDF_URL,
                         "rows": len(am_rows)},
        "to_release": {"stamp_et": "2026-11-15 06:15 PM ET", "url": PM_PDF_URL,
                       "rows": len(ROWS)},
        "elapsed": "12h00m (06:15 AM ET -> 06:15 PM ET, same calendar day)",
        "retrieved_at_utc": RETRIEVED_AT_UTC,
        "match_key": ["date", "matchup", "team", "player"],
        "counts": {"status_changed": len(changed), "added": len(added),
                   "removed": len(removed), "unchanged": len(unchanged)},
        "status_changes": [
            {"date": c[0], "matchup": c[1], "team": c[2], "player": c[3],
             "from_status": c[4], "to_status": c[6],
             "reason_from": c[5], "reason_to": c[7],
             "reason_changed": c[5] != c[7]}
            for c in changed
        ],
        "added": [{"date": a[0], "matchup": a[1], "team": a[2], "player": a[3],
                   "status": a[4], "reason": a[5]} for a in added],
        "removed": [{"date": r[0], "matchup": r[1], "team": r[2], "player": r[3],
                     "status": r[4], "reason": r[5]} for r in removed],
        "note": (
            "Diff is mechanical: rows are matched on (date, matchup, team, player) and any "
            "difference in status or reason is reported. 'Added' includes both newly-reported "
            "players and teams that replaced a single 'NOT YET SUBMITTED' placeholder with a "
            "full submission, so a large added count between a morning and an evening release "
            "is expected, not an error. Rows flagged I-F8F-01 (layout-attributed team) still "
            "diff correctly because the 06:15 AM transcript uses the same attribution rule."
        ),
    }
    DELTA_FILE.write_text(json.dumps(delta, indent=2, ensure_ascii=False) + "\n")

    h = hashlib.sha256(json.dumps(ROWS, ensure_ascii=False).encode()).hexdigest()
    print(f"PM rows: {len(ROWS)}  (AM rows: {len(am_rows)})")
    print(f"status_changed={len(changed)} added={len(added)} removed={len(removed)} "
          f"unchanged={len(unchanged)}")
    print("row-set sha256:", h[:16])
    print()
    for c in changed:
        mark = " + reason" if c[5] != c[7] else ""
        print(f"  CHANGE {c[1]:9} {c[3]:28} {c[4]:12} -> {c[6]:12}{mark}")


if __name__ == "__main__":
    main()
