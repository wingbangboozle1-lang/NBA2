# Live verification — session `arena/3cd85a22-nba2` (2026-11-16, UTC)

Independent verification of the committed published data against the **live official NBA
sources**, read this session, plus a fresh official capture of the 2026-11-16 slate, standings
and injury report. Every verified value below carries its official source URL and this session's
retrieval stamp. A value that could not be confirmed is left blank and flagged — none is inferred.

**Branch:** `arena/3cd85a22-nba2` (base `f943bd1` = `main`). **Retrieval stamp:**
`2026-11-16T18:23:30Z` (13:23 ET). **Scope:** `verified/session-3cd85a22-live/**`,
`analysis/session-3cd85a22-live-verification.md`, append-only `COORDINATION.md`. No file owned by
the open PRs (#98/#82/#80/#78/#72/#70) or by the shared site output was edited.

## 0. Why this session could verify live (and earlier ones could not)

Earlier sessions recorded that `cdn.nba.com` / `stats.nba.com` / `ak-static.cms.nba.com` were
unreachable from **bash** (`HTTP 000` / `SSL_ERROR_SYSCALL`). That is still true of bash. But the
platform **`fetch_page` tool reaches the official sources**, and this session used it to read the
live pages directly. So the "no official value could be re-fetched" caveat that qualified IR-1…IR-9
does **not** apply here: the values below were re-read from the official pages, not only cited from
committed captures.

| Official source read live this session | URL |
|---|---|
| NBA.com Standings | https://www.nba.com/standings |
| NBA.com Schedule (Week 5, Nov 16–22) | https://www.nba.com/schedule?date=2026-11-16 |
| NBA Official Injury Report index | https://official.nba.com/nba-injury-report-2026-27-season/ |
| Official injury-report PDF, 11/16 **01:00 PM ET** | https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-16_01_00PM.pdf |

The injury index lists 11/16 releases from 12:00 a.m. ET through **1:00 p.m. ET**. The committed
`refresh_2026-11-16` capture is the **09:15 / 09:30 a.m. ET** release — a ~3.5-hour freshness gap
against the freshest official release (finding F-3CD-01 below).

## 1. Headline numbers re-derived independently — all MATCH the published v4 model

Re-derived from the committed official-finals pool (183 history games + 5 eleven-fourteenth finals
+ 9 eleven-fifteenth finals = **197 games**) by the script
`verified/session-3cd85a22-live/verify.py`, then compared to `data/v4/model.json`.

| Quantity | Re-derived this session | Published (v4) | Match |
|---|---|---|---|
| Games in pool | 197 (1 neutral excluded → 196) | 197 / 196 | ✅ |
| Home wins (non-neutral) | 102 | 102 | ✅ |
| Home-win rate | **0.5204** | 0.5204 | ✅ |
| Margin mean (pts) | 1.689 | 1.689 | ✅ |
| Margin sd (pts) | **16.987** | 16.987 | ✅ |
| Pinned HCA (pts) = sd·Φ⁻¹(p) | **0.869** | 0.869 | ✅ |
| ρ(home margin, total), n=196 | **−0.038** | −0.038 | ✅ |

The home-court advantage is **pinned**, not fitted: `h = sd(home margin) × Φ⁻¹(measured home-win
rate)`. The re-derivation reproduces the published value exactly, so the published HCA is a
restatement of an official count, as claimed. Sources: the committed official finals
(`data/raw/history/games_*.json`, `data/raw/capture_2026-11-15/results_2026-11-14.json`,
`data/raw/refresh_2026-11-15/results_2026-11-15.json`), each of which records its own official
source URL.

## 2. Standings — committed capture vs live official: **30 / 30 MATCH**

The committed `refresh_2026-11-16` standings (retrieved `2026-11-16T14:30:00Z`, 09:30 ET) were
compared field by field (W-L, HOME, ROAD, NEUTRAL, OT, LAST10) against the live
[nba.com/standings](https://www.nba.com/standings) read at `2026-11-16T18:23:30Z`.

**Result: 30 of 30 clubs identical**, overall record and every split. The committed capture is a
correct point-in-time read of the official standings; nothing drifted between the 09:30 ET capture
and the 13:23 ET re-read. (The league identity `ΣW = ΣL = 197` also holds in the committed capture's
own `checks` block.)

## 3. Slate — committed capture vs live official: **29 / 29 MATCH**

The committed `slate_2026-11-16_to_11-19.json` (29 games, IDs `0022600245`–`0022600273`) was
compared field by field (game id, date, away, home, tip time, arena) against the live
[nba.com/schedule](https://www.nba.com/schedule?date=2026-11-16) read this session.

**Result: 29 of 29 games identical.** Window 11/16 → 11/19: 8 games on 11/16, 5 on 11/17, 12 on
11/18, 4 on 11/19. The committed slate is a correct read of the official schedule.

## 4. Injury report — freshness gap and two genuine status changes

The committed injury transcript is the **09:30 a.m. ET** release (70 player records, retrieved
`2026-11-16T14:52:00Z`). The freshest official release is the **01:00 p.m. ET** PDF (77 rows
captured this session, of which 75 are player rows; 2 rows are `NOT YET SUBMITTED` for BOS and PHX).

| Measure | Committed (09:30 AM ET) | Live official (01:00 PM ET) |
|---|---|---|
| Release stamp | 2026-11-16 09:30 AM ET | 2026-11-16 01:00 PM ET |
| Retrieval stamp | 2026-11-16T14:52:00Z | 2026-11-16T18:23:30Z |
| Player records | 70 | 75 |

**F-3CD-01 — Injury freshness gap.** The published/committed injury capture is the 09:30 a.m. ET
release; the official index had moved to the 01:00 p.m. ET release by this session's retrieval.
**23 player rows** appear in the 1:00 p.m. release that were not in the 09:30 a.m. capture — teams
that filed after 09:30 a.m. (the CHI/CLE, MEM/WAS, HOU/MIA, PHI/BKN blocks grew). This is the same
class of gap the brief's "store every injury PDF with its timestamp and diff consecutive reports"
item is meant to catch; the scheduled job has not been re-run since the 09:30 capture.

**F-3CD-02 — Two genuine status changes between the two releases.**

| Matchup | Team | Player | 09:30 AM ET | 01:00 PM ET |
|---|---|---|---|---|
| CHI@CLE | CLE | Tyson, Jaylon | Questionable | **Doubtful** |
| HOU@MIA | MIA | Larsson, Pelle | Questionable | **Doubtful** |

Both move *toward* absence. Source: the two official PDFs linked in §0.

**F-3CD-03 — Team-attribution defect in the committed 09:30 AM capture (confirmed).** Five
Washington Wizards players — `Jerome, Ty`, `Pippen Jr., Scotty`, `Post, Quinten`, `Saunders,
Richie`, `Stewart, Isaiah` — are recorded under team **MEM** in the committed `09:30 AM` transcript
but under **WAS** in the official 1:00 p.m. release. This is the block-position attribution artefact
already flagged as IR-6; the live release resolves it. The committed capture is therefore **wrong on
the team column for these 5 rows**, not merely stale.

**F-3CD-04 — GSW block capture-quality (confirmed, F-V4-06 class).** In the committed 09:30 AM
transcript the six Golden State Warriors rows carry **blank** status and reason cells (the capture
recorded the flag `F-V4-06 extraction prints only Player | X | Y; X/Y not assigned to a column`).
The 1:00 p.m. release captures them (Curry/Moody/Porzingis/Williams = Out, Santos = Questionable,
Butler III = reason captured, status cell still blank in the parse). The blanks in the committed
capture are an extraction artefact, not absent designations.

## 5. Irregularities raised by this session (for the Flagged for Review page)

| ID | Finding | Status | Source |
|---|---|---|---|
| F-3CD-01 | Committed injury capture is the 09:30 a.m. ET release; 23 player rows were added by the official 01:00 p.m. ET release. The scheduled refresh has not advanced the capture. | open — publish | [injury index](https://official.nba.com/nba-injury-report-2026-27-season/), [01:00 PM PDF](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-16_01_00PM.pdf) |
| F-3CD-02 | Two status changes between releases: CLE Tyson (Q→Doubtful), MIA Larsson (Q→Doubtful). | open — publish | same PDFs |
| F-3CD-03 | Committed 09:30 AM transcript mis-attributes 5 WAS players to MEM (block-position artefact, IR-6). | open — publish | [01:00 PM PDF](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-16_01_00PM.pdf) |
| F-3CD-04 | Committed 09:30 AM GSW block has blank status/reason (F-V4-06 extraction artefact). | open — publish | [01:00 PM PDF](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-16_01_00PM.pdf) |

None of these blocks publication. They are published here with their official source links for
post-launch review, per the brief.

## 6. What this session did **not** verify, and why

* **The live GitHub Pages site is serving the stale v2 tree.** The live index still reads the
  11/15 window and the "2026-11-15 06:15 AM ET" injury revision, while the committed `site/`
  contains the v4 11/16 capture. PR #98 (`arena/fe0ffa49-nba2`) refreshes the published tree to
  11/16; it is open and not merged, so the live URL has not advanced. This session did **not** merge
  or rebuild it (that is PR #98's scope). Confirmed by reading the live URL, not assumed.
* **Injury PDF bytes / SHA-256 of the file.** `fetch_page` returns the PDF's **text**, not its
  bytes, and bash egress to `ak-static.cms.nba.com` is blocked. The capture therefore records the
  official PDF URL, the revision stamp and this session's retrieval stamp, plus a content hash of
  the transcribed text — but **not** the original file hash. This is the same IR-2 / F-V4-01
  limitation; it needs a runner with direct network access, not a guess.
* **Market prices / player props.** No licensed odds or prop feed is reachable; nothing here is a
  bettable edge, and the site holds every stake at 0.00 by policy (gate G6).

## 7. How to reproduce

```bash
python3 verified/session-3cd85a22-live/verify.py
# writes verified/session-3cd85a22-live/verification_results.json
```

The script reads only committed captures plus the fresh live captures stored in the same directory
(`live_standings_2026-11-16.json`, `live_slate_2026-11-16.json`,
`live_injury_report_2026-11-16_0100PM.json`), which each record their official source URL and
retrieval stamp. No official value is hard-coded beyond the transcribed live captures, which are
themselves the official read.
