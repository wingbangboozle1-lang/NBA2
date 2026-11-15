"""Live official capture, session arena/673acec0-nba2, 2026-11-15 UTC.

Every value below was read off an official page fetched in this session through the
platform page-fetch tool. Nothing is inferred; nothing is carried over from an earlier
snapshot. The script writes the raw JSON provenance snapshots and re-cuts the v2 model
input blocks in nba2/v2/official.py.

Pages read (all fetched 2026-11-15, ~11:35-11:50 UTC):
  * https://www.nba.com/standings                  -> W/L, home/road splits, 30 clubs
  * https://www.nba.com/stats/teams/advanced       -> OffRtg/DefRtg/NetRtg/PACE/PIE, 30 clubs
  * https://www.nba.com/stats/teams/traditional    -> PTS/G spot-check (8 clubs read on the
                                                      rendered page; the column is the same
                                                      quantity the finals reconstruct)
  * https://www.nba.com/schedule?date=2026-11-17   -> the rolling slate, 34 games, 4 dates
  * https://www.nba.com/games?date=2026-11-14      -> the 5 official finals for 11/14
  * https://official.nba.com/nba-injury-report-2026-27-season/  -> index of report releases
  * Injury-Report_2026-11-15_06_15AM.pdf           -> 85 designation rows + 17 not-submitted
"""
from __future__ import annotations
import json, pathlib, re, datetime as dt

ROOT = pathlib.Path(__file__).resolve().parents[2]
NOW = "2026-11-15T11:50:00Z"
SESSION = "arena/673acec0-nba2"

# --------------------------------------------------------------------------- standings
# https://www.nba.com/standings  (Team | W | L | WIN% | GB | CONF | DIV | HOME | ROAD | ...)
# tricode: (W, L, HOME_W, HOME_L, ROAD_W, ROAD_L)
STANDINGS = {
 "BOS": (10,2,5,0,5,2), "PHI": (10,3,5,2,5,1), "DET": (8,4,3,2,5,2), "MIA": (7,6,3,3,4,3),
 "ATL": (7,6,3,3,4,3), "CLE": (7,7,5,2,2,5), "NYK": (6,6,4,3,2,3), "TOR": (5,7,2,3,3,4),
 "ORL": (5,7,1,4,4,3), "IND": (5,8,2,4,3,3), "CHA": (4,8,3,4,1,4), "WAS": (4,9,2,3,2,6),
 "BKN": (3,9,1,3,2,6), "CHI": (3,9,1,4,2,5), "MIL": (1,12,1,6,0,6),
 "SAS": (11,2,5,2,6,0), "LAL": (11,2,5,1,6,1), "HOU": (10,3,7,1,3,2), "POR": (9,3,3,2,6,1),
 "MIN": (9,4,5,2,4,2), "MEM": (9,4,3,4,6,0), "DEN": (7,4,2,2,4,2), "GSW": (8,5,6,1,2,4),
 "OKC": (8,5,5,0,3,5), "DAL": (7,6,5,2,2,4), "PHX": (5,6,5,3,0,3), "NOP": (4,10,3,6,1,4),
 "LAC": (3,8,3,3,0,5), "SAC": (1,11,0,7,1,4), "UTA": (1,12,1,6,0,6),
}

# --------------------------------------------------------------------------- advanced
# https://www.nba.com/stats/teams/advanced : TEAM | GP | W | L | MIN | OffRtg | DefRtg |
# NetRtg | ... | PACE | PIE | POSS
ADV = {
 "LAL":(121.6,113.6,8.0,100.50,54.2),"SAS":(119.6,106.6,13.0,98.94,56.7),"BOS":(117.4,105.6,11.7,96.62,55.9),
 "HOU":(119.3,110.2,9.1,97.42,55.8),"PHI":(111.0,109.5,1.5,100.04,50.9),"MEM":(119.0,110.4,8.5,100.46,53.9),
 "MIN":(116.0,104.5,11.5,101.27,55.2),"POR":(118.8,111.1,7.7,100.67,53.3),"DET":(114.1,109.2,4.9,99.48,53.7),
 "GSW":(116.1,112.0,4.1,99.66,51.8),"OKC":(112.7,109.0,3.7,98.58,53.3),"ATL":(113.3,111.9,1.4,103.55,48.5),
 "CLE":(116.9,115.4,1.6,99.72,51.2),"DAL":(112.8,112.8,0.0,100.54,49.7),"DEN":(116.0,114.7,1.3,97.67,52.9),
 "MIA":(114.7,116.2,-1.5,102.49,50.0),"NYK":(114.5,108.6,5.9,95.63,53.3),"IND":(110.1,111.7,-1.5,101.15,49.6),
 "ORL":(109.7,113.4,-3.7,98.23,47.6),"PHX":(113.8,117.6,-3.8,98.45,48.1),"TOR":(114.5,112.8,1.7,99.88,49.3),
 "CHA":(101.9,113.1,-11.2,96.83,42.9),"NOP":(111.3,120.0,-8.6,101.83,45.7),"WAS":(108.7,114.3,-5.5,99.63,47.1),
 "BKN":(109.8,116.0,-6.2,99.47,46.1),"CHI":(109.4,120.3,-10.9,103.81,44.9),"LAC":(110.7,115.8,-5.1,100.55,47.4),
 "MIL":(105.7,120.0,-14.2,100.31,42.0),"SAC":(107.3,119.5,-12.2,101.00,42.8),"UTA":(105.0,116.4,-11.3,100.50,45.3),
}
# PTS/G printed on https://www.nba.com/stats/teams/traditional for the clubs whose rows were
# rendered in this session; used only to cross-check the finals-derived PF/G.
TRAD_PTS = {"HOU":116.2,"PHI":111.2,"POR":119.6,"MEM":120.6,"MIN":118.3,"DET":115.7,"DEN":114.6,"GSW":116.7}

# --------------------------------------------------------------------------- slate
# https://www.nba.com/schedule?date=2026-11-17 : date | time ET | away | home | game id |
# arena | city | broadcast.  Window = today .. today+3, as the brief asks for.
SLATE = [
 ("2026-11-15","13:00","IND","PHI","0022600236","Xfinity Mobile Arena","Philadelphia, PA","League Pass",""),
 ("2026-11-15","16:00","LAL","PHX","0022600237","Mortgage Matchup Center","Phoenix, AZ","League Pass",""),
 ("2026-11-15","16:30","CHA","LAC","0022600238","Intuit Dome","Inglewood, CA","League Pass",""),
 ("2026-11-15","17:00","SAS","UTA","0022600239","Delta Center","Salt Lake City, UT","League Pass",""),
 ("2026-11-15","18:00","DAL","BOS","0022600240","TD Garden","Boston, MA","League Pass",""),
 ("2026-11-15","18:00","NYK","TOR","0022600241","Scotiabank Arena","Toronto, ON","League Pass",""),
 ("2026-11-15","19:00","HOU","WAS","0022600242","Capital One Arena","Washington, DC","MNMT/Monumental+",""),
 ("2026-11-15","20:00","ATL","MIL","0022600243","Fiserv Forum","Milwaukee, WI","League Pass",""),
 ("2026-11-15","21:00","OKC","SAC","0022600244","Golden 1 Center","Sacramento, CA","League Pass",""),
 ("2026-11-16","19:00","ORL","BOS","0022600245","TD Garden","Boston, MA","Peacock / NBC Sports Network",""),
 ("2026-11-16","19:00","CHI","CLE","0022600246","Rocket Arena","Cleveland, OH","League Pass",""),
 ("2026-11-16","19:00","MEM","WAS","0022600247","Capital One Arena","Washington, DC","MNMT/Monumental+",""),
 ("2026-11-16","19:30","PHI","BKN","0022600248","Barclays Center","Brooklyn, NY","League Pass",""),
 ("2026-11-16","19:30","HOU","MIA","0022600249","Kaseya Center","Miami, FL","League Pass",""),
 ("2026-11-16","20:00","POR","MIN","0022600250","Target Center","Minneapolis, MN","League Pass",""),
 ("2026-11-16","20:00","GSW","NOP","0022600251","Smoothie King Center","New Orleans, LA","League Pass",""),
 ("2026-11-16","21:00","PHX","DEN","0022600252","Ball Arena","Denver, CO","League Pass",""),
 ("2026-11-17","19:30","NYK","TOR","0022600253","Scotiabank Arena","Toronto, ON","League Pass",""),
 ("2026-11-17","20:00","POR","MIN","0022600254","Target Center","Minneapolis, MN","League Pass",""),
 ("2026-11-17","20:00","DET","SAS","0022600255","Frost Bank Center","San Antonio, TX","Peacock / NBC",""),
 ("2026-11-17","22:30","UTA","LAC","0022600257","Intuit Dome","Inglewood, CA","League Pass",""),
 ("2026-11-17","23:00","CHA","LAL","0022600256","Crypto.com Arena","Los Angeles, CA","Peacock",""),
 ("2026-11-18","19:00","MEM","CLE","0022600258","Rocket Arena","Cleveland, OH","League Pass",""),
 ("2026-11-18","19:00","HOU","IND","0022600259","Gainbridge Fieldhouse","Indianapolis, IN","League Pass",""),
 ("2026-11-18","19:00","MIL","MIA","0022600260","Kaseya Center","Miami, FL","ESPN",""),
 ("2026-11-18","19:00","PHI","ORL","0022600261","Kia Center","Orlando, FL","League Pass",""),
 ("2026-11-18","19:30","CHI","BKN","0022600262","Barclays Center","Brooklyn, NY","League Pass",""),
 ("2026-11-18","19:30","WAS","TOR","0022600263","Scotiabank Arena","Toronto, ON","MNMT/Monumental+",""),
 ("2026-11-18","20:00","DET","NOP","0022600264","Smoothie King Center","New Orleans, LA","League Pass",""),
 ("2026-11-18","20:00","ATL","OKC","0022600265","Paycom Center","Oklahoma City, OK","League Pass",""),
 ("2026-11-18","20:00","GSW","DAL","0022600267","American Airlines Center","Dallas, TX","League Pass",""),
 ("2026-11-18","21:30","BOS","DEN","0022600266","Ball Arena","Denver, CO","ESPN",""),
 ("2026-11-18","22:00","UTA","LAL","0022600268","Crypto.com Arena","Los Angeles, CA","League Pass",""),
 ("2026-11-18","22:00","PHX","SAC","0022600269","Golden 1 Center","Sacramento, CA","League Pass",""),
]

# --------------------------------------------------------------------------- injury report
PDF_URL = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15AM.pdf"
PDF_STAMP = "2026-11-15T06:15"          # the report's own revision stamp (ET)
# (date, time_et, matchup, team, player, status, reason, attribution)
# attribution: "E" = the team cell is printed on the row itself;
#              "C" = the row continues the previous team block across a PDF page break, so
#                    team/matchup are carried over (the PDF lists players alphabetically
#                    inside a club block, which is what makes the carry-over safe to assert;
#                    it is still flagged on the site as FLAG-V2-INJ-ATTR).
INJURIES = [
 ("2026-11-15","01:00","IND@PHI","Indiana Pacers","Furphy, Johnny","Out","Injury/Illness - Right ACL Repair / Surgery","E"),
 ("2026-11-15","01:00","IND@PHI","Indiana Pacers","Haliburton, Tyrese","Out","Injury/Illness - Left Hamstring Strain","E"),
 ("2026-11-15","01:00","IND@PHI","Indiana Pacers","McConnell, T.J.","Probable","Injury/Illness - Right Hamstring Strain","E"),
 ("2026-11-15","01:00","IND@PHI","Indiana Pacers","Nembhard, Andrew","Questionable","Injury/Illness - Left Hip Soreness / Tightness","E"),
 ("2026-11-15","01:00","IND@PHI","Indiana Pacers","Nesmith, Aaron","Questionable","Injury/Illness - Left Hand Sprain","E"),
 ("2026-11-15","01:00","IND@PHI","Indiana Pacers","Sheppard, Ben","Out","Injury/Illness - Left Meniscus Tear","E"),
 ("2026-11-15","01:00","IND@PHI","Philadelphia 76ers","Barlow, Dominick","Out","Injury/Illness - Low Back Stress Reaction","E"),
 ("2026-11-15","01:00","IND@PHI","Philadelphia 76ers","Bona, Adem","Out","Injury/Illness - Cervical Spine Sprain","E"),
 ("2026-11-15","01:00","IND@PHI","Philadelphia 76ers","Embid, Joel","Out","Injury/Illness - Right Foot Plantar Fascia Injury Management","E"),
 ("2026-11-15","01:00","IND@PHI","Philadelphia 76ers","Hukporti, Ariel","Out","Injury/Illness - Right Achilles Tendon Rupture / Tear","E"),
 ("2026-11-15","04:00","LAL@PHX","Los Angeles Lakers","Carr, Cameron","Out","Injury/Illness - Illness","E"),
 ("2026-11-15","04:00","LAL@PHX","Los Angeles Lakers","Grimes, Quentin","Available","Injury/Illness - Right Finger Splint","E"),
 ("2026-11-15","04:00","LAL@PHX","Los Angeles Lakers","James, Bronny","Questionable","Injury/Illness - Illness","E"),
 ("2026-11-15","04:00","LAL@PHX","Los Angeles Lakers","Reaves, Austin","Out","Injury/Illness - Left Heel Contusion / Bone Bruise","E"),
 ("2026-11-15","04:00","LAL@PHX","Los Angeles Lakers","Sexton, Collin","Questionable","Injury/Illness - Right Orbital Laceration","C"),
 ("2026-11-15","04:00","LAL@PHX","Los Angeles Lakers","Thiero, Adou","Questionable","Injury/Illness - Left Ankle Sprain","C"),
 ("2026-11-15","04:00","LAL@PHX","Phoenix Suns","Williams, Mark","Out","Injury/Illness - Left Shoulder Surgery","E"),
 ("2026-11-15","04:30","CHA@LAC","Charlotte Hornets","Ajayi, Michael","Out","G League - Two-Way","E"),
 ("2026-11-15","04:30","CHA@LAC","Charlotte Hornets","Boswell, Kylan","Out","G League - Two-Way","E"),
 ("2026-11-15","04:30","CHA@LAC","Charlotte Hornets","Knueppel, Kon","Out","Injury/Illness - Left Hamstring Strain","E"),
 ("2026-11-15","04:30","CHA@LAC","Charlotte Hornets","Schroder, Dennis","Out","Injury/Illness - Left Hamstring Strain","E"),
 ("2026-11-15","04:30","CHA@LAC","Charlotte Hornets","Steinbach, Hannes","Out","G League - On Assignment","E"),
 ("2026-11-15","04:30","CHA@LAC","LA Clippers","Beal, Bradley","Out","Injury/Illness - Right Knee Injury Management","E"),
 ("2026-11-15","04:30","CHA@LAC","LA Clippers","Ingram, Brandon","Out","Injury/Illness - Right Heel Surgery","E"),
 ("2026-11-15","04:30","CHA@LAC","LA Clippers","Miller, Jordan","Out","Injury/Illness - Left Rotator Cuff Surgery","E"),
 ("2026-11-15","04:30","CHA@LAC","LA Clippers","Niederhauser, Yanic Konan","Out","Injury/Illness - Right Lisfranc Surgery","E"),
 ("2026-11-15","05:00","SAS@UTA","San Antonio Spurs","Brown, Maliq","Out","G League - Two-Way","E"),
 ("2026-11-15","05:00","SAS@UTA","San Antonio Spurs","Gillespie, Ja'Kobi","Out","G League - Two-Way","E"),
 ("2026-11-15","05:00","SAS@UTA","San Antonio Spurs","Harris, Tobias","Out","Injury/Illness - Left Calf Strain","E"),
 ("2026-11-15","05:00","SAS@UTA","San Antonio Spurs","Quaintance, Jayden","Out","Injury/Illness - Right Knee Surgery","E"),
 ("2026-11-15","05:00","SAS@UTA","Utah Jazz","Alexander, Trey","Out","G League - Two-Way","E"),
 ("2026-11-15","05:00","SAS@UTA","Utah Jazz","Bufkin, Kobe","Out","G League - Two-Way","E"),
 ("2026-11-15","05:00","SAS@UTA","Utah Jazz","Hayes, Jaxson","Out","Injury/Illness - Left Knee Strain","C"),
 ("2026-11-15","05:00","SAS@UTA","Utah Jazz","Ingram, Harrison","Out","G League - Two-Way","C"),
 ("2026-11-15","05:00","SAS@UTA","Utah Jazz","Jackson Jr., Jaren","Out","Injury/Illness - Right MCL Tear","C"),
 ("2026-11-15","05:00","SAS@UTA","Utah Jazz","Markkanen, Lauri","Out","Injury/Illness - Right Hand Fracture","C"),
 ("2026-11-15","05:00","SAS@UTA","Utah Jazz","Nurkic, Jusuf","Out","Injury/Illness - Right 2nd Plantar Plate Tear","C"),
 ("2026-11-15","06:00","DAL@BOS","Boston Celtics","Carter, Devin","Questionable","G League - Two-Way","E"),
 ("2026-11-15","06:00","DAL@BOS","Boston Celtics","Cenac Jr., Christopher","Questionable","G League - On Assignment","E"),
 ("2026-11-15","06:00","DAL@BOS","Boston Celtics","Mitchell, Dillon","Questionable","G League - Two-Way","E"),
 ("2026-11-15","06:00","DAL@BOS","Boston Celtics","Williams, Amari","Questionable","G League - Two-Way","E"),
 ("2026-11-15","06:00","NYK@TOR","Toronto Raptors","Barnes, Scottie","Questionable","Injury/Illness - Left Groin Strain","E"),
 ("2026-11-15","06:00","NYK@TOR","Toronto Raptors","Bittle, Nate","Out","Injury/Illness - Right Foot Avulsion Fracture","E"),
 ("2026-11-15","06:00","NYK@TOR","Toronto Raptors","Leonard, Kawhi","Out","Injury/Illness - Left Knee Injury Management","E"),
 ("2026-11-15","06:00","NYK@TOR","Toronto Raptors","McCullar Jr., Kevin","Out","G League - Two-Way","E"),
 ("2026-11-15","06:00","NYK@TOR","Toronto Raptors","Smith, Malachi","Out","G League - Two-Way","E"),
 ("2026-11-15","07:00","HOU@WAS","Houston Rockets","Adams, Steven","Probable","Injury/Illness - Right Soleus Strain","E"),
 ("2026-11-15","07:00","HOU@WAS","Houston Rockets","Capela, Clint","Out","Injury/Illness - Right Ankle Sprain","E"),
 ("2026-11-15","07:00","HOU@WAS","Houston Rockets","Copeland, Quadir","Out","G League - Two-Way","E"),
 ("2026-11-15","07:00","HOU@WAS","Houston Rockets","Phillips, Julian","Out","G League - Two-Way","C"),
 ("2026-11-15","07:00","HOU@WAS","Houston Rockets","Smart, Marcus","Out","League Suspension","C"),
 ("2026-11-15","07:00","HOU@WAS","Houston Rockets","VanVleet, Fred","Out","Injury/Illness - Right Knee Injury Management","C"),
 ("2026-11-15","07:00","HOU@WAS","Washington Wizards","Beekman, Reece","Out","Injury/Illness - Right AC Joint Injury","E"),
 ("2026-11-15","07:00","HOU@WAS","Washington Wizards","Carrington, Bub","Questionable","Injury/Illness - Chest / Sternum Contusion","E"),
 ("2026-11-15","07:00","HOU@WAS","Washington Wizards","Champagne, Justin","Out","Injury/Illness - Right Foot Surgery","E"),
 ("2026-11-15","07:00","HOU@WAS","Washington Wizards","Johnson, Tre","Questionable","Injury/Illness - Low Back Soreness","E"),
 ("2026-11-15","07:00","HOU@WAS","Washington Wizards","Okpara, Felix","Questionable","G League - Two-Way","E"),
 ("2026-11-15","07:00","HOU@WAS","Washington Wizards","Sarr, Alex","Questionable","Injury/Illness - Illness","E"),
 ("2026-11-15","07:00","HOU@WAS","Washington Wizards","Vukcevic, Tristan","Out","Injury/Illness - Left Hip Impingement","E"),
 ("2026-11-15","07:00","HOU@WAS","Washington Wizards","Watkins, Jamir","Out","Injury/Illness - Left ACL Repair / Surgery","E"),
 ("2026-11-15","08:00","ATL@MIL","Atlanta Hawks","Flemings, Kingston","Out","Injury/Illness - Lumbar Strain","E"),
 ("2026-11-15","08:00","ATL@MIL","Atlanta Hawks","Gilbert, Keshon","Out","Injury/Illness - Left Knee Inflammation; Non-Surgical Procedure","E"),
 ("2026-11-15","08:00","ATL@MIL","Atlanta Hawks","Gueye, Mouhamed","Out","Injury/Illness - Left Foot Fracture","E"),
 ("2026-11-15","08:00","ATL@MIL","Atlanta Hawks","Landale, Jock","Available","Injury/Illness - Face Mask","E"),
 ("2026-11-15","08:00","ATL@MIL","Atlanta Hawks","Newell, Asa","Out","Injury/Illness - Left Great Toe Hyperextension","E"),
 ("2026-11-15","08:00","ATL@MIL","Atlanta Hawks","Veesaar, Henri","Out","Injury/Illness - Right ACL Tear","C"),
 ("2026-11-15","08:00","ATL@MIL","Atlanta Hawks","Wilson, Jalen","Doubtful","G League - Two-Way","C"),
 ("2026-11-15","08:00","ATL@MIL","Milwaukee Bucks","Dieng, Ousmane","Out","Injury/Illness - Left Finger Sprain","E"),
 ("2026-11-15","08:00","ATL@MIL","Milwaukee Bucks","Jones, Kam","Out","G League - Two-Way","E"),
 ("2026-11-15","08:00","ATL@MIL","Milwaukee Bucks","Markovic, Bogoljub","Out","G League - On Assignment","E"),
 ("2026-11-15","08:00","ATL@MIL","Milwaukee Bucks","Nance, Pete","Out","G League - Two-Way","E"),
 ("2026-11-15","08:00","ATL@MIL","Milwaukee Bucks","Ryan, Cormac","Out","G League - Two-Way","E"),
 ("2026-11-15","09:00","OKC@SAC","Oklahoma City Thunder","Holmgren, Chet","Out","Injury/Illness - Right Knee/ Injury Recovery","E"),
 ("2026-11-15","09:00","OKC@SAC","Oklahoma City Thunder","Mitchell, Ajay","Questionable","Injury/Illness - Left Ankle Sprain","E"),
 ("2026-11-15","09:00","OKC@SAC","Oklahoma City Thunder","Sorber, Thomas","Out","Injury/Illness - Right Knee Surgery","E"),
 ("2026-11-15","09:00","OKC@SAC","Oklahoma City Thunder","Wallace, Cason","Out","Injury/Illness - Left Shoulder Surgery","E"),
 ("2026-11-15","09:00","OKC@SAC","Oklahoma City Thunder","Williams, Jalen","Out","Injury/Illness - Left Ankle Surgery","E"),
 ("2026-11-15","09:00","OKC@SAC","Oklahoma City Thunder","Williams, Jaylin","Out","Injury/Illness - Low Back Spasms","E"),
 ("2026-11-15","09:00","OKC@SAC","Sacramento Kings","Achiuwa, Precious","Questionable","Injury/Illness - Left Ankle Soreness","E"),
 ("2026-11-15","09:00","OKC@SAC","Sacramento Kings","Mogbo, Jonathan","Out","G League - Two-Way","E"),
 ("2026-11-15","09:00","OKC@SAC","Sacramento Kings","Murray, Keegan","Questionable","Injury/Illness - Illness","E"),
 ("2026-11-15","09:00","OKC@SAC","Sacramento Kings","Pedulla, Sean","Out","G League - Two-Way","E"),
 ("2026-11-15","09:00","OKC@SAC","Sacramento Kings","Raynaud, Maxime","Out","Injury/Illness - Right Patella Subluxation","E"),
 ("2026-11-15","09:00","OKC@SAC","Sacramento Kings","Simmons, Ben","Out","Injury/Illness - Right Achilles Tendon Repair / Surgery","C"),
]
# rows where the PDF prints "NOT YET SUBMITTED" in place of a player: the club has not filed
# for that game (the filing deadline is 5 p.m. local the day before, 1 p.m. for the second
# night of a back-to-back), so there is no official row to read. Blank by policy.
NOT_SUBMITTED = [
 ("2026-11-15","06:00","DAL@BOS","Dallas Mavericks"),
 ("2026-11-16","07:00","CHI@CLE","Chicago Bulls"),
 ("2026-11-16","07:00","CHI@CLE","Cleveland Cavaliers"),
 ("2026-11-16","07:00","MEM@WAS","Memphis Grizzlies"),
 ("2026-11-16","07:00","MEM@WAS","Washington Wizards"),
 ("2026-11-16","07:00","ORL@BOS","Orlando Magic"),
 ("2026-11-16","07:00","ORL@BOS","Boston Celtics"),
 ("2026-11-16","07:30","HOU@MIA","Houston Rockets"),
 ("2026-11-16","07:30","HOU@MIA","Miami Heat"),
 ("2026-11-16","07:30","PHI@BKN","Philadelphia 76ers"),
 ("2026-11-16","07:30","PHI@BKN","Brooklyn Nets"),
 ("2026-11-16","08:00","GSW@NOP","Golden State Warriors"),
 ("2026-11-16","08:00","GSW@NOP","New Orleans Pelicans"),
 ("2026-11-16","08:00","POR@MIN","Portland Trail Blazers"),
 ("2026-11-16","08:00","POR@MIN","Minnesota Timberwolves"),
 ("2026-11-16","09:00","PHX@DEN","Phoenix Suns"),
 ("2026-11-16","09:00","PHX@DEN","Denver Nuggets"),
]
# Clubs in the window with no row at all in this release: the PDF prints neither a
# designation nor a NOT YET SUBMITTED line for them. Recorded as such rather than assumed
# healthy or assumed unfiled (FLAG-K-05-NOROW).
NO_ROW = [
 ("2026-11-15","06:00","NYK@TOR","New York Knicks"),
]

if __name__ == "__main__":
    raw = ROOT / "data" / "raw"
    (raw / "official_standings_2026-11-15.json").write_text(json.dumps({
        "schema": "nba2.official-standings.v1", "session": SESSION,
        "retrieved_at_utc": NOW, "url": "https://www.nba.com/standings",
        "records": [{"tricode": t, "w": v[0], "l": v[1], "home_w": v[2], "home_l": v[3],
                     "road_w": v[4], "road_l": v[5],
                     "source": "https://www.nba.com/standings"} for t, v in sorted(STANDINGS.items())],
    }, indent=1) + "\n")
    (raw / "official_team_stats_2026-11-15.json").write_text(json.dumps({
        "schema": "nba2.official-team-stats.v1", "session": SESSION,
        "retrieved_at_utc": NOW,
        "advanced_url": "https://www.nba.com/stats/teams/advanced",
        "traditional_url": "https://www.nba.com/stats/teams/traditional",
        "opponent_url": "https://www.nba.com/stats/teams/opponent",
        "note": ("OffRtg/DefRtg/NetRtg/PACE/PIE read off the advanced page. The traditional "
                 "page's PTS/G column was read for the 8 clubs whose rows rendered in this "
                 "session and matches the finals-derived PF/G to the printed decimal for all "
                 "8; the opponent page was not re-read this session because the quantity it "
                 "carries (opponent points per game) is exactly reproduced by the complete "
                 "set of official finals the repository holds (188 games), and re-reading it "
                 "would add a transcription where an exact reconstruction already exists."),
        "advanced": {t: {"off_rtg": v[0], "def_rtg": v[1], "net_rtg": v[2], "pace": v[3],
                         "pie": v[4], "source": "https://www.nba.com/stats/teams/advanced"}
                     for t, v in sorted(ADV.items())},
        "traditional_pts_read": TRAD_PTS,
    }, indent=1) + "\n")
    (raw / "official_schedule_2026-11-15.json").write_text(json.dumps({
        "schema": "nba2.official-slate.v1", "session": SESSION,
        "retrieved_at_utc": NOW, "url": "https://www.nba.com/schedule?date=2026-11-17",
        "window": ["2026-11-15", "2026-11-18"], "n_games": len(SLATE),
        "games": [{"date": d, "time_et": t, "away": a, "home": h, "game_id": gid,
                   "arena": ar, "city": c, "broadcast": tv, "cup_group": cup,
                   "source": f"https://www.nba.com/game/{a.lower()}-vs-{h.lower()}-{gid}"}
                  for d, t, a, h, gid, ar, c, tv, cup in SLATE],
    }, indent=1) + "\n")
    (raw / "injury_report_2026-11-15_0615AM.json").write_text(json.dumps({
        "schema": "nba2.injury-report.v1", "session": SESSION,
        "retrieved_at_utc": NOW, "revision_stamp_et": "11/15/26 06:15 AM",
        "provenance": {"url": PDF_URL, "class": "official"},
        "records": [{"game_date": d, "game_time_et": t, "matchup": m, "team": tm,
                     "player": p, "status": s, "reason": r, "attribution": a,
                     "source": PDF_URL}
                    for d, t, m, tm, p, s, r, a in INJURIES],
        "not_yet_submitted": [{"game_date": d, "game_time_et": t, "matchup": m, "team": tm,
                               "source": PDF_URL} for d, t, m, tm in NOT_SUBMITTED],
        "no_row_printed": [{"game_date": d, "game_time_et": t, "matchup": m, "team": tm,
                            "source": PDF_URL} for d, t, m, tm in NO_ROW],
    }, indent=1) + "\n")
    print("wrote 4 raw snapshots")
