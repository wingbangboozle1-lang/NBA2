# Official-source spot check — `arena/e77ce5ad-nba2` (S-02)

Checked: 2026-11-14 (UTC session date). Method: platform page-fetch tool only (direct `curl` to nba.com is blocked from this sandbox). Every row below records the value, the official URL fetched, and the result. A row is **Verified** only if the official text was fetched in this session and quoted here. Nothing in the published site was edited.

## Official URLs fetched

| Ref | Official URL | What it shows |
|---|---|---|
| OF-1 | https://official.nba.com/nba-injury-report-2026-27-season/ | Index of NBA referee-operations injury PDFs for 11/14; latest listed revision = **05:15 AM ET** |
| OF-2 | https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_05_15AM.pdf | Injury report 11/14/26 05:15 AM (text extraction; later table pages partly garbled) |
| OF-3 | https://www.nba.com/games?date=2026-11-14 | nba.com game list for 11/14 with ET tip times |
| OF-4 | https://www.nba.com/games?date=2026-11-15 | nba.com game list for 11/15 with ET tip times (chunk 1 of 2 read; 6 games shown in full, 9 games on the calendar cell) |
| OF-5 | https://www.nba.com/schedule | Schedule shell (JavaScript-rendered; no game rows in the fetched text) — **not usable as a value source** |

## A. Tip times, 11/14 (repo value from `data/raw/official_game_times_2026-11-14.json`)

| Matchup (away@home) | Repo ET | Official ET (OF-3) | Result | Notes |
|---|---|---|---|---|
| DEN@NOP | 19:00 | 7:00 pm ET (`den-vs-nop-0022600231`) | **Verified** | |
| DAL@CLE | 19:30 | 7:30 pm ET (`dal-vs-cle-0022600232`) | **Verified** | |
| BKN@MEM | 20:00 | 8:00 pm ET (`bkn-vs-mem-0022600234`) | **Verified** | |
| DET@MIA | 20:00 | 8:00 pm ET (`det-vs-mia-0022600233`) | **Time verified; source label IRREGULAR** | The repo says this time was "captured" from the 07:30 PM injury PDF (`time_captured: true`). The same repo's injury snapshot note says the PDF's time cell for DET@MIA was **lost in extraction**. The time is right; the attribution is wrong. See I-02. |
| CHI@MIN | 20:00 | 8:00 pm ET (`chi-vs-min-0022600235`) | **Verified** | |

Game count for 11/14: nba.com calendar shows **5 games** on 11/14 (OF-3 calendar cell); repo has 5. **Verified.**

## B. Tip times, 11/15 (not in the repo's published slate)

| Matchup | Official ET (OF-4) | OF-2 printed row | Result |
|---|---|---|---|
| IND@PHI | 1:00 PM ET (`ind-vs-phi-0022600236`) | `11/15/2026 \| 01:00 (ET) \| IND@PHI` — NOT YET SUBMITTED for both teams | Official row exists; time agrees with the PDF once read as 1:00 PM. **Not in repo.** |
| LAL@PHX | 4:00 PM ET (`lal-vs-phx-0022600237`) | `11/15/2026 \| 04:00 (ET) \| LAL@PHX` — NOT YET SUBMITTED | Official row exists; agrees. **Not in repo.** |
| CHA@LAC, SAS@UTA, NYK@TOR, DAL@BOS (11/15) | 4:30, 5:00, 6:00, 6:00 PM ET (OF-4) | Not in OF-2 text, which shows these only as `04:30 (ET) CHA@LAC` etc. with no date cell | Not checked against the repo (not in published slate). See I-04. |

## C. 11/14 injury rows: latest official release (05:15 AM ET, OF-2) vs. repo snapshot `data/raw/injury_report_2026-11-14_daybefore.json` (19:30 ET release)

| Team (game) | Official 05:15 AM rows | Repo 19:30 rows | Result |
|---|---|---|---|
| Denver (DEN@NOP) | Holmes II Out (G League – On Assignment); Nembhard Out (G League – Two-Way); Strawther Out (Injury/Illness – Left Knee Sprain); Whitmore Out (G League – Two-Way) | identical (4 rows) | **Verified (no change)** |
| New Orleans (DEN@NOP) | NOT YET SUBMITTED | NOT YET SUBMITTED | **Verified (no change)** |
| Dallas (DAL@CLE) | Biberovic Out; Christie Questionable; de Larrea Out; Johnson Jr. Probable; Lively II Out; Martin, Caleb Available | identical (6 rows) | **Verified (no change)** |
| Cleveland (DAL@CLE) | NOT YET SUBMITTED | NOT YET SUBMITTED | **Verified (no change)** |
| Brooklyn (BKN@MEM) | Bilodeau Out; Brown Jr. Questionable; Jefferson Out; Nelson Out; Saraf Out; Traore, Nolan Probable | identical (6 rows) | **Verified (no change)** |
| Memphis (BKN@MEM) | NOT YET SUBMITTED (visible in OF-2 continuation text) | NOT YET SUBMITTED | **Verified (no change)** |
| Chicago (CHI@MIN) | NOT YET SUBMITTED | NOT YET SUBMITTED | **Verified (no change)** |
| Minnesota (CHI@MIN) | Beringer Available; DiVincenzo Out; Edwards Out | identical (3 rows) | **Verified (no change)** |
| Detroit (DET@MIA) | Duren Out; Harkless Questionable; Joe Out; Jones Questionable; Lanier Out; Okorie Out; Onyenso Out | identical (7 rows) | **Verified (no change)** |
| Miami (DET@MIA) | NOT YET SUBMITTED | NOT YET SUBMITTED | **Verified (no change)** |

Result: all 11/14 rows the repo carries match the 05:15 AM release. **No status changes were found in the rows that could be read.** Rows from the continuation pages of OF-2 (CHI/MIN/MIA/later games) were read only where the text was legible; the rest of that PDF text is garbled, so those are reported as "not re-read" below.

## D. Gaps and open items (not verified; left as-is)

- **I-01 — Stale injury snapshot.** The published injury data stops at the **19:30 ET 11/13** release. The official index (OF-1) lists a newer **05:15 AM ET 11/14** release (and the 11/14 day-of reports are still due). The published site does say "later game-day releases can still change statuses before tip-off", so the staleness is disclosed, but the newer release is not ingested. *Requested, not edited* — owned by the data-refresh session.
- **I-02 — DET@MIA time provenance.** Time value correct (8:00 pm ET per OF-3), but `official_game_times_2026-11-14.json` marks it as captured from the 07:30 PM injury PDF, while the injury snapshot says that cell was lost. Attribution should read "nba.com/games (schedule capture)".
- **I-03 — Time-conversion rule.** The repo converts the PDF's bare "07:00 (ET)" to 19:00 ("evening times on a 12-hour clock"). This is correct for every 11/13–11/14 row checked above, but the same rule would turn the 11/15 "01:00 (ET)" (IND@PHI, verified 1:00 PM) into 01:00, and "04:00 (ET)" (LAL@PHX, verified 4:00 PM) into 04:00. A rule that reads hours 1–6 as PM would be needed before ingesting 11/15–11/16 rows. *Logged for the owner; not changed.*
- **I-04 — 11/15 slate not yet in the repo.** Nine 11/15 games are on the nba.com calendar (OF-4) and the PDF lists the first ones. The repo holds no 11/15–11/17 games; this is consistent with the board's prior FLAG-SLATE-06 but worth re-stating: the 11/15 games are on the official calendar now.
- **I-05 — Schedule page is a JavaScript shell.** `nba.com/schedule` fetched without game rows, so it cannot verify values. The `games?date=` pages do carry the rows. Any table citing `/schedule` alone should cite the date pages instead.
- **I-06 — Partial PDF read.** OF-2's later pages were partly garbled by text extraction (for example, the first-row cells for CHI@MIN and DET@MIA continuation rows lack the date/matchup cells). Those rows were compared only where legible. A full row-by-row re-read needs a PDF-capable fetch, which this session did not have.

## Result

| Check | Result |
|---|---|
| 11/14 tip times (5 games) | 4 verified; DET@MIA value verified but its stated source is wrong (I-02) |
| 11/14 injury rows vs. latest official release (10 team blocks) | all legible rows match; no changes |
| Published injury snapshot currency | **behind** — 19:30 ET vs. 05:15 AM ET (I-01) |
| 11/15 games | official, not in repo (I-04) |
