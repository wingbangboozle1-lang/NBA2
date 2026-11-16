"""The 2026-11-16 01:00 PM ET official injury release, transcribed.

Kept as its own module so the transcription is reviewable on its own and the diff
against the 09:15 AM release can be reproduced without touching the capture module.

Source (official): https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-16_01_00PM.pdf
Index that publishes it (official): https://official.nba.com/nba-injury-report-2026-27-season/

How the columns are read
------------------------
The official PDF has seven columns: Game Date | Game Time | Matchup | Team | Player Name |
Current Status | Reason. The text extraction drops EMPTY leading cells, so a row can print
with fewer than seven cells. A row is reconstructed as follows, and never by inference:

* seven cells  -> read positionally;
* six cells    -> Game Date is empty (a page-continuation row). The date, time and matchup
                  are taken from the block the row is printed in, which the PDF itself
                  establishes, and the reconstruction is recorded in the row's note;
* five cells   -> Game Date and Game Time are empty. Matchup is the first cell;
* four cells    -> Game Date, Game Time and Matchup are empty. The team is taken from the
                  block context.

A cell whose text is a league status word (Out / Questionable / Doubtful / Available /
Probable) is a Current Status. A cell whose text is not one of those is a Reason. When a
row prints a Reason but no status word, the STATUS IS LEFT BLANK and the reason is kept:
the status is not confirmed by the official text, so it is not published. That is flagged
F-V4-10 and is the only row in this release affected.
"""

from __future__ import annotations

STATUS_WORDS = ("Out", "Questionable", "Doubtful", "Available", "Probable", "Suspended")

D = "2026-11-16"
D17 = "2026-11-17"

# (date, time_et, matchup, team, player, status, reason, note)
ROWS: list[list[str]] = [
    # ---------------------------------------------------------------- CHI@CLE 07:00
    [D, "07:00", "CHI@CLE", "Chicago Bulls", "Awaka, Tobe", "Out", "Injury/Illness - Disc Irritation", ""],
    [D, "07:00", "CHI@CLE", "Chicago Bulls", "Robinson, Orlando", "Out", "G League - On Assignment", ""],
    [D, "07:00", "CHI@CLE", "Chicago Bulls", "Sellers, Jaylin", "Out", "G League - Two-Way", ""],
    [D, "07:00", "CHI@CLE", "Chicago Bulls", "Smith, Jalen", "Questionable", "Injury/Illness - Left Finger Sprain", ""],
    [D, "07:00", "CHI@CLE", "Chicago Bulls", "Wilson, Caleb", "Out", "Injury/Illness - Right Metacarpal Fracture", ""],
    [D, "07:00", "CHI@CLE", "Cleveland Cavaliers", "Diop, Khalifa", "Out", "G League - On Assignment", ""],
    [D, "07:00", "CHI@CLE", "Cleveland Cavaliers", "Merrill, Sam", "Out", "Injury/Illness - Right Elbow Injury Management", ""],
    [D, "07:00", "CHI@CLE", "Cleveland Cavaliers", "Mobley, Evan", "Out", "Injury/Illness - Left Great Toe Sprain", ""],
    [D, "07:00", "CHI@CLE", "Cleveland Cavaliers", "Tomlin, Nae'Qwan", "Out", "Injury/Illness - Low Back Stress Reaction", ""],
    [D, "07:00", "CHI@CLE", "Cleveland Cavaliers", "Tyson, Jaylon", "Doubtful", "Injury/Illness - Right Ankle Injury Management", ""],
    [D, "07:00", "CHI@CLE", "Cleveland Cavaliers", "Udeh, Jr., Ernest", "Out", "G League - Two-Way", ""],
    [D, "07:00", "CHI@CLE", "Cleveland Cavaliers", "Watson, Peyton", "Questionable", "Injury/Illness - Right Abdominal Soreness", ""],
    # ---------------------------------------------------------------- MEM@WAS 07:00
    [D, "07:00", "MEM@WAS", "Memphis Grizzlies", "Edey, Zach", "Questionable", "Injury/Illness - Left Ankle Injury Management", ""],
    [D, "07:00", "MEM@WAS", "Memphis Grizzlies", "Jackson, GG", "Out", "Injury/Illness - Left 5th Metatarsal", ""],
    [D, "07:00", "MEM@WAS", "Memphis Grizzlies", "Jerome, Ty", "Out", "Injury/Illness - Right Hip Soreness",
     "F-V4-05 continuation row: the PDF drops the date, time and matchup cells at the page break; taken from the MEM@WAS block it is printed in"],
    [D, "07:00", "MEM@WAS", "Memphis Grizzlies", "Pippen Jr., Scotty", "Out", "Injury/Illness - Lumbar Disc Herniation",
     "F-V4-05 continuation row: date, time and matchup taken from the MEM@WAS block"],
    [D, "07:00", "MEM@WAS", "Memphis Grizzlies", "Post, Quinten", "Questionable", "Injury/Illness - Concussion Protocol",
     "F-V4-05 continuation row: date, time and matchup taken from the MEM@WAS block"],
    [D, "07:00", "MEM@WAS", "Memphis Grizzlies", "Saunders, Richie", "Out", "Injury/Illness - Right Knee Surgery",
     "F-V4-05 continuation row: date, time and matchup taken from the MEM@WAS block"],
    [D, "07:00", "MEM@WAS", "Memphis Grizzlies", "Stewart, Isaiah", "Out", "Injury/Illness - Illness",
     "F-V4-05 continuation row: date, time and matchup taken from the MEM@WAS block"],
    [D, "07:00", "MEM@WAS", "Washington Wizards", "Beekman, Reece", "Out", "Injury/Illness - Right AC Joint Injury", ""],
    [D, "07:00", "MEM@WAS", "Washington Wizards", "Champagne, Justin", "Out", "Injury/Illness - Right Foot Surgery", ""],
    [D, "07:00", "MEM@WAS", "Washington Wizards", "Johnson, Tre", "Questionable", "Injury/Illness - Low Back Soreness", ""],
    [D, "07:00", "MEM@WAS", "Washington Wizards", "Okpara, Felix", "Questionable", "G League - Two-Way", ""],
    [D, "07:00", "MEM@WAS", "Washington Wizards", "Vukcevic, Tristan", "Out", "Injury/Illness - Left Hip Impingement", ""],
    [D, "07:00", "MEM@WAS", "Washington Wizards", "Watkins, Jamir", "Out", "Injury/Illness - Left ACL Repair / Surgery", ""],
    # ---------------------------------------------------------------- ORL@BOS 07:00
    [D, "07:00", "ORL@BOS", "Orlando Magic", "Banchero, Paolo", "Out", "Injury/Illness - Right High Ankle Sprain",
     "F-V4-05 continuation row: the PDF drops the date and time cells; taken from the ORL@BOS block it is printed in"],
    [D, "07:00", "ORL@BOS", "Orlando Magic", "Isaac, Jonathan", "Out", "Injury/Illness - Left Knee Injury Management",
     "F-V4-05 continuation row: date and time taken from the ORL@BOS block"],
    [D, "07:00", "ORL@BOS", "Orlando Magic", "Nelson, Izaiyah", "Out", "Injury/Illness - Left Ankle Injury Recovery",
     "F-V4-05 continuation row: date and time taken from the ORL@BOS block"],
    [D, "07:00", "ORL@BOS", "Orlando Magic", "Penda, Noah", "Out", "Injury/Illness - Right Partially Torn Hamstring",
     "F-V4-05 continuation row: date and time taken from the ORL@BOS block"],
    [D, "07:00", "ORL@BOS", "Boston Celtics", "", "", "NOT YET SUBMITTED",
     "the league's own placeholder row: Boston has not filed a report for this game as of this release"],
    # ---------------------------------------------------------------- HOU@MIA 07:30
    [D, "07:30", "HOU@MIA", "Houston Rockets", "Adams, Steven", "Out", "Injury/Illness - Left Lower Leg Injury Management", ""],
    [D, "07:30", "HOU@MIA", "Houston Rockets", "Capela, Clint", "Out", "Injury/Illness - Right Ankle Sprain", ""],
    [D, "07:30", "HOU@MIA", "Houston Rockets", "Copeland, Quadir", "Out", "G League - Two-Way", ""],
    [D, "07:30", "HOU@MIA", "Houston Rockets", "Phillips, Julian", "Out", "G League - Two-Way", ""],
    [D, "07:30", "HOU@MIA", "Houston Rockets", "Smart, Marcus", "Out", "League Suspension", ""],
    [D, "07:30", "HOU@MIA", "Houston Rockets", "Thompson, Amen", "Questionable", "Injury/Illness - Left Knee Soreness", ""],
    [D, "07:30", "HOU@MIA", "Miami Heat", "Goldin, Vladislav", "Out", "G League - Two-Way", ""],
    [D, "07:30", "HOU@MIA", "Miami Heat", "Jovic, Nikola", "Questionable", "Injury/Illness - Illness", ""],
    [D, "07:30", "HOU@MIA", "Miami Heat", "Larsson, Pelle", "Doubtful", "Injury/Illness - Illness", ""],
    [D, "07:30", "HOU@MIA", "Miami Heat", "Thompson, Klay", "Available", "Injury/Illness - Left Ankle Sprain", ""],
    # ---------------------------------------------------------------- PHI@BKN 07:30
    [D, "07:30", "PHI@BKN", "Philadelphia 76ers", "Barlow, Dominick", "Out", "Injury/Illness - Low Back Stress Reaction", ""],
    [D, "07:30", "PHI@BKN", "Philadelphia 76ers", "Bona, Adem", "Out", "Injury/Illness - Cervical Spine Sprain", ""],
    [D, "07:30", "PHI@BKN", "Philadelphia 76ers", "Embiid, Joel", "Questionable", "Injury/Illness - Right Foot Plantar Fascia Injury Management", ""],
    [D, "07:30", "PHI@BKN", "Philadelphia 76ers", "Hukporti, Ariel", "Out", "Injury/Illness - Right Achilles Tendon Rupture / Tear", ""],
    [D, "07:30", "PHI@BKN", "Philadelphia 76ers", "James, LeBron", "Out", "Injury/Illness - Low Back/Sciatica Management", ""],
    [D, "07:30", "PHI@BKN", "Brooklyn Nets", "Bilodeau, Tyler", "Out", "G League - Two-Way",
     "F-V4-05 continuation row: the PDF drops the date and time cells; taken from the PHI@BKN block it is printed in"],
    [D, "07:30", "PHI@BKN", "Brooklyn Nets", "Jefferson, Joshua", "Out", "G League - On Assignment",
     "F-V4-05 continuation row: date and time taken from the PHI@BKN block"],
    [D, "07:30", "PHI@BKN", "Brooklyn Nets", "Nelson, Grant", "Out", "G League - Two-Way",
     "F-V4-05 continuation row: date and time taken from the PHI@BKN block"],
    [D, "07:30", "PHI@BKN", "Brooklyn Nets", "Powell, Drake", "Out", "G League - On Assignment",
     "F-V4-05 continuation row: date and time taken from the PHI@BKN block"],
    [D, "07:30", "PHI@BKN", "Brooklyn Nets", "Saraf, Ben", "Out", "G League - On Assignment",
     "F-V4-05 continuation row: date and time taken from the PHI@BKN block"],
    # ---------------------------------------------------------------- GSW@NOP 08:00
    [D, "08:00", "GSW@NOP", "Golden State Warriors", "Butler III, Jimmy", "", "Injury/Illness - Right ACL Repair / Surgery",
     "F-V4-10 this row prints no Current Status cell; only the reason is legible, so the status is left BLANK and flagged. Never inferred."],
    [D, "08:00", "GSW@NOP", "Golden State Warriors", "Curry, Stephen", "Out", "",
     "F-V4-11 this row prints the status but no reason; the status is read from the status column and the reason is left blank, not inferred"],
    [D, "08:00", "GSW@NOP", "Golden State Warriors", "Moody, Moses", "Out", "",
     "F-V4-11 status legible, reason cell empty in the PDF"],
    [D, "08:00", "GSW@NOP", "Golden State Warriors", "Porzingis, Kristaps", "Out", "",
     "F-V4-11 status legible, reason cell empty in the PDF"],
    [D, "08:00", "GSW@NOP", "Golden State Warriors", "Santos, Gui", "Questionable", "",
     "F-V4-11 status legible, reason cell empty in the PDF"],
    [D, "08:00", "GSW@NOP", "Golden State Warriors", "Williams, Brandon", "Out", "",
     "F-V4-11 status legible, reason cell empty in the PDF"],
    [D, "08:00", "GSW@NOP", "New Orleans Pelicans", "Dia, Malik", "Questionable", "G League - Two-Way", ""],
    [D, "08:00", "GSW@NOP", "New Orleans Pelicans", "Mathurin, Bennedict", "Out", "Injury/Illness - Left Plantar Fasciitis", ""],
    [D, "08:00", "GSW@NOP", "New Orleans Pelicans", "McGowens, Bryce", "Out", "Injury/Illness - Left Elbow Infection", ""],
    [D, "08:00", "GSW@NOP", "New Orleans Pelicans", "Murphy III, Trey", "Out", "Injury/Illness - Bilateral Patellar Tendinopathy", ""],
    [D, "08:00", "GSW@NOP", "New Orleans Pelicans", "Murray, Dejounte", "Out", "Injury/Illness - Left Ankle Sprain", ""],
    [D, "08:00", "GSW@NOP", "New Orleans Pelicans", "Pierre Jr., Jaron", "Questionable", "G League - Two-Way", ""],
    [D, "08:00", "GSW@NOP", "New Orleans Pelicans", "Reese, Julian", "Questionable", "G League - Two-Way",
     "F-V4-05 continuation row: date, time and matchup taken from the GSW@NOP block"],
    [D, "08:00", "GSW@NOP", "New Orleans Pelicans", "Watford, Trendon", "Out", "Injury/Illness - Right Ankle Sprain",
     "F-V4-05 continuation row: date, time and matchup taken from the GSW@NOP block"],
    # ---------------------------------------------------------------- POR@MIN 08:00
    [D, "08:00", "POR@MIN", "Portland Trail Blazers", "Krejci, Vit", "Out", "Injury/Illness - Left Ankle Fracture",
     "F-V4-05 continuation row: date and time taken from the POR@MIN block"],
    [D, "08:00", "POR@MIN", "Portland Trail Blazers", "Morant, Ja", "Out", "Injury/Illness - Left Hamstring Strain",
     "F-V4-05 continuation row: date and time taken from the POR@MIN block"],
    [D, "08:00", "POR@MIN", "Portland Trail Blazers", "Sharpe, Shaedon", "Out", "Injury/Illness - Right Knee Surgery",
     "F-V4-05 continuation row: date and time taken from the POR@MIN block"],
    [D, "08:00", "POR@MIN", "Portland Trail Blazers", "Youngblood, Chris", "Out", "Injury/Illness - Right Heel Contusion / Bone Bruise",
     "F-V4-05 continuation row: date and time taken from the POR@MIN block"],
    [D, "08:00", "POR@MIN", "Minnesota Timberwolves", "Beringer, Joan", "Available", "Injury/Illness - Face Mask",
     "F-V4-05 continuation row: date and time taken from the POR@MIN block"],
    [D, "08:00", "POR@MIN", "Minnesota Timberwolves", "Clark, Jaylen", "Out", "Injury/Illness - Right Hamstring Strain",
     "F-V4-05 continuation row: date and time taken from the POR@MIN block"],
    [D, "08:00", "POR@MIN", "Minnesota Timberwolves", "DiVincenzo, Donte", "Out", "Injury/Illness - Right Achilles Tendon Repair / Surgery",
     "F-V4-05 continuation row: date and time taken from the POR@MIN block"],
    [D, "08:00", "POR@MIN", "Minnesota Timberwolves", "Edwards, Anthony", "Out", "Injury/Illness - Right Knee Arthroscopy",
     "F-V4-05 continuation row: date and time taken from the POR@MIN block"],
    # ---------------------------------------------------------------- PHX@DEN 09:00
    [D, "09:00", "PHX@DEN", "Phoenix Suns", "", "", "NOT YET SUBMITTED",
     "the league's own placeholder row: Phoenix has not filed a report for this game as of this release"],
    [D, "09:00", "PHX@DEN", "Denver Nuggets", "Holmes II, DaRon", "Out", "G League - On Assignment", ""],
    [D, "09:00", "PHX@DEN", "Denver Nuggets", "Nembhard, Ryan", "Out", "G League - Two-Way", ""],
    [D, "09:00", "PHX@DEN", "Denver Nuggets", "Strawther, Julian", "Out", "Injury/Illness - Left Knee Sprain", ""],
    [D, "09:00", "PHX@DEN", "Denver Nuggets", "Whitmore, Cam", "Out", "G League - Two-Way",
     "F-V4-05 continuation row: date and time taken from the PHX@DEN block"],
    # ---------------------------------------------------------------- 11/17 filings
    [D17, "07:30", "NYK@TOR", "New York Knicks", "", "", "NOT YET SUBMITTED",
     "the league's own placeholder row: New York has not filed a report for this game as of this release"],
    [D17, "07:30", "NYK@TOR", "Toronto Raptors", "", "", "NOT YET SUBMITTED",
     "the league's own placeholder row: Toronto has not filed a report for this game as of this release"],
    [D17, "08:00", "DET@SAS", "Detroit Pistons", "", "", "NOT YET SUBMITTED",
     "the league's own placeholder row: Detroit has not filed a report for this game as of this release"],
    [D17, "08:00", "DET@SAS", "San Antonio Spurs", "", "", "NOT YET SUBMITTED",
     "the league's own placeholder row: San Antonio has not filed a report for this game as of this release"],
    [D17, "08:00", "POR@MIN", "Portland Trail Blazers", "", "", "NOT YET SUBMITTED",
     "the league's own placeholder row: Portland has not filed a report for this game as of this release"],
    [D17, "08:00", "POR@MIN", "Minnesota Timberwolves", "", "", "NOT YET SUBMITTED",
     "the league's own placeholder row: Minnesota has not filed a report for this game as of this release"],
    [D17, "10:30", "UTA@LAC", "Utah Jazz", "", "", "NOT YET SUBMITTED",
     "the league's own placeholder row: Utah has not filed a report for this game as of this release"],
    [D17, "10:30", "UTA@LAC", "LA Clippers", "", "", "NOT YET SUBMITTED",
     "the league's own placeholder row: the Clippers have not filed a report for this game as of this release"],
    [D17, "11:00", "CHA@LAL", "Charlotte Hornets", "", "", "NOT YET SUBMITTED",
     "the league's own placeholder row: Charlotte has not filed a report for this game as of this release"],
    [D17, "11:00", "CHA@LAL", "Los Angeles Lakers", "", "", "NOT YET SUBMITTED",
     "the league's own placeholder row: the Lakers have not filed a report for this game as of this release"],
]

LAYOUT_NOTES = [
    ("F-V4-05", "Continuation rows in the official PDF lose their date, time, matchup and "
                "sometimes their team cell at a page break. Each such row is keyed off the "
                "block the PDF prints it in, and the reconstruction is written into the row's "
                "note so a reader can see it was reconstructed rather than read."),
    ("F-V4-10", "One GSW@NOP row (Jimmy Butler III) prints no Current Status cell at all in "
                "this release: only the reason is legible. The status is left BLANK and "
                "flagged. It is not back-filled from the club's other rows and it is not "
                "treated as Available."),
    ("F-V4-11", "Five GSW@NOP rows (Curry, Moody, Porzingis, Santos, Williams) print a "
                "legible Current Status but an empty Reason cell, so the reason is left "
                "blank. In the 09:15 AM release the same six rows lost the status column "
                "instead; the status is therefore now readable for five of the six, and the "
                "diff records that change."),
]
