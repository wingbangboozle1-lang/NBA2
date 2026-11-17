"""Official injury releases, stored **verbatim** as the page-fetch tool rendered them.

Why this module exists
----------------------
The previous v4 build stored a *transcription* of one release: 70 hand-normalised rows
written into ``capture.py``. That is a lossy, interpretive step sitting between the official
PDF and the published table, and it introduced two defects that a reviewer can see:

* **A real status was dropped.** The 09:15 AM transcription records
  ``Tyson, Jaylon | Questionable`` for Cleveland. The 09:30 AM PDF prints **Doubtful** for
  the same player. A transcription that renders both as the same word cannot detect the
  change, and a diff built on it reports "0 changes" with confidence.
* **An artefact was mistaken for evidence.** Six GSW@NOP rows keep only player + reason
  because the status column does not survive text conversion. Those were stored as blank
  and flagged F-V4-06, which is honest — but the underlying reading problem is the
  transcription, not the PDF.

So the raw rendering is now the stored artefact, and every row-level value in the published
diff is derived **by code** from this text (``injury_diff.parse_render``). Nothing is
normalised by hand; where the rendering does not carry a cell, the cell stays blank and the
row is flagged.

What is stored, and what is not
-------------------------------
* ``text`` is the document exactly as returned by the platform page-fetch tool, chunk marks
  removed and nothing reordered.
* ``text_sha256`` is over that text, so an edit to this module is detectable in review.
* **The PDF bytes are not stored here.** Bash egress to ``ak-static.cms.nba.com`` is
  blocked in this sandbox (TLS reset), so the bytes cannot be downloaded from a build.
  ``nba2/v4/injury_ingest.py`` attempts the byte-level archive from a GitHub runner, where
  the CDN is expected to be reachable, and records the outcome either way (F-V4-01).

Chunking
--------
The fetch tool returns long documents in chunks. The 13:00 PM release came back in two. The
junction fell inside the ``PHX@DEN`` block, so the join is recorded explicitly
(``chunk_junction``) with the basis for it: the resumed chunk re-prints the row prefix and
the resulting row has the same cell shape as every other row in that block, and the same
five Denver rows appear, single-chunked, in the 09:30 AM release. A reviewer can check both
PDFs at the URLs below. This is the one place in the module where a judgement was made, so
it is labelled rather than buried — F-V4-10.
"""

from __future__ import annotations

import hashlib

INDEX_URL = "https://official.nba.com/nba-injury-report-2026-27-season/"

# The status vocabulary the league prints. Anything outside it is *not* coerced into it:
# a word that is not a status stays unread and the row is flagged.
STATUS_WORDS = ("Out", "Doubtful", "Questionable", "Probable", "Available")

RENDERS = [
    {
        "stamp_et": "2026-11-16 09:30 AM ET",
        "revision_et": "11/16/26 09:30 AM",
        "url": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-16_09_30AM.pdf",
        "index_checked_utc": "2026-11-16T18:35:00Z",
        "retrieved_utc": "2026-11-16T18:36:00Z",
        "method": "platform page-fetch tool (fetch_page); returned as a single chunk",
        "chunk_junction": None,
        "text": """**Injury Report: 11/16/26 09:30 AM**

| Game Date | Game Time | Matchup | Team | Player Name | Current Status | Reason |
| --- | --- | --- | --- | --- | --- | --- |
| 11/16/2026 | 07:00 (ET) | CHI@CLE | Chicago Bulls | Awaka, Tobe | Out | Injury/Illness - Disc Irritation |
| 11/16/2026 | 07:00 (ET) | CHI@CLE | Chicago Bulls | Robinson, Orlando | Out | G League - On Assignment |
| 11/16/2026 | 07:00 (ET) | CHI@CLE | Chicago Bulls | Sellers, Jaylin | Out | G League - Two-Way |
| 11/16/2026 | 07:00 (ET) | CHI@CLE | Chicago Bulls | Smith, Jalen | Questionable | Injury/Illness - Left Finger Sprain |
| 11/16/2026 | 07:00 (ET) | CHI@CLE | Chicago Bulls | Wilson, Caleb | Out | Injury/Illness - Right Metacarpal Fracture |
| 11/16/2026 | 07:00 (ET) | CHI@CLE | Cleveland Cavaliers | Diop, Khalifa | Out | G League - On Assignment |
| 11/16/2026 | 07:00 (ET) | CHI@CLE | Cleveland Cavaliers | Merrill, Sam | Out | Injury/Illness - Right Elbow Injury Management |
| 11/16/2026 | 07:00 (ET) | CHI@CLE | Cleveland Cavaliers | Mobley, Evan | Out | Injury/Illness - Left Great Toe Sprain |
| 11/16/2026 | 07:00 (ET) | CHI@CLE | Cleveland Cavaliers | Tomlin, Nae'Qwan | Out | Injury/Illness - Low Back Stress Reaction |
| 11/16/2026 | 07:00 (ET) | CHI@CLE | Cleveland Cavaliers | Tyson, Jaylon | Doubtful | Injury/Illness - Right Ankle Injury Management |
| 11/16/2026 | 07:00 (ET) | CHI@CLE | Cleveland Cavaliers | Udeh, Jr., Ernest | Out | G League - Two-Way |
| 11/16/2026 | 07:00 (ET) | CHI@CLE | Cleveland Cavaliers | Watson, Peyton | Questionable | Injury/Illness - Right Abdominal Soreness |
| 11/16/2026 | 07:00 (ET) | MEM@WAS | Memphis Grizzlies | Edey, Zach | Questionable | Injury/Illness - Left Ankle Injury Management |
| 11/16/2026 | 07:00 (ET) | MEM@WAS | Memphis Grizzlies | Jackson, GG | Out | Injury/Illness - Left Foot Injury |

---

**Injury Report: 11/16/26 09:30 AM**

|  |  |  | Jerome, Ty | Out | Injury/Illness - Right Hip Soreness |
| --- | --- | --- | --- | --- | --- |
|  |  |  | Pippen Jr., Scotty | Out | Injury/Illness - Lumbar Disc Herniation |
|  |  |  | Post, Quinten | Questionable | Injury/Illness - Concussion Protocol |
|  |  |  | Saunders, Richie | Out | Injury/Illness - Right Knee Surgery |
|  |  |  | Stewart, Isaiah | Questionable | Injury/Illness - Illness |
|  |  | Washington Wizards |  |  | NOT YET SUBMITTED |
|  | ORL@BOS | Orlando Magic | Banchero, Paolo | Out | Injury/Illness - Right High Ankle Sprain |
|  | ORL@BOS | Orlando Magic | Isaac, Jonathan | Out | Injury/Illness - Left Knee Injury Management |
|  | ORL@BOS | Orlando Magic | Nelson, Izaiyah | Out | Injury/Illness - Left Ankle Injury Recovery |
|  | ORL@BOS | Orlando Magic | Penda, Noah | Out | Injury/Illness - Right Partially Torn Hamstring |
|  | ORL@BOS | Boston Celtics |  |  | NOT YET SUBMITTED |
| 07:30 (ET) | HOU@MIA | Houston Rockets |  |  | NOT YET SUBMITTED |
| 07:30 (ET) | HOU@MIA | Miami Heat | Goldin, Vladislav | Out | G League - Two-Way |
| 07:30 (ET) | HOU@MIA | Miami Heat | Larsson, Pelle | Questionable | Injury/Illness - Illness |
| 07:30 (ET) | HOU@MIA | Miami Heat | Thompson, Klay | Available | Injury/Illness - Left Ankle Sprain |
| 07:30 (ET) | PHI@BKN | Philadelphia 76ers |  |  | NOT YET SUBMITTED |

---

**Injury Report: 11/16/26 09:30 AM**

|  |  | Brooklyn Nets | Bilodeau, Tyler | Out | G League - Two-Way |
| --- | --- | --- | --- | --- | --- |
|  |  | Brooklyn Nets | Jefferson, Joshua | Out | G League - On Assignment |
|  |  | Brooklyn Nets | Nelson, Grant | Out | G League - Two-Way |
|  |  | Brooklyn Nets | Powell, Drake | Out | G League - On Assignment |
|  |  | Brooklyn Nets | Saraf, Ben | Out | G League - On Assignment |
|  | 08:00 (ET) | GSW@NOP | Golden State Warriors | Butler III, Jimmy | Injury/Illness - Right ACL Repair / Surgery |
|  | 08:00 (ET) | GSW@NOP | Golden State Warriors | Curry, Stephen | Out |
|  | 08:00 (ET) | GSW@NOP | Golden State Warriors | Moody, Moses | Out |
|  | 08:00 (ET) | GSW@NOP | Golden State Warriors | Porzingis, Kristaps | Out |
|  | 08:00 (ET) | GSW@NOP | Golden State Warriors | Santos, Gui | Questionable |
|  | 08:00 (ET) | GSW@NOP | Golden State Warriors | Williams, Brandon | Out |
|  | 08:00 (ET) | GSW@NOP | New Orleans Pelicans | Dia, Malik | Questionable | G League - Two-Way |
|  | 08:00 (ET) | GSW@NOP | New Orleans Pelicans | Mathurin, Bennedict | Out | Injury/Illness - Left Plantar Fasciitis |
|  | 08:00 (ET) | GSW@NOP | New Orleans Pelicans | McGowens, Bryce | Out | Injury/Illness - Left Elbow Infection |
|  | 08:00 (ET) | GSW@NOP | New Orleans Pelicans | Murphy III, Trey | Out | Injury/Illness - Bilateral Patellar Tendinopathy |
|  | 08:00 (ET) | GSW@NOP | New Orleans Pelicans | Murray, Dejounte | Out | Injury/Illness - Left Ankle Sprain |
|  | 08:00 (ET) | GSW@NOP | New Orleans Pelicans | Pierre Jr., Jaron | Questionable | G League - Two-Way |

---

**Injury Report: 11/16/26 09:30 AM**

|  |  |  |  | Reese, Julian | Questionable | G League - Two-Way |
| --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  | Watford, Trendon | Out | Injury/Illness - Right Ankle Sprain |
|  |  | POR@MIN | Portland Trail Blazers | Krejci, Vit | Out | Injury/Illness - Left Ankle Fracture |
|  |  | POR@MIN | Portland Trail Blazers | Morant, Ja | Out | Injury/Illness - Left Hamstring Strain |
|  |  | POR@MIN | Portland Trail Blazers | Sharpe, Shaedon | Out | Injury/Illness - Right Knee Surgery |
|  |  | POR@MIN | Portland Trail Blazers | Youngblood, Chris | Out | Injury/Illness - Right Heel Contusion / Bone Bruise |
|  |  | POR@MIN | Minnesota Timberwolves | Beringer, Joan | Available | Injury/Illness - Face Mask |
|  |  | POR@MIN | Minnesota Timberwolves | Clark, Jaylen | Out | Injury/Illness - Right Hamstring Strain |
|  |  | POR@MIN | Minnesota Timberwolves | DiVincenzo, Donte | Out | Injury/Illness - Right Achilles Tendon Repair / Surgery |
|  |  | POR@MIN | Minnesota Timberwolves | Edwards, Anthony | Out | Injury/Illness - Right Knee Arthroscopy |
|  | 09:00 (ET) | PHX@DEN | Phoenix Suns |  |  | NOT YET SUBMITTED |
|  | 09:00 (ET) | PHX@DEN | Denver Nuggets | Holmes II, DaRon | Out | G League - On Assignment |
|  | 09:00 (ET) | PHX@DEN | Denver Nuggets | Nembhard, Ryan | Out | G League - Two-Way |
|  | 09:00 (ET) | PHX@DEN | Denver Nuggets | Strawther, Julian | Out | Injury/Illness - Left Knee Sprain |
|  | 09:00 (ET) | PHX@DEN | Denver Nuggets | Whitmore, Cam | Out | G League - Two-Way |
| 11/17/2026 | 07:30 (ET) | NYK@TOR | New York Knicks |  |  | NOT YET SUBMITTED |
| 11/17/2026 | 07:30 (ET) | NYK@TOR | Toronto Raptors |  |  | NOT YET SUBMITTED |

---

**Injury Report: 11/16/26 09:30 AM**

|  | 08:00 (ET) | DET@SAS | Detroit Pistons | NOT YET SUBMITTED |
| --- | --- | --- | --- | --- |
|  | 08:00 (ET) | DET@SAS | San Antonio Spurs | NOT YET SUBMITTED |
|  | 08:00 (ET) | POR@MIN | Portland Trail Blazers | NOT YET SUBMITTED |
|  | 08:00 (ET) | POR@MIN | Minnesota Timberwolves | NOT YET SUBMITTED |
|  | 10:30 (ET) | UTA@LAC | Utah Jazz | NOT YET SUBMITTED |
|  | 10:30 (ET) | UTA@LAC | LA Clippers | NOT YET SUBMITTED |
|  | 11:00 (ET) | CHA@LAL | Charlotte Hornets | NOT YET SUBMITTED |
|  | 11:00 (ET) | CHA@LAL | Los Angeles Lakers | NOT YET SUBMITTED |""",
    },
    {
        "stamp_et": "2026-11-16 01:00 PM ET",
        "revision_et": "11/16/26 01:00 PM",
        "url": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-16_01_00PM.pdf",
        "index_checked_utc": "2026-11-16T18:35:00Z",
        "retrieved_utc": "2026-11-16T18:38:00Z",
        "method": "platform page-fetch tool (fetch_page); returned in two chunks",
        "chunk_junction": {
            "flag": "F-V4-10",
            "where": "inside the PHX@DEN block (11/16 09:00 ET)",
            "basis": ("the resumed chunk re-prints the row prefix, and joining it that way gives "
                      "the same six-cell shape as every other Denver row in the block; the same "
                      "five Denver rows were read single-chunked from the 09:30 AM release, and "
                      "they match row for row"),
        },
        "text": """**Injury Report: 11/16/26 01:00 PM**

| Game Date | Game Time | Matchup | Team | Player Name | Current Status | Reason |
| --- | --- | --- | --- | --- | --- | --- |
| 11/16/2026 | 07:00 (ET) | CHI@CLE | Chicago Bulls | Awaka, Tobe | Out | Injury/Illness - Disc Irritation |
| 11/16/2026 | 07:00 (ET) | CHI@CLE | Chicago Bulls | Robinson, Orlando | Out | G League - On Assignment |
| 11/16/2026 | 07:00 (ET) | CHI@CLE | Chicago Bulls | Sellers, Jaylin | Out | G League - Two-Way |
| 11/16/2026 | 07:00 (ET) | CHI@CLE | Chicago Bulls | Smith, Jalen | Questionable | Injury/Illness - Left Finger Sprain |
| 11/16/2026 | 07:00 (ET) | CHI@CLE | Chicago Bulls | Wilson, Caleb | Out | Injury/Illness - Right Metacarpal Fracture |
| 11/16/2026 | 07:00 (ET) | CHI@CLE | Cleveland Cavaliers | Diop, Khalifa | Out | G League - On Assignment |
| 11/16/2026 | 07:00 (ET) | CHI@CLE | Cleveland Cavaliers | Merrill, Sam | Out | Injury/Illness - Right Elbow Injury Management |
| 11/16/2026 | 07:00 (ET) | CHI@CLE | Cleveland Cavaliers | Mobley, Evan | Out | Injury/Illness - Left Great Toe Sprain |
| 11/16/2026 | 07:00 (ET) | CHI@CLE | Cleveland Cavaliers | Tomlin, Nae'Qwan | Out | Injury/Illness - Low Back Stress Reaction |
| 11/16/2026 | 07:00 (ET) | CHI@CLE | Cleveland Cavaliers | Tyson, Jaylon | Doubtful | Injury/Illness - Right Ankle Injury Management |
| 11/16/2026 | 07:00 (ET) | CHI@CLE | Cleveland Cavaliers | Udeh, Jr., Ernest | Out | G League - Two-Way |
| 11/16/2026 | 07:00 (ET) | CHI@CLE | Cleveland Cavaliers | Watson, Peyton | Questionable | Injury/Illness - Right Abdominal Soreness |
| 11/16/2026 | 07:00 (ET) | MEM@WAS | Memphis Grizzlies | Edey, Zach | Questionable | Injury/Illness - Left Ankle Injury Management |
| 11/16/2026 | 07:00 (ET) | MEM@WAS | Memphis Grizzlies | Jackson, GG | Out | Injury/Illness - Left 5th Metatarsal |

---

**Injury Report: 11/16/26 01:00 PM**

|  |  | Fracture |  |  |  |
| --- | --- | --- | --- | --- | --- |
|  |  | Jerome, Ty | Out | Injury/Illness - Right Hip Soreness |
|  |  | Pippen Jr., Scotty | Out | Injury/Illness - Lumbar Disc Herniation |
|  |  | Post, Quinten | Questionable | Injury/Illness - Concussion Protocol |
|  |  | Saunders, Richie | Out | Injury/Illness - Right Knee Surgery |
|  |  | Stewart, Isaiah | Out | Injury/Illness - Illness |
|  | Washington Wizards | Beekman, Reece | Out | Injury/Illness - Right AC Joint Injury |
|  | Washington Wizards | Champagne, Justin | Out | Injury/Illness - Right Foot Surgery |
|  | Washington Wizards | Johnson, Tre | Questionable | Injury/Illness - Low Back Soreness |
|  | Washington Wizards | Okpara, Felix | Questionable | G League - Two-Way |
|  | Washington Wizards | Vukcevic, Tristan | Out | Injury/Illness - Left Hip Impingement |
|  | Washington Wizards | Watkins, Jamir | Out | Injury/Illness - Left ACL Repair / Surgery |
| ORL@BOS | Orlando Magic | Banchero, Paolo | Out | Injury/Illness - Right High Ankle Sprain |
| ORL@BOS | Orlando Magic | Isaac, Jonathan | Out | Injury/Illness - Left Knee Injury Management |
| ORL@BOS | Orlando Magic | Nelson, Izaiyah | Out | Injury/Illness - Left Ankle Injury Recovery |
| ORL@BOS | Orlando Magic | Penda, Noah | Out | Injury/Illness - Right Partially Torn Hamstring |

---

**Injury Report: 11/16/26 01:00 PM**

| Boston Celtics |  |  | NOT YET SUBMITTED |  |  |  |
| --- | --- | --- | --- | --- | --- | --- |
| 07:30 (ET) | HOU@MIA | Houston Rockets | Adams, Steven | Out | Injury/Illness - Left Lower Leg Injury Management |
| 07:30 (ET) | HOU@MIA | Houston Rockets | Capela, Clint | Out | Injury/Illness - Right Ankle Sprain |
| 07:30 (ET) | HOU@MIA | Houston Rockets | Copeland, Quadir | Out | G League - Two-Way |
| 07:30 (ET) | HOU@MIA | Houston Rockets | Phillips, Julian | Out | G League - Two-Way |
| 07:30 (ET) | HOU@MIA | Houston Rockets | Smart, Marcus | Out | League Suspension |
| 07:30 (ET) | HOU@MIA | Houston Rockets | Thompson, Amen | Questionable | Injury/Illness - Left Knee Soreness |
| 07:30 (ET) | HOU@MIA | Miami Heat | Goldin, Vladislav | Out | G League - Two-Way |
| 07:30 (ET) | HOU@MIA | Miami Heat | Jovic, Nikola | Questionable | Injury/Illness - Illness |
| 07:30 (ET) | HOU@MIA | Miami Heat | Larsson, Pelle | Doubtful | Injury/Illness - Illness |
| 07:30 (ET) | HOU@MIA | Miami Heat | Thompson, Klay | Available | Injury/Illness - Left Ankle Sprain |
| 07:30 (ET) | PHI@BKN | Philadelphia 76ers | Barlow, Dominick | Out | Injury/Illness - Low Back Stress Reaction |
| 07:30 (ET) | PHI@BKN | Philadelphia 76ers | Bona, Adem | Out | Injury/Illness - Cervical Spine Sprain |
| 07:30 (ET) | PHI@BKN | Philadelphia 76ers | Embiid, Joel | Questionable | Injury/Illness - Right Foot Plantar Fascia Injury Management |
| 07:30 (ET) | PHI@BKN | Philadelphia 76ers | Hukporti, Ariel | Out | Injury/Illness - Right Achilles Tendon Rupture / Tear |
| 07:30 (ET) | PHI@BKN | Philadelphia 76ers | James, LeBron | Out | Injury/Illness - Low Back/Sciatica Management |

---

**Injury Report: 11/16/26 01:00 PM**

|  |  | Brooklyn Nets | Bilodeau, Tyler | Out | G League - Two-Way |
| --- | --- | --- | --- | --- | --- |
|  |  | Brooklyn Nets | Jefferson, Joshua | Out | G League - On Assignment |
|  |  | Brooklyn Nets | Nelson, Grant | Out | G League - Two-Way |
|  |  | Brooklyn Nets | Powell, Drake | Out | G League - On Assignment |
|  |  | Brooklyn Nets | Saraf, Ben | Out | G League - On Assignment |
|  | 08:00 (ET) | GSW@NOP | Golden State Warriors | Butler III, Jimmy | Injury/Illness - Right ACL Repair / Surgery |
|  | 08:00 (ET) | GSW@NOP | Golden State Warriors | Curry, Stephen | Out |
|  | 08:00 (ET) | GSW@NOP | Golden State Warriors | Moody, Moses | Out |
|  | 08:00 (ET) | GSW@NOP | Golden State Warriors | Porzingis, Kristaps | Out |
|  | 08:00 (ET) | GSW@NOP | Golden State Warriors | Santos, Gui | Questionable |
|  | 08:00 (ET) | GSW@NOP | Golden State Warriors | Williams, Brandon | Out |
|  | 08:00 (ET) | GSW@NOP | New Orleans Pelicans | Dia, Malik | Questionable | G League - Two-Way |
|  | 08:00 (ET) | GSW@NOP | New Orleans Pelicans | Mathurin, Bennedict | Out | Injury/Illness - Left Plantar Fasciitis |
|  | 08:00 (ET) | GSW@NOP | New Orleans Pelicans | McGowens, Bryce | Out | Injury/Illness - Left Elbow Infection |
|  | 08:00 (ET) | GSW@NOP | New Orleans Pelicans | Murphy III, Trey | Out | Injury/Illness - Bilateral Patellar Tendinopathy |
|  | 08:00 (ET) | GSW@NOP | New Orleans Pelicans | Murray, Dejounte | Out | Injury/Illness - Left Ankle Sprain |
|  | 08:00 (ET) | GSW@NOP | New Orleans Pelicans | Pierre Jr., Jaron | Questionable | G League - Two-Way |

---

**Injury Report: 11/16/26 01:00 PM**

|  |  |  |  | Reese, Julian | Questionable | G League - Two-Way |
| --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  | Watford, Trendon | Out | Injury/Illness - Right Ankle Sprain |
|  |  | POR@MIN | Portland Trail Blazers | Krejci, Vit | Out | Injury/Illness - Left Ankle Fracture |
|  |  | POR@MIN | Portland Trail Blazers | Morant, Ja | Out | Injury/Illness - Left Hamstring Strain |
|  |  | POR@MIN | Portland Trail Blazers | Sharpe, Shaedon | Out | Injury/Illness - Right Knee Surgery |
|  |  | POR@MIN | Portland Trail Blazers | Youngblood, Chris | Out | Injury/Illness - Right Heel Contusion / Bone Bruise |
|  |  | POR@MIN | Minnesota Timberwolves | Beringer, Joan | Available | Injury/Illness - Face Mask |
|  |  | POR@MIN | Minnesota Timberwolves | Clark, Jaylen | Out | Injury/Illness - Right Hamstring Strain |
|  |  | POR@MIN | Minnesota Timberwolves | DiVincenzo, Donte | Out | Injury/Illness - Right Achilles Tendon Repair / Surgery |
|  |  | POR@MIN | Minnesota Timberwolves | Edwards, Anthony | Out | Injury/Illness - Right Knee Arthroscopy |
|  | 09:00 (ET) | PHX@DEN | Phoenix Suns |  |  | NOT YET SUBMITTED |
|  | 09:00 (ET) | PHX@DEN | Denver Nuggets | Holmes II, DaRon | Out | G League - On Assignment |
|  | 09:00 (ET) | PHX@DEN | Denver Nuggets | Nembhard, Ryan | Out | G League - Two-Way |
|  | 09:00 (ET) | PHX@DEN | Denver Nuggets | Strawther, Julian | Out | Injury/Illness - Left Knee Sprain |
|  | 09:00 (ET) | PHX@DEN | Denver Nuggets | Whitmore, Cam | Out | G League - Two-Way |
| 11/17/2026 | 07:30 (ET) | NYK@TOR | New York Knicks |  |  | NOT YET SUBMITTED |
| 11/17/2026 | 07:30 (ET) | NYK@TOR | Toronto Raptors |  |  | NOT YET SUBMITTED |

---

**Injury Report: 11/16/26 01:00 PM**

|  | 08:00 (ET) | DET@SAS | Detroit Pistons | NOT YET SUBMITTED |
| --- | --- | --- | --- | --- |
|  | 08:00 (ET) | DET@SAS | San Antonio Spurs | NOT YET SUBMITTED |
|  | 08:00 (ET) | POR@MIN | Portland Trail Blazers | NOT YET SUBMITTED |
|  | 08:00 (ET) | POR@MIN | Minnesota Timberwolves | NOT YET SUBMITTED |
|  | 10:30 (ET) | UTA@LAC | Utah Jazz | NOT YET SUBMITTED |
|  | 10:30 (ET) | UTA@LAC | LA Clippers | NOT YET SUBMITTED |
|  | 11:00 (ET) | CHA@LAL | Charlotte Hornets | NOT YET SUBMITTED |
|  | 11:00 (ET) | CHA@LAL | Los Angeles Lakers | NOT YET SUBMITTED |""",
    },
    {
        "stamp_et": "2026-11-17 11:00 AM ET",
        "revision_et": "11/17/26 11:00 AM",
        "url": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-17_11_00AM.pdf",
        "index_checked_utc": "2026-11-17T16:39:00Z",
        "retrieved_utc": "2026-11-17T16:41:00Z",
        "method": "platform page-fetch tool (fetch_page); returned as a single chunk",
        "chunk_junction": "the Kessler reason ends at 'Right Lower Leg' and the next rendered "
                          "line prints a stray header cell 'Soreness' before the Reaves "
                          "continuation row; the junction is recorded, not merged (F-V4-10)",
        "text": "## Injury Report: 11/17/26 11:00 AM\n\n| Game Date | Game Time | Matchup | Team | Player Name | Current Status | Reason |\n| --- | --- | --- | --- | --- | --- | --- |\n| 11/17/2026 | 07:30 (ET) | NYK@TOR | Toronto Raptors | Bittle, Nate | Out | Injury/Illness - Right Foot Avulsion Fracture |\n| 11/17/2026 | 07:30 (ET) | NYK@TOR | Toronto Raptors | Leonard, Kawhi | Out | Injury/Illness - Left Knee Injury Management |\n| 11/17/2026 | 07:30 (ET) | NYK@TOR | Toronto Raptors | McCullar Jr., Kevin | Out | G League - Two-Way |\n| 11/17/2026 | 07:30 (ET) | NYK@TOR | Toronto Raptors | Smith, Malachi | Out | G League - Two-Way |\n| 11/17/2026 | 08:00 (ET) | DET@SAS | Detroit Pistons | Duren, Jalen | Out | Injury/Illness - Right Hamstring Strain |\n| 11/17/2026 | 08:00 (ET) | DET@SAS | Detroit Pistons | Holland II, Ronald | Out | Injury/Illness - Left Knee Contusion / Bone Bruise |\n| 11/17/2026 | 08:00 (ET) | DET@SAS | Detroit Pistons | Joe, Isaiah | Doubtful | Injury/Illness - Right Hip Contusion |\n| 11/17/2026 | 08:00 (ET) | DET@SAS | Detroit Pistons | Okorie, Ebuka | Out | G League - On Assignment |\n| 11/17/2026 | 08:00 (ET) | DET@SAS | Detroit Pistons | Onyenso, Ugonna | Out | G League - Two-Way |\n| 11/17/2026 | 08:00 (ET) | DET@SAS | Detroit Pistons | Prince, Taurean | Out | Injury/Illness - Right Knee Soreness |\n| 11/17/2026 | 08:00 (ET) | DET@SAS | Detroit Pistons | Robinson, Duncan | Out | Injury/Illness - Left Quadriceps Strain |\n| 11/17/2026 | 08:00 (ET) | DET@SAS | San Antonio Spurs | Brown, Maliq | Out | G League - Two-Way |\n| 11/17/2026 | 08:00 (ET) | DET@SAS | San Antonio Spurs | Gillespie, Ja'Kobi | Out | G League - Two-Way |\n| 11/17/2026 | 08:00 (ET) | DET@SAS | San Antonio Spurs | Harris, Tobias | Out | Injury/Illness - Left Calf Strain |\n| 11/17/2026 | 08:00 (ET) | DET@SAS | San Antonio Spurs | Quaintance, Jayden | Out | Injury/Illness - Right Knee Surgery |\n| 11/17/2026 | 08:00 (ET) | POR@MIN | Portland Trail Blazers |  |  | NOT YET SUBMITTED |\n\n---\n\n**Injury Report: 11/17/26 11:00 AM**\n\n|  |  | Minnesota Timberwolves |  |  | NOT YET SUBMITTED |\n| --- | --- | --- | --- | --- | --- |\n| 10:30 (ET) | UTA@LAC | Utah Jazz | Bufkin, Kobe | Out | G League - Two-Way |\n| 10:30 (ET) | UTA@LAC | Utah Jazz | Hayes, Jaxson | Out | Injury/Illness - Left Knee Strain |\n| 10:30 (ET) | UTA@LAC | Utah Jazz | Ingram, Harrison | Out | G League - Two-Way |\n| 10:30 (ET) | UTA@LAC | Utah Jazz | Jackson Jr., Jaren | Out | Injury/Illness - Right MCL Tear |\n| 10:30 (ET) | UTA@LAC | Utah Jazz | Markkanen, Lauri | Out | Injury/Illness - Right Hand Fracture |\n| 10:30 (ET) | UTA@LAC | Utah Jazz | Nurkic, Jusuf | Out | Injury/Illness - Right Right Foot; 2nd Plantar Plate Tear |\n| 10:30 (ET) | UTA@LAC | LA Clippers | Beal, Bradley | Out | Injury/Illness - Right Knee Injury Management |\n| 10:30 (ET) | UTA@LAC | LA Clippers | Ingram, Brandon | Out | Injury/Illness - Right Heel Surgery |\n| 10:30 (ET) | UTA@LAC | LA Clippers | Miller, Jordan | Out | Injury/Illness - Left Rotator Cuff Surgery |\n| 10:30 (ET) | UTA@LAC | LA Clippers | Niederhauser, Yanic Konan | Out | Injury/Illness - Right Lisfranc Surgery |\n| 11:00 (ET) | CHA@LAL | Charlotte Hornets | Ajayi, Michael | Out | G League - Two-Way |\n| 11:00 (ET) | CHA@LAL | Charlotte Hornets | Boswell, Kylan | Out | G League - Two-Way |\n| 11:00 (ET) | CHA@LAL | Charlotte Hornets | Knueppel, Kon | Out | Injury/Illness - Left Hamstring Strain |\n| 11:00 (ET) | CHA@LAL | Charlotte Hornets | Schroder, Dennis | Out | Injury/Illness - Left Hamstring Strain |\n| 11:00 (ET) | CHA@LAL | Charlotte Hornets | Steinbach, Hannes | Out | G League - On Assignment |\n| 11:00 (ET) | CHA@LAL | Los Angeles Lakers | Grimes, Quentin | Available | Injury/Illness - Right Finger Splint |\n| 11:00 (ET) | CHA@LAL | Los Angeles Lakers | Kessler, Walker | Out | Injury/Illness - Right Lower Leg |\n\n---\n\n**Injury Report: 11/17/26 11:00 AM**\n\n|  |  |  |  | Soreness |  |  |\n| --- | --- | --- | --- | --- | --- | --- |\n|  |  |  |  | Reaves, Austin | Out | Injury/Illness - Left Heel Contusion / Bone Bruise |\n| 11/18/2026 | 07:00 (ET) | HOU@IND | Houston Rockets |  |  | NOT YET SUBMITTED |\n| 11/18/2026 | 07:00 (ET) | HOU@IND | Indiana Pacers |  |  | NOT YET SUBMITTED |\n| 11/18/2026 | 07:00 (ET) | MEM@CLE | Memphis Grizzlies |  |  | NOT YET SUBMITTED |\n| 11/18/2026 | 07:00 (ET) | MEM@CLE | Cleveland Cavaliers |  |  | NOT YET SUBMITTED |\n| 11/18/2026 | 07:00 (ET) | MIL@MIA | Milwaukee Bucks |  |  | NOT YET SUBMITTED |\n| 11/18/2026 | 07:00 (ET) | MIL@MIA | Miami Heat |  |  | NOT YET SUBMITTED |\n| 11/18/2026 | 07:00 (ET) | PHI@ORL | Philadelphia 76ers |  |  | NOT YET SUBMITTED |\n| 11/18/2026 | 07:00 (ET) | PHI@ORL | Orlando Magic |  |  | NOT YET SUBMITTED |\n| 11/18/2026 | 07:30 (ET) | CHI@BKN | Chicago Bulls |  |  | NOT YET SUBMITTED |\n| 11/18/2026 | 07:30 (ET) | CHI@BKN | Brooklyn Nets |  |  | NOT YET SUBMITTED |\n| 11/18/2026 | 07:30 (ET) | WAS@TOR | Washington Wizards |  |  | NOT YET SUBMITTED |\n| 11/18/2026 | 07:30 (ET) | WAS@TOR | Toronto Raptors |  |  | NOT YET SUBMITTED |\n| 11/18/2026 | 08:00 (ET) | ATL@OKC | Atlanta Hawks |  |  | NOT YET SUBMITTED |\n| 11/18/2026 | 08:00 (ET) | ATL@OKC | Oklahoma City Thunder |  |  | NOT YET SUBMITTED |\n| 11/18/2026 | 08:00 (ET) | DET@NOP | Detroit Pistons |  |  | NOT YET SUBMITTED |\n| 11/18/2026 | 08:00 (ET) | DET@NOP | New Orleans Pelicans |  |  | NOT YET SUBMITTED |\n\n---\n\n**Injury Report: 11/17/26 11:00 AM**\n\n|  |  | GSW@DAL | Golden State Warriors | NOT YET SUBMITTED |\n| --- | --- | --- | --- | --- |\n|  |  | GSW@DAL | Dallas Mavericks | NOT YET SUBMITTED |\n|  | 09:30 (ET) | BOS@DEN | Boston Celtics | NOT YET SUBMITTED |\n|  | 09:30 (ET) | BOS@DEN | Denver Nuggets | NOT YET SUBMITTED |\n|  | 10:00 (ET) | PHX@SAC | Phoenix Suns | NOT YET SUBMITTED |\n|  | 10:00 (ET) | PHX@SAC | Sacramento Kings | NOT YET SUBMITTED |\n|  | 10:00 (ET) | UTA@LAL | Utah Jazz | NOT YET SUBMITTED |\n|  | 10:00 (ET) | UTA@LAL | Los Angeles Lakers | NOT YET SUBMITTED |\n",
    },
]


def text_sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _revision_key(revision_et: str) -> tuple:
    """'11/16/26 09:30 AM' -> (2026, 11, 16, 9, 30). Used only to order the releases."""
    date, clock, ampm = revision_et.split(" ")
    mm, dd, yy = (int(x) for x in date.split("/"))
    hh, mi = (int(x) for x in clock.split(":"))
    hh = hh % 12 + (12 if ampm == "PM" else 0)
    return (2000 + yy, mm, dd, hh, mi)


def newest() -> dict:
    """The most recent stored rendering. Never a guess: ordered by the PDF's own stamp."""
    return sorted(RENDERS, key=lambda r: _revision_key(r["revision_et"]))[-1]


def with_hashes() -> list[dict]:
    out = []
    for r in RENDERS:
        d = {k: v for k, v in r.items() if k != "text"}
        d["text_sha256"] = text_sha(r["text"])
        d["text_lines"] = len(r["text"].splitlines())
        out.append(d)
    return out


def selftest() -> list[str]:
    """Cheap invariants: a rendering that contradicts its own header fails the build."""
    problems: list[str] = []
    for r in RENDERS:
        head = f"Injury Report: {r['revision_et']}"
        if head not in r["text"]:
            problems.append(f"{r['stamp_et']}: header {head!r} not found in the stored text")
        if r["url"].rsplit("/", 1)[-1].replace("Injury-Report_", "").replace(".pdf", "") == "":
            problems.append(f"{r['stamp_et']}: empty PDF name")
        if not r["index_checked_utc"] or not r["retrieved_utc"]:
            problems.append(f"{r['stamp_et']}: a stamp is missing")
    stamps = [r["revision_et"] for r in RENDERS]
    if stamps != sorted(stamps, key=_revision_key):
        problems.append("renders are not stored in revision order")
    if len(set(stamps)) != len(stamps):
        problems.append("duplicate revision stamp")
    return problems
