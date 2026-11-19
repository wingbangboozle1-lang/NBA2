url: https://www.nba.com/stats/teams/opponent?Season=2026-27&SeasonType=Regular+Season
retrieved_utc: 2026-11-19T12:26Z
retrieval_method: agent page-fetch tool (direct curl to www.nba.com fails TLS handshake from the sandbox)
page_title: Teams Opponent | Stats | NBA.com
page_header_rows: 30 Rows; season 2026-27; Season Type = Regular Season
default_columns_printed_by_the_page: GP W L MIN OppFGM OppFGA OppFG% Opp3PM Opp3PA Opp3P%
  OppFTM OppFTA OppFT% OppOREB OppDREB OppREB OppAST OppTOV OppSTL OppBLK OppBLKA OppPF OppPFD
  OppPTS +/- (plus a RANK column for each)

WHAT THIS FILE CONTAINS, EXACTLY
  The four columns this session parses — GP, OppPTS, +/- and MIN — reproduced verbatim in the
  page's row order. **The other 21 stat columns were not transcribed and no claim is made about
  them.** Every value below can be checked against the URL above.

---- rows (page order) ----

| 1 | Los Angeles Lakers | 16 | 48.3 | 114.4 | -6.4 |
| 1 | Philadelphia 76ers | 16 | 48.0 | 111.6 | -2.9 |
| 3 | Houston Rockets | 16 | 48.0 | 109.2 | -8.7 |
| 3 | San Antonio Spurs | 15 | 48.3 | 105.9 | -11.2 |
| 5 | Boston Celtics | 15 | 48.3 | 103.4 | -10.5 |
| 5 | Memphis Grizzlies | 15 | 48.3 | 112.9 | -9.0 |
| 5 | Minnesota Timberwolves | 15 | 48.3 | 106.1 | -10.6 |
| 8 | Detroit Pistons | 14 | 48.7 | 108.9 | -6.4 |
| 9 | Atlanta Hawks | 15 | 48.3 | 115.8 | -1.9 |
| 9 | Miami Heat | 15 | 48.3 | 119.9 | -0.7 |
| 9 | Oklahoma City Thunder | 15 | 48.0 | 107.7 | -4.4 |
| 9 | Portland Trail Blazers | 14 | 48.0 | 111.0 | -6.0 |
| 13 | Cleveland Cavaliers | 16 | 48.3 | 116.3 | -1.9 |
| 13 | Dallas Mavericks | 15 | 48.0 | 113.2 | 0.9 |
| 13 | Denver Nuggets | 13 | 48.4 | 112.2 | -0.9 |
| 13 | Golden State Warriors | 15 | 48.3 | 112.8 | -0.9 |
| 13 | New York Knicks | 14 | 48.4 | 103.9 | -6.1 |
| 18 | Phoenix Suns | 14 | 48.0 | 115.7 | 1.6 |
| 19 | Orlando Magic | 14 | 48.4 | 112.8 | 3.4 |
| 20 | Indiana Pacers | 15 | 48.0 | 114.8 | 3.3 |
| 20 | New Orleans Pelicans | 16 | 48.9 | 122.8 | 7.4 |
| 20 | Toronto Raptors | 15 | 48.3 | 112.0 | 0.0 |
| 20 | Washington Wizards | 16 | 48.6 | 117.9 | 7.2 |
| 24 | Charlotte Hornets | 14 | 48.4 | 110.4 | 10.3 |
| 24 | Chicago Bulls | 14 | 48.4 | 124.6 | 8.4 |
| 24 | LA Clippers | 13 | 48.4 | 117.7 | 5.8 |
| 27 | Brooklyn Nets | 14 | 48.4 | 119.2 | 8.4 |
| 27 | Utah Jazz | 16 | 48.6 | 116.0 | 7.3 |
| 29 | Milwaukee Bucks | 15 | 48.0 | 120.9 | 13.1 |
| 29 | Sacramento Kings | 14 | 48.0 | 121.7 | 14.0 |

---- identity checks a transcription error would break (all pass on the numbers above) ----

For every one of the 30 clubs: OwnPTS(traditional page) − OppPTS(this page) equals the +/− on the
traditional page, and equals the negated +/− on this page. Spot values:
  BOS 113.9 − 103.4 = +10.5 (traditional +/- 10.5; opponent +/- −10.5)
  SAS 117.1 − 105.9 = +11.2 (traditional +/- 11.2; opponent +/- −11.2)
  SAC 107.7 − 121.7 = −14.0 (traditional +/- −14.0; opponent +/- 14.0)
  MIN 116.7 − 106.1 = +10.6 (traditional +/- 10.6; opponent +/- −10.6)
The full 30-club recomputation is done in code by tools/session-164d832b-capture.py, which fails
closed on any mismatch.

---- irregularity ----

The Kings (+/- 14.0 on this page) and the Bucks (13.1) print ranks 29 and 29 on the traditional
page despite the traditional page's own +/− ordering being Kings −14.0 then Bucks −13.1 — i.e. the
"29" rank is shared by the two worst records, not a sort error. Recorded for completeness.
