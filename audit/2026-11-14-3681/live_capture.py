"""Transcription of official NBA pages fetched live by session arena/3681def8-nba2.

Every value in this module was read off an official NBA document retrieved in this
session (2026-11-14 ~10:20-10:35 UTC) through the platform page-fetch tool. Direct
HTTP egress from the sandbox to nba.com is blocked (curl -> HTTP 000), so each block
below records the method as well as the URL and the retrieval time.

Nothing here is inferred, interpolated, or carried over from another session's file.
Where the official document does not state a value, the field is absent, not guessed.
"""

RETRIEVED_UTC = "2026-11-14T10:25:00Z"
METHOD = "platform page-fetch tool (direct curl from the sandbox returns HTTP 000 for all nba.com hosts)"

# ---------------------------------------------------------------------------
# 1. Final scores, 2026-11-13 slate (9 games)
# Source: https://www.nba.com/schedule?date=2026-11-14  (Week 4 grid, Nov 9-15)
#         retrieved 2026-11-14 ~10:20 UTC. Every game card shows "Final" plus the
#         two team scores. One game (ATL@CHI) is labelled "Final/OT".
#         Each game's own page is the per-row source link.
# ---------------------------------------------------------------------------
SCHEDULE_URL = "https://www.nba.com/schedule?date=2026-11-14"

# game_id, date, away, home, away_pts, home_pts, periods, cup_group, arena, city, state
FINALS_2026_11_13 = [
    ("0022600034", "2026-11-13", "NYK", "IND", 104, 106, 4, "East Group B", "Gainbridge Fieldhouse", "Indianapolis", "IN"),
    ("0022600035", "2026-11-13", "MIL", "ORL",  99, 107, 4, "East Group A", "Kia Center",             "Orlando",      "FL"),
    ("0022600036", "2026-11-13", "CLE", "MIA", 121, 133, 4, "East Group B", "Kaseya Center",          "Miami",        "FL"),
    ("0022600037", "2026-11-13", "ATL", "CHI", 117, 125, 5, "East Group C", "United Center",          "Chicago",      "IL"),  # Final/OT
    ("0022600038", "2026-11-13", "MEM", "NOP", 142, 111, 4, "West Group B", "Smoothie King Center",   "New Orleans",  "LA"),
    ("0022600039", "2026-11-13", "UTA", "HOU", 118, 125, 4, "West Group A", "Toyota Center",          "Houston",      "TX"),
    ("0022600040", "2026-11-13", "GSW", "SAS",  85, 123, 4, "West Group C", "Frost Bank Center",      "San Antonio",  "TX"),
    ("0022600041", "2026-11-13", "POR", "SAC", 120, 107, 4, "West Group C", "Golden 1 Center",        "Sacramento",   "CA"),
    ("0022600042", "2026-11-13", "OKC", "LAC", 112, 113, 4, "West Group B", "Intuit Dome",            "Inglewood",    "CA"),
]

# ---------------------------------------------------------------------------
# 2. Upcoming slate 2026-11-14 .. 2026-11-17 (27 games) - live re-verification
# Source: https://www.nba.com/schedule?date=2026-11-14 (Week 4 + Week 5 grids)
#         retrieved 2026-11-14 ~10:20-10:28 UTC.
#         Per-date game counts printed on the page: 11/14 "5 Games", 11/15 "9 Games",
#         11/16 "8 Games", 11/17 "5 Games".
# ---------------------------------------------------------------------------
# game_id, date, time_et, away, home, arena, city, state, broadcast
SLATE_2026_11_14_TO_17 = [
    ("0022600231", "2026-11-14", "19:00", "DEN", "NOP", "Smoothie King Center", "New Orleans",  "LA", "League Pass"),
    ("0022600232", "2026-11-14", "19:30", "DAL", "CLE", "Rocket Arena",          "Cleveland",    "OH", "League Pass"),
    ("0022600233", "2026-11-14", "20:00", "DET", "MIA", "Kaseya Center",         "Miami",        "FL", "NBA TV"),
    ("0022600234", "2026-11-14", "20:00", "BKN", "MEM", "FedExForum",            "Memphis",      "TN", "League Pass"),
    ("0022600235", "2026-11-14", "20:00", "CHI", "MIN", "Target Center",         "Minneapolis",  "MN", "League Pass"),
    ("0022600236", "2026-11-15", "13:00", "IND", "PHI", "Xfinity Mobile Arena",  "Philadelphia", "PA", "League Pass"),
    ("0022600237", "2026-11-15", "16:00", "LAL", "PHX", "Mortgage Matchup Center", "Phoenix",    "AZ", "League Pass"),
    ("0022600238", "2026-11-15", "16:30", "CHA", "LAC", "Intuit Dome",           "Inglewood",    "CA", "League Pass"),
    ("0022600239", "2026-11-15", "17:00", "SAS", "UTA", "Delta Center",          "Salt Lake City", "UT", "League Pass"),
    ("0022600240", "2026-11-15", "18:00", "DAL", "BOS", "TD Garden",             "Boston",       "MA", "League Pass"),
    ("0022600241", "2026-11-15", "18:00", "NYK", "TOR", "Scotiabank Arena",      "Toronto",      "ON", "League Pass"),
    ("0022600242", "2026-11-15", "19:00", "HOU", "WAS", "Capital One Arena",     "Washington",   "DC", "MNMT / Monumental+"),
    ("0022600243", "2026-11-15", "20:00", "ATL", "MIL", "Fiserv Forum",          "Milwaukee",    "WI", "League Pass"),
    ("0022600244", "2026-11-15", "21:00", "OKC", "SAC", "Golden 1 Center",       "Sacramento",   "CA", "League Pass"),
    ("0022600245", "2026-11-16", "19:00", "ORL", "BOS", "TD Garden",             "Boston",       "MA", "Peacock / NBC Sports Network"),
    ("0022600246", "2026-11-16", "19:00", "CHI", "CLE", "Rocket Arena",          "Cleveland",    "OH", "League Pass"),
    ("0022600247", "2026-11-16", "19:00", "MEM", "WAS", "Capital One Arena",     "Washington",   "DC", "MNMT / Monumental+"),
    ("0022600248", "2026-11-16", "19:30", "PHI", "BKN", "Barclays Center",       "Brooklyn",     "NY", "League Pass"),
    ("0022600249", "2026-11-16", "19:30", "HOU", "MIA", "Kaseya Center",         "Miami",        "FL", "League Pass"),
    ("0022600250", "2026-11-16", "20:00", "POR", "MIN", "Target Center",         "Minneapolis",  "MN", "League Pass"),
    ("0022600251", "2026-11-16", "20:00", "GSW", "NOP", "Smoothie King Center",  "New Orleans",  "LA", "League Pass"),
    ("0022600252", "2026-11-16", "21:00", "PHX", "DEN", "Ball Arena",            "Denver",       "CO", "League Pass"),
    ("0022600253", "2026-11-17", "19:30", "NYK", "TOR", "Scotiabank Arena",      "Toronto",      "ON", "League Pass"),
    ("0022600254", "2026-11-17", "20:00", "POR", "MIN", "Target Center",         "Minneapolis",  "MN", "League Pass"),
    ("0022600255", "2026-11-17", "20:00", "DET", "SAS", "Frost Bank Center",     "San Antonio",  "TX", "Peacock / NBC"),
    ("0022600257", "2026-11-17", "22:30", "UTA", "LAC", "Intuit Dome",           "Inglewood",    "CA", "League Pass"),
    ("0022600256", "2026-11-17", "23:00", "CHA", "LAL", "Crypto.com Arena",      "Los Angeles",  "CA", "Peacock"),
]

# ---------------------------------------------------------------------------
# 3. Official injury report - 2026-11-14 05:00 AM ET release
# Source: https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_05_00AM.pdf
#         retrieved 2026-11-14 ~10:29 UTC. Index page listing this file:
#         https://official.nba.com/nba-injury-report-2026-27-season/
#         The PDF's own header reads "Injury Report: 11/14/26 05:00 AM".
#         Times in the PDF's "Game Time" column are 12-hour ET without a meridiem
#         (e.g. DEN@NOP "07:00 (ET)" is the 7:00 PM ET tip printed on the schedule);
#         the 11/15 rows ("01:00", "04:00", ...) match the schedule's PM tips.
# ---------------------------------------------------------------------------
INJURY_PDF_URL = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_05_00AM.pdf"
INJURY_INDEX_URL = "https://official.nba.com/nba-injury-report-2026-27-season/"

# date, time_et, matchup, team, player (None = club submitted no designation), status, reason
INJURY_2026_11_14_0500AM = [
    ("2026-11-14", "07:00", "DEN@NOP", "Denver Nuggets",        "Holmes II, DaRon",    "Out",          "G League - On Assignment"),
    ("2026-11-14", "07:00", "DEN@NOP", "Denver Nuggets",        "Nembhard, Ryan",      "Out",          "G League - Two-Way"),
    ("2026-11-14", "07:00", "DEN@NOP", "Denver Nuggets",        "Strawther, Julian",   "Out",          "Injury/Illness - Left Knee Sprain"),
    ("2026-11-14", "07:00", "DEN@NOP", "Denver Nuggets",        "Whitmore, Cam",       "Out",          "G League - Two-Way"),
    ("2026-11-14", "07:00", "DEN@NOP", "New Orleans Pelicans",  None,                  None,           "NOT YET SUBMITTED"),
    ("2026-11-14", "07:30", "DAL@CLE", "Dallas Mavericks",      "Biberovic, Tarik",    "Out",          "Injury/Illness - Right Heel Bursitis"),
    ("2026-11-14", "07:30", "DAL@CLE", "Dallas Mavericks",      "Christie, Max",       "Questionable", "Injury/Illness - Left Ankle Sprain"),
    ("2026-11-14", "07:30", "DAL@CLE", "Dallas Mavericks",      "de Larrea, Sergio",   "Out",          "Injury/Illness - Right Knee Sprain"),
    ("2026-11-14", "07:30", "DAL@CLE", "Dallas Mavericks",      "Johnson Jr., Morez",  "Probable",     "Injury/Illness - Left Shin / Tibia Contusion"),
    ("2026-11-14", "07:30", "DAL@CLE", "Dallas Mavericks",      "Lively II, Dereck",   "Out",          "Injury/Illness - Right Foot Surgery"),
    ("2026-11-14", "07:30", "DAL@CLE", "Dallas Mavericks",      "Martin, Caleb",       "Available",    "Injury/Illness - Right Thumb Splint"),
    ("2026-11-14", "07:30", "DAL@CLE", "Cleveland Cavaliers",   None,                  None,           "NOT YET SUBMITTED"),
    ("2026-11-14", "08:00", "BKN@MEM", "Brooklyn Nets",         "Bilodeau, Tyler",     "Out",          "G League - Two-Way"),
    ("2026-11-14", "08:00", "BKN@MEM", "Brooklyn Nets",         "Brown Jr., Mikel",    "Questionable", "Injury/Illness - Illness"),
    ("2026-11-14", "08:00", "BKN@MEM", "Brooklyn Nets",         "Jefferson, Joshua",   "Out",          "G League - On Assignment"),
    ("2026-11-14", "08:00", "BKN@MEM", "Brooklyn Nets",         "Nelson, Grant",       "Out",          "G League - Two-Way"),
    ("2026-11-14", "08:00", "BKN@MEM", "Brooklyn Nets",         "Saraf, Ben",          "Out",          "G League - On Assignment"),
    ("2026-11-14", "08:00", "BKN@MEM", "Brooklyn Nets",         "Traore, Nolan",       "Probable",     "Injury/Illness - Right Calf Tightness / Soreness"),
    ("2026-11-14", "08:00", "BKN@MEM", "Memphis Grizzlies",     None,                  None,           "NOT YET SUBMITTED"),
    ("2026-11-14", "08:00", "CHI@MIN", "Chicago Bulls",         None,                  None,           "NOT YET SUBMITTED"),
    ("2026-11-14", "08:00", "CHI@MIN", "Minnesota Timberwolves","Beringer, Joan",      "Available",    "Injury/Illness - Face Mask"),
    ("2026-11-14", "08:00", "CHI@MIN", "Minnesota Timberwolves","DiVincenzo, Donte",   "Out",          "Injury/Illness - Right Achilles Tendon Repair / Surgery"),
    ("2026-11-14", "08:00", "CHI@MIN", "Minnesota Timberwolves","Edwards, Anthony",    "Out",          "Injury/Illness - Right Knee Arthroscopy"),
    ("2026-11-14", "08:00", "DET@MIA", "Detroit Pistons",       "Duren, Jalen",        "Out",          "Injury/Illness - Right Hamstring Strain"),
    ("2026-11-14", "08:00", "DET@MIA", "Detroit Pistons",       "Harkless, Elijah",    "Questionable", "G League - Two-Way"),
    ("2026-11-14", "08:00", "DET@MIA", "Detroit Pistons",       "Joe, Isaiah",         "Out",          "Injury/Illness - Right Hip Contusion"),
    ("2026-11-14", "08:00", "DET@MIA", "Detroit Pistons",       "Jones, Isaac",        "Questionable", "G League - Two-Way"),
    ("2026-11-14", "08:00", "DET@MIA", "Detroit Pistons",       "Lanier, Chaz",        "Out",          "G League - On Assignment"),
    ("2026-11-14", "08:00", "DET@MIA", "Detroit Pistons",       "Okorie, Ebuka",       "Out",          "G League - On Assignment"),
    ("2026-11-14", "08:00", "DET@MIA", "Detroit Pistons",       "Onyenso, Ugonna",     "Out",          "G League - Two-Way"),
    ("2026-11-14", "08:00", "DET@MIA", "Miami Heat",            None,                  None,           "NOT YET SUBMITTED"),
]
# 11/15 rows: every club on the 11/15 slate had filed nothing at 05:00 AM ET on 11/14.
INJURY_2026_11_15_NOT_SUBMITTED = [
    ("2026-11-15", "01:00", "IND@PHI", "Indiana Pacers"),
    ("2026-11-15", "01:00", "IND@PHI", "Philadelphia 76ers"),
    ("2026-11-15", "04:00", "LAL@PHX", "Los Angeles Lakers"),
    ("2026-11-15", "04:00", "LAL@PHX", "Phoenix Suns"),
    ("2026-11-15", "04:30", "CHA@LAC", "Charlotte Hornets"),
    ("2026-11-15", "04:30", "CHA@LAC", "LA Clippers"),
    ("2026-11-15", "05:00", "SAS@UTA", "San Antonio Spurs"),
    ("2026-11-15", "05:00", "SAS@UTA", "Utah Jazz"),
    ("2026-11-15", "06:00", "DAL@BOS", "Dallas Mavericks"),
    ("2026-11-15", "06:00", "DAL@BOS", "Boston Celtics"),
    ("2026-11-15", "06:00", "NYK@TOR", "New York Knicks"),
    ("2026-11-15", "06:00", "NYK@TOR", "Toronto Raptors"),
    ("2026-11-15", "07:00", "HOU@WAS", "Houston Rockets"),
    ("2026-11-15", "07:00", "HOU@WAS", "Washington Wizards"),
    ("2026-11-15", "08:00", "ATL@MIL", "Atlanta Hawks"),
    ("2026-11-15", "08:00", "ATL@MIL", "Milwaukee Bucks"),
    ("2026-11-15", "09:00", "OKC@SAC", "Oklahoma City Thunder"),
    ("2026-11-15", "09:00", "OKC@SAC", "Sacramento Kings"),
]

# ---------------------------------------------------------------------------
# 4. Official standings (NBA.com) as of the morning of 2026-11-14 - i.e. including
#    the completed 2026-11-13 games. This is the first OFFICIAL win-loss capture in
#    the repository; every prior ratings snapshot used a third-party source for W-L.
# Source: https://www.nba.com/standings  retrieved 2026-11-14 ~10:29 UTC,
#         "NBA 2026-27 Regular Season Standings", Group By Conference.
#         Columns read: W, L, WIN%, GB, CONF, DIV, HOME, ROAD, Neutral, OT, LAST10, STREAK
# ---------------------------------------------------------------------------
STANDINGS_URL = "https://www.nba.com/standings"

# tricode, conference, rank, w, l, win_pct, gb, conf, div, home, road, neutral, ot, last10, streak
STANDINGS_2026_11_14 = [
    ("BOS", "East",  1, 10,  2, ".833", "--",  "10-1", "4-0", "5-0", "5-2", "0-0", "1-0", "9-1",  "W 5"),
    ("PHI", "East",  2, 10,  3, ".769", "0.5", "10-3", "3-1", "5-2", "5-1", "0-0", "0-0", "7-3",  "W 1"),
    ("DET", "East",  3,  8,  3, ".727", "1.5", "8-2",  "0-0", "3-2", "5-1", "0-0", "1-0", "7-3",  "W 2"),
    ("ATL", "East",  4,  7,  6, ".538", "3.5", "7-2",  "4-1", "3-3", "4-3", "0-0", "0-1", "5-5",  "L 2"),
    ("MIA", "East",  5,  6,  6, ".500", "4",   "3-2",  "1-1", "2-3", "4-3", "0-0", "1-0", "6-4",  "W 3"),
    ("NYK", "East",  6,  6,  6, ".500", "4",   "6-6",  "1-3", "4-3", "2-3", "0-0", "0-0", "6-4",  "L 2"),
    ("CLE", "East",  7,  6,  7, ".462", "4.5", "5-5",  "1-0", "4-2", "2-5", "0-0", "1-0", "4-6",  "L 1"),
    ("TOR", "East",  8,  5,  7, ".417", "5",   "4-3",  "0-2", "2-3", "3-4", "0-0", "0-0", "3-7",  "L 3"),
    ("ORL", "East",  9,  5,  7, ".417", "5",   "3-4",  "0-2", "1-4", "4-3", "0-0", "0-1", "5-5",  "W 3"),
    ("IND", "East", 10,  5,  8, ".385", "5.5", "3-5",  "0-1", "2-4", "3-3", "0-1", "0-0", "3-7",  "W 2"),
    ("CHA", "East", 11,  4,  8, ".333", "6",   "4-7",  "2-2", "3-4", "1-4", "0-0", "0-0", "3-7",  "L 1"),
    ("WAS", "East", 12,  4,  9, ".308", "6.5", "4-8",  "2-3", "2-3", "2-6", "0-0", "0-1", "2-8",  "L 6"),
    ("BKN", "East", 13,  3,  8, ".273", "6.5", "2-7",  "0-2", "1-3", "2-5", "0-0", "0-1", "3-7",  "W 1"),
    ("CHI", "East", 14,  2,  9, ".182", "7.5", "2-8",  "1-0", "1-4", "1-5", "0-0", "1-0", "2-8",  "W 1"),
    ("MIL", "East", 15,  1, 12, ".077", "9.5", "1-9",  "1-2", "1-6", "0-6", "0-0", "0-0", "1-9",  "L 9"),
    ("SAS", "West",  1, 11,  2, ".846", "--",  "10-2", "2-1", "5-2", "6-0", "0-0", "1-0", "10-0", "W 11"),
    ("LAL", "West",  2, 11,  2, ".846", "--",  "6-2",  "4-1", "5-1", "6-1", "0-0", "0-0", "8-2",  "W 7"),
    ("HOU", "West",  3, 10,  3, ".769", "1",   "6-3",  "2-1", "7-1", "3-2", "0-0", "0-0", "7-3",  "W 3"),
    ("POR", "West",  4,  9,  3, ".750", "1.5", "9-3",  "4-0", "3-2", "6-1", "0-0", "0-0", "7-3",  "W 3"),
    ("MIN", "West",  5,  9,  3, ".750", "1.5", "5-2",  "1-0", "5-1", "4-2", "0-0", "0-1", "7-3",  "W 5"),
    ("MEM", "West",  6,  8,  4, ".667", "2.5", "7-3",  "1-1", "2-4", "6-0", "0-0", "0-1", "6-4",  "W 1"),
    ("GSW", "West",  7,  8,  5, ".615", "3",   "6-5",  "3-2", "6-1", "2-4", "0-0", "1-0", "8-2",  "L 2"),
    ("OKC", "West",  8,  8,  5, ".615", "3",   "5-5",  "1-2", "5-0", "3-5", "0-0", "0-0", "5-5",  "L 3"),
    ("DEN", "West",  9,  6,  4, ".600", "3.5", "4-4",  "0-2", "2-2", "3-2", "1-0", "1-0", "6-4",  "W 1"),
    ("DAL", "West", 10,  7,  5, ".583", "3.5", "3-5",  "1-3", "5-2", "2-3", "0-0", "0-0", "6-4",  "L 1"),
    ("PHX", "West", 11,  5,  6, ".455", "5",   "3-6",  "2-1", "5-3", "0-3", "0-0", "0-0", "5-5",  "W 2"),
    ("NOP", "West", 12,  4,  9, ".308", "7",   "3-7",  "1-1", "3-5", "1-4", "0-0", "2-1", "4-6",  "L 5"),
    ("LAC", "West", 13,  3,  8, ".273", "7",   "3-6",  "1-4", "3-3", "0-5", "0-0", "0-1", "2-8",  "W 1"),
    ("SAC", "West", 14,  1, 11, ".083", "9.5", "1-9",  "0-2", "0-7", "1-4", "0-0", "0-0", "1-9",  "L 5"),
    ("UTA", "West", 15,  1, 12, ".077", "10",  "1-10", "0-2", "1-6", "0-6", "0-0", "0-2", "0-10", "L 11"),
]

# ---------------------------------------------------------------------------
# 5. Filing-cadence rules quoted verbatim from the official index page
#    https://official.nba.com/nba-injury-report-2026-27-season/  (retrieved 10:29 UTC)
# ---------------------------------------------------------------------------
FILING_RULES_VERBATIM = [
    "By 5 p.m. local time the day before a game (other than the second day of a back-to-back), teams must designate a participation status and identify a specific injury, illness, other medical condition, or other reason for any player whose participation in the game may be affected for any reason.",
    "For the second game of a back-to-back, teams must report the above information by 1 p.m. local time on the day of the game.",
    "In addition, teams are required to submit a game-day injury report between 11 a.m. and 1 p.m. local time (and between 8 and 10 a.m. for tip-offs 5 p.m. or earlier) on game days (besides the second game of a back-to-back).",
    "Reports are updated on a continual basis throughout the day.",
]
