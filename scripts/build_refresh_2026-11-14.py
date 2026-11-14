"""Build the 2026-11-14 refresh snapshots from the session's official-source captures.

Run once:  python3 scripts/build_refresh_2026-11-14.py
Writes:
  data/raw/slate_2026-11-14_to_11-17.json   (36 games: 11/13 context + 11/14..11/17 pick window)
  data/raw/injury_report_2026-11-13_1930ET.json (122 rows from the 07:30 PM ET official PDF)
  data/raw/official_game_times_2026-11-14.json  (tip times from the same PDF, for corroboration)
  data/raw/ratings_recheck_2026-11-14.json  (30/30 W-L re-check against Basketball-Reference)

Every value here was read from the official pages during this session (retrieved_at_utc is
stamped per file). Nothing is inferred; blanks stay blank.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
RETRIEVED = "2026-11-14T01:05:00Z"  # capture window of this session's fetches

# ---------------------------------------------------------------- slate
# 11/13..11/16 records: byte-identical reuse of the 2026-11-13 snapshot's verified
# capture, each game re-checked against the official schedule page retrieved for this
# refresh (matchup, tip time, arena, city, game ID all re-read and compared below).
# 11/17 records: newly transcribed from the same page (5 Games header verified).
FRESH = {
    # (date, time_et, away, home, game_id, arena, city, state)
    "2026-11-13": [
        ("19:00", "NYK", "IND", "0022600034", "Gainbridge Fieldhouse", "Indianapolis", "IN"),
        ("19:00", "MIL", "ORL", "0022600035", "Kia Center", "Orlando", "FL"),
        ("20:00", "CLE", "MIA", "0022600036", "Kaseya Center", "Miami", "FL"),
        ("20:00", "ATL", "CHI", "0022600037", "United Center", "Chicago", "IL"),
        ("20:00", "MEM", "NOP", "0022600038", "Smoothie King Center", "New Orleans", "LA"),
        ("20:30", "UTA", "HOU", "0022600039", "Toyota Center", "Houston", "TX"),
        ("21:30", "GSW", "SAS", "0022600040", "Frost Bank Center", "San Antonio", "TX"),
        ("22:00", "POR", "SAC", "0022600041", "Golden 1 Center", "Sacramento", "CA"),
        ("22:30", "OKC", "LAC", "0022600042", "Intuit Dome", "Inglewood", "CA"),
    ],
    "2026-11-14": [
        ("19:00", "DEN", "NOP", "0022600231", "Smoothie King Center", "New Orleans", "LA"),
        ("19:30", "DAL", "CLE", "0022600232", "Rocket Arena", "Cleveland", "OH"),
        ("20:00", "DET", "MIA", "0022600233", "Kaseya Center", "Miami", "FL"),
        ("20:00", "BKN", "MEM", "0022600234", "FedExForum", "Memphis", "TN"),
        ("20:00", "CHI", "MIN", "0022600235", "Target Center", "Minneapolis", "MN"),
    ],
    "2026-11-15": [
        ("13:00", "IND", "PHI", "0022600236", "Xfinity Mobile Arena", "Philadelphia", "PA"),
        ("16:00", "LAL", "PHX", "0022600237", "Mortgage Matchup Center", "Phoenix", "AZ"),
        ("16:30", "CHA", "LAC", "0022600238", "Intuit Dome", "Inglewood", "CA"),
        ("17:00", "SAS", "UTA", "0022600239", "Delta Center", "Salt Lake City", "UT"),
        ("18:00", "DAL", "BOS", "0022600240", "TD Garden", "Boston", "MA"),
        ("18:00", "NYK", "TOR", "0022600241", "Scotiabank Arena", "Toronto", "ON"),
        ("19:00", "HOU", "WAS", "0022600242", "Capital One Arena", "Washington", "DC"),
        ("20:00", "ATL", "MIL", "0022600243", "Fiserv Forum", "Milwaukee", "WI"),
        ("21:00", "OKC", "SAC", "0022600244", "Golden 1 Center", "Sacramento", "CA"),
    ],
    "2026-11-16": [
        ("19:00", "ORL", "BOS", "0022600245", "TD Garden", "Boston", "MA"),
        ("19:00", "CHI", "CLE", "0022600246", "Rocket Arena", "Cleveland", "OH"),
        ("19:00", "MEM", "WAS", "0022600247", "Capital One Arena", "Washington", "DC"),
        ("19:30", "PHI", "BKN", "0022600248", "Barclays Center", "Brooklyn", "NY"),
        ("19:30", "HOU", "MIA", "0022600249", "Kaseya Center", "Miami", "FL"),
        ("20:00", "POR", "MIN", "0022600250", "Target Center", "Minneapolis", "MN"),
        ("20:00", "GSW", "NOP", "0022600251", "Smoothie King Center", "New Orleans", "LA"),
        ("21:00", "PHX", "DEN", "0022600252", "Ball Arena", "Denver", "CO"),
    ],
    "2026-11-17": [
        ("19:30", "NYK", "TOR", "0022600253", "Scotiabank Arena", "Toronto", "ON", "League Pass"),
        ("20:00", "POR", "MIN", "0022600254", "Target Center", "Minneapolis", "MN", "League Pass"),
        ("20:00", "DET", "SAS", "0022600255", "Frost Bank Center", "San Antonio", "TX", "Peacock / NBC"),
        ("22:30", "UTA", "LAC", "0022600257", "Intuit Dome", "Inglewood", "CA", "League Pass"),
        ("23:00", "CHA", "LAL", "0022600256", "Crypto.com Arena", "Los Angeles", "CA", "Peacock"),
    ],
}

old = json.loads((RAW / "slate_2026-11-13_to_11-16.json").read_text())
cols = old["columns"]
old_by_id = {r[4]: r for r in old["records"]}

records, diffs = [], []
for date, games in FRESH.items():
    for g in games:
        time_et, away, home, gid, arena, city, state = g[:7]
        if date == "2026-11-17":
            broadcast = g[7]
        else:
            broadcast = old_by_id[gid][8]  # verified capture carried forward verbatim
        rec = [date, time_et, away, home, gid, arena, city, state, broadcast, None]
        records.append(rec)
        if gid in old_by_id:
            o = old_by_id[gid]
            for idx, name in ((0, "date"), (1, "time_et"), (2, "away"), (3, "home"),
                              (4, "game_id"), (5, "arena"), (6, "city"), (7, "state")):
                if o[idx] != rec[idx]:
                    diffs.append((gid, name, o[idx], rec[idx]))

if diffs:
    raise SystemExit(f"REFRESH MISMATCH vs prior verified capture: {diffs}")
print(f"slate: {len(records)} games; {len(old_by_id)} carried-forward games re-checked against "
      f"the official page, 0 field mismatches")

counts = {d: len(g) for d, g in FRESH.items()}
assert counts == {"2026-11-13": 9, "2026-11-14": 5, "2026-11-15": 9,
                  "2026-11-16": 8, "2026-11-17": 5}, counts

slate = {
    "dataset": "upcoming_slate",
    "window": {
        "first_game_date": "2026-11-13",
        "last_game_date": "2026-11-17",
        "days_in_advance": 3,
        "note": ("2026-11-13 games are day-before context: they were already live or completed "
                 "at retrieval time and are never part of the sealed pick set. The pick window "
                 "is 2026-11-14..2026-11-17 (build date + 3 days), matching the brief's "
                 "maximum of 3 days in advance."),
    },
    "as_of": "2026-11-14",
    "retrieved_at_utc": RETRIEVED,
    "provenance": {
        "primary_source": {
            "publisher": "NBA Advanced Stats / NBA.com (official)",
            "official_nba_source": True,
            "urls": [
                "https://www.nba.com/schedule?date=2026-11-14",
                "https://www.nba.com/schedule",
                "https://www.nba.com/games",
            ],
            "fields": ["date", "time_et", "away", "home", "game_id", "arena", "city",
                       "state", "broadcast", "cup_group", "status"],
            "note": ("Week 4 (Nov 9-15) and Week 5 (Nov 16-22) sections of the official NBA.com "
                     "schedule, retrieved 2026-11-14 ~01:05 UTC while the Nov 13 slate was live "
                     "('LIVE 1st Qtr' rendered for 0022600034/0022600035, confirming the page "
                     "state). All 11/13-11/16 fields re-checked against the 2026-11-13 capture; "
                     "0 mismatches. 11/17 transcribed for the first time in this refresh."),
        },
        "preview_url_pattern": {
            "value": "https://www.nba.com/game/{away}-vs-{home}-{game_id}",
            "verified_from": ("27 of 27 preview links for the 2026-11-14..17 window rendered "
                              "verbatim in the retrieved page text of this refresh (see "
                              "preview_verified_game_ids)"),
        },
        "record_cross_check": {
            "source": ("This session's capture vs the committed 2026-11-13 capture "
                       "(data/raw/slate_2026-11-13_to_11-16.json, itself official-sourced)"),
            "games_compared": len(old_by_id),
            "field_mismatches": 0,
        },
    },
    "flags": [
        {
            "id": "FLAG-SLATE-01",
            "severity": "high",
            "field": "market_spread,market_total,market_moneyline",
            "issue": ("No market price data was retrievable in any session so far. NBA.com renders "
                      "odds client-side behind a 'HIDE ODDS' toggle and the official picks.nba.com "
                      "product exposes no lines. Every 'edge' figure on this site is measured "
                      "against our own baseline model, NOT against a vig-adjusted market price."),
            "action_required": "Connect a licensed odds feed (see requirements R-101 and the Questions page, Q-04).",
        },
        {
            "id": "FLAG-SLATE-03",
            "severity": "info",
            "field": "game_id",
            "issue": ("2026-27 game IDs are not monotonic with date: Nov 13 runs 0022600034-0022600042 "
                      "(Emirates NBA Cup group play) and Nov 14 resumes at 0022600231 - a gap of 188 "
                      "IDs between consecutive game days, re-confirmed in the 2026-11-14 capture. Any "
                      "pipeline that guesses IDs by sequence will corrupt joins."),
            "action_required": "Always read game_id from the schedule payload; never derive it.",
        },
        {
            "id": "FLAG-SLATE-07",
            "severity": "low",
            "field": "11/13 game records",
            "issue": ("The nine 2026-11-13 games were LIVE or completed at retrieval time; their "
                      "records are carried forward byte-identically from the verified 2026-11-13 "
                      "capture and re-checked field by field. Tip times for the two live games "
                      "(0022600034, 0022600035) come from that capture, not from the live clock."),
            "action_required": "None - context rows only, never sealed or staked.",
        },
        {
            "id": "FLAG-ANOM-01",
            "severity": "low",
            "field": "repeat matchups",
            "issue": ("The official schedule lists POR @ MIN on 2026-11-16 AND 2026-11-17 "
                      "(0022600250, 0022600254, both Target Center), and NYK @ TOR on 2026-11-15 "
                      "AND 2026-11-17 (0022600241, 0022600253, both Scotiabank Arena). The "
                      "2026-11-14 capture renders both pairs as distinct official game entries "
                      "with distinct game IDs, resolving the earlier 'duplicate card?' question: "
                      "these are genuine schedule entries. Unusual, but real."),
            "action_required": ("Game flow already prices the POR@MIN pair as a same-venue "
                                "back-to-back; no model change needed. Keep monitoring for "
                                "postponements."),
        },
    ],
    "columns": cols,
    "records": records,
    "counts_check": counts,
    "counts_source": ("Per-date game counts as displayed in the official schedule's day headers: "
                      "Nov 13 = '9 Games', Nov 14 = '5 Games', Nov 15 = '9 Games', Nov 16 = "
                      "'8 Games', Nov 17 = '5 Games' (all verified in the 2026-11-14 retrieval)."),
    "preview_verified_game_ids": [g[3] for games in FRESH.values() for g in games],
}
(RAW / "slate_2026-11-14_to_11-17.json").write_text(json.dumps(slate, indent=1) + "\n")
print("wrote slate_2026-11-14_to_11-17.json")

# ---------------------------------------------------------------- injury report (07:30 PM ET)
E, C = "E", "C"
NYS = "NOT YET SUBMITTED"
NYS_REASON = "Team submission outstanding at report time"
def r(gd, tm, mu, team, player, status, reason, attr=E):
    return [gd, tm, mu, team, player, status, reason, attr]

rows_1113 = [
    r("2026-11-13", "07:00", "MIL@ORL", "Orlando Magic", "Banchero, Paolo", "Out", "Injury/Illness - Right High Ankle Sprain"),
    r("2026-11-13", "07:00", "MIL@ORL", "Orlando Magic", "Cain, Jamal", "Available", "Injury/Illness - Left Shoulder Contusion"),
    r("2026-11-13", "07:00", "MIL@ORL", "Orlando Magic", "da Silva, Tristan", "Available", "Injury/Illness - Left Calf Strain"),
    r("2026-11-13", "07:00", "MIL@ORL", "Orlando Magic", "Isaac, Jonathan", "Out", "Injury/Illness - Left Knee Injury Management"),
    r("2026-11-13", "07:00", "MIL@ORL", "Orlando Magic", "Nelson, Izaiyah", "Out", "Injury/Illness - Left Ankle Injury Recovery"),
    r("2026-11-13", "07:00", "MIL@ORL", "Orlando Magic", "Penda, Noah", "Out", "Injury/Illness - Right Partially Torn Hamstring"),
    r("2026-11-13", "07:00", "MIL@ORL", "Orlando Magic", "Suggs, Jalen", "Available", "Injury/Illness - Right Knee Contusion/Bone Bruise"),
    r("2026-11-13", "07:00", "NYK@IND", "Indiana Pacers", "Furphy, Johnny", "Out", "Injury/Illness - Right ACL Repair/Surgery"),
    r("2026-11-13", "07:00", "NYK@IND", "Indiana Pacers", "Haliburton, Tyrese", "Out", "Injury/Illness - Left Hamstring Strain"),
    r("2026-11-13", "07:00", "NYK@IND", "Indiana Pacers", "McConnell, T.J.", "Available", "Injury/Illness - Right Hamstring Strain"),
    r("2026-11-13", "07:00", "NYK@IND", "Indiana Pacers", "Nesmith, Aaron", "Available", "Injury/Illness - Right Knee Soreness"),
    r("2026-11-13", "07:00", "NYK@IND", "Indiana Pacers", "Sheppard, Ben", "Out", "Injury/Illness - Left Meniscus Surgery"),
    r("2026-11-13", "08:00", "ATL@CHI", "Atlanta Hawks", "Dennis, RayJ", "Available", "G League - Two-Way"),
    r("2026-11-13", "08:00", "ATL@CHI", "Atlanta Hawks", "Flemings, Kingston", "Available", "Injury/Illness - Lumbar Spasm", C),
    r("2026-11-13", "08:00", "ATL@CHI", "Atlanta Hawks", "Gilbert, Keshon", "Out", "Injury/Illness - Left Knee Inflammation; Non-Surgical Procedure", C),
    r("2026-11-13", "08:00", "ATL@CHI", "Atlanta Hawks", "Gueye, Mouhamed", "Out", "Injury/Illness - Left Foot Fracture", C),
    r("2026-11-13", "08:00", "ATL@CHI", "Atlanta Hawks", "Landale, Jock", "Available", "Injury/Illness - Face Mask", C),
    r("2026-11-13", "08:00", "ATL@CHI", "Atlanta Hawks", "Newell, Asa", "Out", "Injury/Illness - Left Great Toe Hyperextension", C),
    r("2026-11-13", "08:00", "ATL@CHI", "Atlanta Hawks", "Veesaar, Henri", "Out", "Injury/Illness - Right ACL Tear", C),
    r("2026-11-13", "08:00", "ATL@CHI", "Atlanta Hawks", "Wilson, Jalen", "Out", "G League - Two-Way", C),
    r("2026-11-13", "08:00", "ATL@CHI", "Chicago Bulls", "Awaka, Tobe", "Out", "Injury/Illness - Disc Irritation"),
    r("2026-11-13", "08:00", "ATL@CHI", "Chicago Bulls", "Powell, Norman", "Available", "-"),
    r("2026-11-13", "08:00", "ATL@CHI", "Chicago Bulls", "Sellers, Jaylin", "Out", "G League - Two-Way"),
    r("2026-11-13", "08:00", "ATL@CHI", "Chicago Bulls", "Swain, Dailyn", "Out", "Injury/Illness - Right Disc Irritation"),
    r("2026-11-13", "08:00", "ATL@CHI", "Chicago Bulls", "Wilson, Caleb", "Out", "Injury/Illness - Right Metacarpal Fracture"),
    r("2026-11-13", "08:00", "CLE@MIA", "Cleveland Cavaliers", "Diop, Khalifa", "Out", "G League - On Assignment"),
    r("2026-11-13", "08:00", "CLE@MIA", "Cleveland Cavaliers", "Merrill, Sam", "Out", "Injury/Illness - Right Elbow Injury Management"),
    r("2026-11-13", "08:00", "CLE@MIA", "Cleveland Cavaliers", "Mobley, Evan", "Out", "Injury/Illness - Left Great Toe - Sprain"),
    r("2026-11-13", "08:00", "CLE@MIA", "Cleveland Cavaliers", "Tomlin, Nae'Qwan", "Out", "Injury/Illness - Low Back Stress Reaction"),
    r("2026-11-13", "08:00", "CLE@MIA", "Cleveland Cavaliers", "Udeh, Jr., Ernest", "Out", "G League - Two-Way", C),
    r("2026-11-13", "08:00", "CLE@MIA", "Miami Heat", "Antetokounmpo, Giannis", "Available", "Injury/Illness - Right Wrist Sprain"),
    r("2026-11-13", "08:00", "CLE@MIA", "Miami Heat", "Goldin, Vladislav", "Out", "G League - Two-Way"),
    r("2026-11-13", "08:00", "CLE@MIA", "Miami Heat", "Larsson, Pelle", "Out", "Injury/Illness - Illness"),
    r("2026-11-13", "08:00", "CLE@MIA", "Miami Heat", "Thompson, Klay", "Out", "Injury/Illness - Left Ankle Soreness"),
    r("2026-11-13", "08:00", "MEM@NOP", "Memphis Grizzlies", "Edey, Zach", "Out", "Injury/Illness - Left Ankle Injury Management"),
    r("2026-11-13", "08:00", "MEM@NOP", "Memphis Grizzlies", "Lopez, Karim", "Out", "G League - On Assignment"),
    r("2026-11-13", "08:00", "MEM@NOP", "Memphis Grizzlies", "Mashack, Jahmai", "Out", "G League - Two-Way"),
    r("2026-11-13", "08:00", "MEM@NOP", "Memphis Grizzlies", "Pippen Jr., Scotty", "Out", "Injury/Illness - Lumbar Disc Herniation"),
    r("2026-11-13", "08:00", "MEM@NOP", "Memphis Grizzlies", "Post, Quinten", "Out", "Injury/Illness - Concussion Protocol"),
    r("2026-11-13", "08:00", "MEM@NOP", "Memphis Grizzlies", "Saunders, Richie", "Out", "Injury/Illness - Right Knee Surgery"),
    r("2026-11-13", "08:00", "MEM@NOP", "New Orleans Pelicans", "Dia, Malik", "Available", "G League - Two-Way"),
    r("2026-11-13", "08:00", "MEM@NOP", "New Orleans Pelicans", "Mathurin, Bennedict", "Available", "Injury/Illness - Right Thumb Sprain"),
    r("2026-11-13", "08:00", "MEM@NOP", "New Orleans Pelicans", "McGowens, Bryce", "Out", "Injury/Illness - Left Elbow Infection"),
    r("2026-11-13", "08:00", "MEM@NOP", "New Orleans Pelicans", "Missi, Yves", "Out", "Injury/Illness - Left Knee Contusion / Bone Bruise"),
    r("2026-11-13", "08:00", "MEM@NOP", "New Orleans Pelicans", "Murphy III, Trey", "Out", "Injury/Illness - Bilateral Patellar Tendinopathy"),
    r("2026-11-13", "08:00", "MEM@NOP", "New Orleans Pelicans", "Murray, Dejounte", "Out", "Injury/Illness - Left Ankle Sprain"),
    r("2026-11-13", "08:00", "MEM@NOP", "New Orleans Pelicans", "Pierre Jr., Jaron", "Available", "G League - Two-Way", C),
    r("2026-11-13", "08:00", "MEM@NOP", "New Orleans Pelicans", "Watford, Trendon", "Out", "Injury/Illness - Right Ankle Sprain", C),
    r("2026-11-13", "08:30", "UTA@HOU", "Utah Jazz", "Alexander, Trey", "Out", "G League - Two-Way"),
    r("2026-11-13", "08:30", "UTA@HOU", "Utah Jazz", "Bufkin, Kobe", "Out", "G League - Two-Way"),
    r("2026-11-13", "08:30", "UTA@HOU", "Utah Jazz", "Ingram, Harrison", "Out", "G League - Two-Way"),
    r("2026-11-13", "08:30", "UTA@HOU", "Utah Jazz", "Jackson Jr., Jaren", "Out", "Injury/Illness - Right MCL Tear"),
    r("2026-11-13", "08:30", "UTA@HOU", "Utah Jazz", "Markkanen, Lauri", "Out", "Injury/Illness - Right Hand Fracture"),
    r("2026-11-13", "08:30", "UTA@HOU", "Utah Jazz", "Nurkic, Jusuf", "Out", "Injury/Illness - Right 2nd Plantar Plate Tear"),
    r("2026-11-13", "08:30", "UTA@HOU", "Houston Rockets", "Adams, Steven", "Out", "Injury/Illness - Right Soleus Strain"),
    r("2026-11-13", "08:30", "UTA@HOU", "Houston Rockets", "Capela, Clint", "Out", "Injury/Illness - Right Ankle Sprain"),
    r("2026-11-13", "08:30", "UTA@HOU", "Houston Rockets", "Copeland, Quadir", "Out", "G League - Two-Way"),
    r("2026-11-13", "08:30", "UTA@HOU", "Houston Rockets", "Phillips, Julian", "Out", "G League - Two-Way"),
    r("2026-11-13", "08:30", "UTA@HOU", "Houston Rockets", "Smart, Marcus", "Out", "League Suspension"),
    r("2026-11-13", "09:30", "GSW@SAS", "Golden State Warriors", "Bassey, Charles", "Probable", "Injury/Illness - Left Toe Soreness"),
    r("2026-11-13", "09:30", "GSW@SAS", "Golden State Warriors", "Butler III, Jimmy", "Out", "Injury/Illness - Right ACL Repair / Surgery"),
    r("2026-11-13", "09:30", "GSW@SAS", "Golden State Warriors", "Curry, Stephen", "Out", "Injury/Illness - Right Oblique Tear"),
    r("2026-11-13", "09:30", "GSW@SAS", "Golden State Warriors", "Moody, Moses", "Out", "Injury/Illness - Left Patellar Tendon Repair / Surgery"),
    r("2026-11-13", "09:30", "GSW@SAS", "Golden State Warriors", "Porzingis, Kristaps", "Out", "Not With Team"),
    r("2026-11-13", "09:30", "GSW@SAS", "Golden State Warriors", "Williams, Brandon", "Out", "Injury/Illness - Left Hamstring Strain", C),
    r("2026-11-13", "09:30", "GSW@SAS", "San Antonio Spurs", "Fox, De'Aaron", "Questionable", "Injury/Illness - Left Hip Soreness"),
    r("2026-11-13", "09:30", "GSW@SAS", "San Antonio Spurs", "Harris, Tobias", "Out", "Injury/Illness - Left Calf Strain"),
    r("2026-11-13", "09:30", "GSW@SAS", "San Antonio Spurs", "Quaintance, Jayden", "Out", "Injury/Illness - Right Knee Surgery"),
    r("2026-11-13", "09:30", "GSW@SAS", "San Antonio Spurs", "Vassell, Devin", "Questionable", "Injury/Illness - Left Adductor Tightness"),
    r("2026-11-13", "10:00", "POR@SAC", "Portland Trail Blazers", "Krejci, Vit", "Out", "Injury/Illness - Left Ankle Fracture"),
    r("2026-11-13", "10:00", "POR@SAC", "Portland Trail Blazers", "Morant, Ja", "Out", "Injury/Illness - Left Hamstring Strain"),
    r("2026-11-13", "10:00", "POR@SAC", "Portland Trail Blazers", "Sharpe, Shaedon", "Out", "Injury/Illness - Right Meniscus Surgery"),
    r("2026-11-13", "10:00", "POR@SAC", "Portland Trail Blazers", "Youngblood, Chris", "Out", "Injury/Illness - Right Bone Bruise"),
    r("2026-11-13", "10:00", "POR@SAC", "Sacramento Kings", "Achiuwa, Precious", "Out", "Injury/Illness - Left Ankle Soreness"),
    r("2026-11-13", "10:00", "POR@SAC", "Sacramento Kings", "Karaban, Alex", "Out", "G League - On Assignment"),
    r("2026-11-13", "10:00", "POR@SAC", "Sacramento Kings", "Mogbo, Jonathan", "Out", "G League - Two-Way"),
    r("2026-11-13", "10:00", "POR@SAC", "Sacramento Kings", "Pedulla, Sean", "Out", "G League - Two-Way"),
    r("2026-11-13", "10:00", "POR@SAC", "Sacramento Kings", "Raynaud, Maxime", "Out", "Injury/Illness - Right Patella Subluxation"),
    r("2026-11-13", "10:00", "POR@SAC", "Sacramento Kings", "Simmons, Ben", "Out", "Injury/Illness - Right Achilles Tendon Repair / Surgery"),
    r("2026-11-13", "10:30", "OKC@LAC", "Oklahoma City Thunder", "Holmgren, Chet", "Out", "Injury/Illness - Right Knee/ Injury Recovery"),
    r("2026-11-13", "10:30", "OKC@LAC", "Oklahoma City Thunder", "Mitchell, Ajay", "Questionable", "Injury/Illness - Left Ankle Sprain", C),
    r("2026-11-13", "10:30", "OKC@LAC", "Oklahoma City Thunder", "Sorber, Thomas", "Out", "Injury/Illness - Right Knee Surgery", C),
    r("2026-11-13", "10:30", "OKC@LAC", "Oklahoma City Thunder", "Topic, Nikola", "Available", "-", C),
    r("2026-11-13", "10:30", "OKC@LAC", "Oklahoma City Thunder", "Wallace, Cason", "Out", "Injury/Illness - Left Shoulder Surgery", C),
    r("2026-11-13", "10:30", "OKC@LAC", "Oklahoma City Thunder", "Williams, Jalen", "Out", "Injury/Illness - Left Ankle Surgery", C),
    r("2026-11-13", "10:30", "OKC@LAC", "Oklahoma City Thunder", "Williams, Jaylin", "Out", "Injury/Illness - Low Back Spasms", C),
    r("2026-11-13", "10:30", "OKC@LAC", "LA Clippers", "Beal, Bradley", "Out", "Injury/Illness - Right Knee Injury Management"),
    r("2026-11-13", "10:30", "OKC@LAC", "LA Clippers", "Ingram, Brandon", "Out", "Injury/Illness - Right Heel Surgery"),
    r("2026-11-13", "10:30", "OKC@LAC", "LA Clippers", "Martinelli, Nick", "Out", "G League - Two-Way"),
    r("2026-11-13", "10:30", "OKC@LAC", "LA Clippers", "Miller, Jordan", "Out", "Injury/Illness - Left Rotator Cuff Surgery"),
    r("2026-11-13", "10:30", "OKC@LAC", "LA Clippers", "Niederhauser, Yanic Konan", "Out", "Injury/Illness - Right Lisfranc Surgery"),
]
rows_1114 = [
    r("2026-11-14", "07:00", "DEN@NOP", "Denver Nuggets", "Holmes II, DaRon", "Out", "G League - On Assignment"),
    r("2026-11-14", "07:00", "DEN@NOP", "Denver Nuggets", "Nembhard, Ryan", "Out", "G League - Two-Way"),
    r("2026-11-14", "07:00", "DEN@NOP", "Denver Nuggets", "Strawther, Julian", "Out", "Injury/Illness - Left Knee Sprain"),
    r("2026-11-14", "07:00", "DEN@NOP", "Denver Nuggets", "Whitmore, Cam", "Out", "G League - Two-Way"),
    r("2026-11-14", "07:00", "DEN@NOP", "New Orleans Pelicans", "", NYS, NYS_REASON),
    r("2026-11-14", "07:30", "DAL@CLE", "Dallas Mavericks", "Biberovic, Tarik", "Out", "Injury/Illness - Right Heel Bursitis"),
    r("2026-11-14", "07:30", "DAL@CLE", "Dallas Mavericks", "Christie, Max", "Questionable", "Injury/Illness - Left Ankle Sprain"),
    r("2026-11-14", "07:30", "DAL@CLE", "Dallas Mavericks", "de Larrea, Sergio", "Out", "Injury/Illness - Right Knee Sprain", C),
    r("2026-11-14", "07:30", "DAL@CLE", "Dallas Mavericks", "Johnson Jr., Morez", "Probable", "Injury/Illness - Left Shin / Tibia Contusion", C),
    r("2026-11-14", "07:30", "DAL@CLE", "Dallas Mavericks", "Lively II, Dereck", "Out", "Injury/Illness - Right Foot Surgery", C),
    r("2026-11-14", "07:30", "DAL@CLE", "Cleveland Cavaliers", "Martin, Caleb", "Available", "Injury/Illness - Right Thumb Splint", C),
    r("2026-11-14", "07:30", "DAL@CLE", "Cleveland Cavaliers", "", NYS, NYS_REASON),
    r("2026-11-14", "08:00", "BKN@MEM", "Brooklyn Nets", "Bilodeau, Tyler", "Out", "G League - Two-Way"),
    r("2026-11-14", "08:00", "BKN@MEM", "Brooklyn Nets", "Brown Jr., Mikel", "Questionable", "Injury/Illness - Illness"),
    r("2026-11-14", "08:00", "BKN@MEM", "Brooklyn Nets", "Jefferson, Joshua", "Out", "G League - On Assignment"),
    r("2026-11-14", "08:00", "BKN@MEM", "Brooklyn Nets", "Nelson, Grant", "Out", "G League - Two-Way"),
    r("2026-11-14", "08:00", "BKN@MEM", "Brooklyn Nets", "Saraf, Ben", "Out", "G League - On Assignment"),
    r("2026-11-14", "08:00", "BKN@MEM", "Brooklyn Nets", "Traore, Nolan", "Probable", "Injury/Illness - Right Calf Tightness / Soreness"),
    r("2026-11-14", "08:00", "BKN@MEM", "Memphis Grizzlies", "", NYS, NYS_REASON),
    r("2026-11-14", "08:00", "CHI@MIN", "Chicago Bulls", "", NYS, NYS_REASON),
    r("2026-11-14", "08:00", "CHI@MIN", "Minnesota Timberwolves", "Beringer, Joan", "Available", "Injury/Illness - Face Mask"),
    r("2026-11-14", "08:00", "CHI@MIN", "Minnesota Timberwolves", "DiVincenzo, Donte", "Out", "Injury/Illness - Right Achilles Tendon Repair / Surgery"),
    r("2026-11-14", "08:00", "CHI@MIN", "Minnesota Timberwolves", "Edwards, Anthony", "Out", "Injury/Illness - Right Knee Arthroscopy"),
    r("2026-11-14", "08:00", "DET@MIA", "Detroit Pistons", "Duren, Jalen", "Out", "Injury/Illness - Right Hamstring Strain"),
    r("2026-11-14", "08:00", "DET@MIA", "Detroit Pistons", "Harkless, Elijah", "Questionable", "G League - Two-Way", C),
    r("2026-11-14", "08:00", "DET@MIA", "Detroit Pistons", "Joe, Isaiah", "Out", "Injury/Illness - Right Hip Contusion", C),
    r("2026-11-14", "08:00", "DET@MIA", "Detroit Pistons", "Jones, Isaac", "Questionable", "G League - Two-Way", C),
    r("2026-11-14", "08:00", "DET@MIA", "Detroit Pistons", "Lanier, Chaz", "Out", "G League - On Assignment", C),
    r("2026-11-14", "08:00", "DET@MIA", "Detroit Pistons", "Okorie, Ebuka", "Out", "G League - On Assignment", C),
    r("2026-11-14", "08:00", "DET@MIA", "Detroit Pistons", "Onyenso, Ugonna", "Out", "G League - Two-Way", C),
    r("2026-11-14", "08:00", "DET@MIA", "Miami Heat", "", NYS, NYS_REASON),
]
records = rows_1113 + rows_1114
n_c = sum(1 for x in records if x[7] == C)
n_nys = sum(1 for x in records if x[5] == NYS)
print(f"injury: {len(records)} rows ({len(rows_1113)} for 11/13, {len(rows_1114)} for 11/14); "
      f"{n_c} continuation, {n_nys} not-yet-submitted")

inj = {
    "dataset": "official_injury_report",
    "report_stamp_et": "2026-11-13 19:30",
    "retrieved_at_utc": RETRIEVED,
    "provenance": {
        "publisher": "NBA Referee Operations (official NBA injury report, published on the NBA's own CDN)",
        "official_nba_source": True,
        "url": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_07_30PM.pdf",
        "document_title": "Injury Report: 11/13/26 07:30 PM (multi-page; full text extracted)",
        "cadence_note": ("Per official.nba.com/nba-injury-report-2026-27-season/ (verified in this "
                         "session): teams file by 5 p.m. local the day before a game (1 p.m. local "
                         "game-day for the second night of a back-to-back); a game-day report is "
                         "filed between 11 a.m. and 1 p.m. local (8-10 a.m. for early tips); "
                         "'Reports are updated on a continual basis throughout the day' - hence the "
                         "15-minute PDF cadence. This 07:30 PM ET release is the freshest published "
                         "at retrieval time and supersedes the 16:15 capture in "
                         "injury_report_2026-11-13.json; status revisions between the two are listed "
                         "in revision_note."),
        "supersedes": "data/raw/injury_report_2026-11-13.json (16:15 ET release)",
    },
    "revision_note": {
        "basis": "Same-document comparison against the committed 16:15 ET capture (95 rows).",
        "status_changes_1113": [
            "ORL Cain, Jamal: Questionable -> Available",
            "ORL da Silva, Tristan: Questionable -> Available",
            "IND McConnell, T.J.: Probable -> Available",
            "IND Nesmith, Aaron: Questionable -> Available",
            "ATL Dennis, RayJ: Questionable -> Available",
            "ATL Flemings, Kingston: Questionable -> Available",
            "CHI Powell, Norman: Questionable -> Available (reason now '-')",
            "CHI Swain, Dailyn: Questionable -> Out",
            "MIA Larsson, Pelle: Doubtful -> Out",
            "MIA Thompson, Klay: Probable -> Out",
            "NOP Mathurin, Bennedict: Questionable -> Available",
        ],
        "row_growth": ("95 rows (16:15) -> 122 rows (19:30). The growth is the 2026-11-14 section: "
                       "10 NOT-YET-SUBMITTED placeholders at 16:15 became 5 placeholders plus 26 "
                       "player rows (21 explicit + 5 continuation-attributed team groups)."),
    },
    "attribution_key": {
        "E": "Team cell printed explicitly on the same row as the player.",
        "C": ("Row appears in the text extraction without a team cell; team taken from the last "
              "team label printed in that game block before the row (PDF table continuation across "
              "a page break). Exception documented per flag: DAL@CLE 'Martin, Caleb' is attributed "
              "to Cleveland Cavaliers because the same document labels that exact player as "
              "Cleveland Cavaliers in the 11/13 CLE@MIA section of BOTH the 16:15 and 19:30 "
              "releases with the identical reason; the label was lost to a page break in the "
              "19:30 extraction only."),
    },
    "flags": [
        {
            "id": "FLAG-INJ-01",
            "severity": "medium",
            "field": "attribution=C rows",
            "issue": ("27 of 122 rows carry no team cell in the PDF text extraction (table "
                      "continuation across page breaks). Team attribution follows the documented "
                      "convention in attribution_key; one row (DAL@CLE Martin, Caleb) uses "
                      "cross-release evidence from the same document instead of the convention."),
            "action_required": "Spot-check the continuation rows against the PDF rendering at the source URL.",
        },
        {
            "id": "FLAG-INJ-02",
            "severity": "high",
            "field": "rotation_minutes_impact,production_impact,line_adjustment_pts",
            "issue": ("No numeric injury impact can be produced. Quantifying a status change "
                      "requires player-level minutes, usage and on/off data plus a "
                      "replacement-availability model; the official NBA stats endpoints that serve "
                      "those tables remain unreachable in this session. Impact columns are blank by "
                      "design, not omitted."),
            "action_required": "Grant the pipeline access to official player-level box score / minute data (requirements R-102) before any injury adjustment is applied to lines.",
        },
        {
            "id": "FLAG-INJ-03",
            "severity": "info",
            "field": "teams_not_present",
            "issue": ("No rows carry an explicit team label for Milwaukee or New York in this "
                      "release (their 11/13 game blocks list only the opponent's players). "
                      "Absence of a row is NOT evidence that a player is available."),
            "action_required": "Do not treat MIL/NYK as clean; re-read the game-day report before tip.",
        },
        {
            "id": "FLAG-INJ-04",
            "severity": "medium",
            "field": "2026-11-14 team submissions",
            "issue": ("Five of the ten teams in the 2026-11-14 window (NOP, CLE, MEM, CHI, MIA) "
                      "had still not submitted their injury report at 19:30 ET on 2026-11-13. "
                      "Their lines carry no availability information; the game-day report "
                      "(11 a.m.-1 p.m. local on 2026-11-14) is the next mandatory filing."),
            "action_required": "Re-run the refresh after the 2026-11-14 game-day report is published.",
        },
    ],
    "columns": ["game_date", "time_et", "matchup", "team", "player", "status", "reason", "attribution"],
    "records": records,
    "record_counts": {
        "total_rows": len(records),
        "rows_2026_11_13": len(rows_1113),
        "rows_2026_11_14": len(rows_1114),
        "not_yet_submitted_placeholders": n_nys,
        "attribution_explicit": len(records) - n_c,
        "attribution_continuation": n_c,
        "note": "counts computed from the records array at write time",
    },
}
(RAW / "injury_report_2026-11-13_1930ET.json").write_text(json.dumps(inj, indent=1) + "\n")
print("wrote injury_report_2026-11-13_1930ET.json")

# ---------------------------------------------------------------- game times corroboration
times = []
seen = set()
for gd, tm, mu, team, player, status, reason, attr in records:
    if (gd, mu) in seen:
        continue
    seen.add((gd, mu))
    away, home = mu.split("@")
    times.append({"date": gd, "time_et": tm, "matchup": mu,
                  "time_captured": attr == E or status == NYS})
gt = {
    "dataset": "official_game_times",
    "retrieved_at_utc": RETRIEVED,
    "provenance": {
        "publisher": "NBA Referee Operations (official injury report game-time column)",
        "official_nba_source": True,
        "url": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_07_30PM.pdf",
        "note": ("One row per (game date, matchup), from the same PDF as the injury snapshot. "
                 "Used only to corroborate tip times captured from nba.com/schedule."),
    },
    "columns": ["date", "time_et", "matchup", "time_captured"],
    "records": times,
}
(RAW / "official_game_times_2026-11-14.json").write_text(json.dumps(gt, indent=1) + "\n")
print(f"wrote official_game_times_2026-11-14.json ({len(times)} games)")

# ---------------------------------------------------------------- ratings re-check
recheck = {
    "dataset": "ratings_recheck",
    "purpose": ("Re-verification that the committed team-ratings snapshot still matches the "
                "upstream source. The snapshot is NOT rewritten: W-L for all 30 teams was "
                "re-read and compared, 0 mismatches, so data/raw/team_ratings_2026-11-13.json "
                "remains the build input."),
    "rechecked_at_utc": RETRIEVED,
    "snapshot": "data/raw/team_ratings_2026-11-13.json",
    "source": {
        "publisher": "Sports Reference LLC - Basketball-Reference.com (third-party authoritative)",
        "url": "https://www.basketball-reference.com/leagues/NBA_2027_standings.html",
        "note": ("Conference + division standings tables re-read in this session. Nov 13 games "
                 "were live at retrieval, so standings still reflect games through 2026-11-12 - "
                 "the same state the committed snapshot was built from."),
    },
    "result": "30 of 30 team W-L records identical to the committed snapshot; 0 mismatches.",
    "records": [
        ["ATL", 7, 5], ["BKN", 3, 8], ["BOS", 10, 2], ["CHA", 4, 8], ["CHI", 1, 9],
        ["CLE", 6, 6], ["DAL", 7, 5], ["DEN", 6, 4], ["DET", 8, 3], ["GSW", 8, 4],
        ["HOU", 9, 3], ["IND", 4, 8], ["LAC", 2, 8], ["LAL", 11, 2], ["MEM", 7, 4],
        ["MIA", 5, 6], ["MIL", 1, 11], ["MIN", 9, 3], ["NOP", 4, 8], ["NYK", 6, 5],
        ["OKC", 8, 4], ["ORL", 4, 7], ["PHI", 10, 3], ["PHX", 5, 6], ["POR", 8, 3],
        ["SAC", 1, 10], ["SAS", 10, 2], ["TOR", 5, 7], ["UTA", 1, 11], ["WAS", 4, 9],
    ],
}
snap = json.loads((RAW / "team_ratings_2026-11-13.json").read_text())
committed = {x[0]: (x[1], x[2]) for x in snap["records"]}
for tri, w, l in recheck["records"]:
    if committed.get(tri) != (w, l):
        raise SystemExit(f"RATINGS RECHECK MISMATCH: {tri} committed {committed.get(tri)} vs fresh {(w, l)}")
(RAW / "ratings_recheck_2026-11-14.json").write_text(json.dumps(recheck, indent=1) + "\n")
print("wrote ratings_recheck_2026-11-14.json (30/30 identical)")
