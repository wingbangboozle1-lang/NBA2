# Line-by-line repo review — session `arena/fe0ffa49-nba2`, 2026-11-16

Branch `arena/fe0ffa49-nba2`, base `main` @ `32019ac`. Every finding below was produced by
reading the working tree, running the code, or reading an official page — **not** by reading
a prior session's summary of itself. Findings are ordered by cost-if-ignored.

The review question is not "is the number plausible". It is: **can this number be traced, line
by line, to an official page committed in this repository, and will it still be true tomorrow
morning when the results feed appends nine more finals?**

---

## 1. Verified true, line by line

| Claim | How it was checked | Result |
|---|---|---|
| 197 official finals, 2026-10-20 → 2026-11-15 | `data/raw/history/games_*.json` (25 dated files) | 197 rows, 0 duplicate `game_id`, ΣW = ΣL = 197 |
| Standings W/L | rebuilt from the 197 finals vs the live 11/16 standings capture | 30/30 identical |
| Home/road splits | same rebuild | 28/30 identical; both exceptions (DEN, IND) are the NEUTRAL column and are documented in `capture_2026-11-16/standings_2026-11-16.json` under `cross_check.mismatches` |
| Window 2026-11-16 → 2026-11-19 = 29 games | `capture_2026-11-16/slate_2026-11-16_to_11-19.json` | IDs contiguous `0022600245`–`0022600273`; 8 + 5 + 12 + 4 |
| Injury release the site prices from | `Injury-Report_2026-11-16_09_15AM.pdf` | 57 player rows + 15 NOT YET SUBMITTED; 11/16 and 11/17 only |
| v3 pre-tip seal | `data/v3/ledger/sealed-2026-11-15.json` | 34 rows, sha `34e144c635b83b8991a61e8ca26c164bdfc6c6679b6a62220175debad2e35e91`, sealed 2026-11-15T11:41:00Z |
| σ of the game total | `nba2.v2.model` | 19.0829 over 197 de-duplicated finals |
| Site integrity | `nba2.v2.check`, `nba2.v3.check`, `nba2.pipeline.lint`, `tools/check_links_all.py` | 0/0, 0/0, 1427 rows across 50 tables all sourced, 5981 internal links OK |
| Test suites | v2 136, v3 64, v1 79, backtest 49 | all OK |

## 2. Defects found and fixed in this session

These are the reason this review exists. Each one is a case where the repository **said** one
thing and **did** another.

**RR-29 — the v3 ledger seal was not a seal.** `nba2/v3/ledger.py::seal()` recomputed and
overwrote the seal file on *every* build. Because the committed finals history grows every
game night, every v3 margin for the already-Final 11-15 slate moved, and the build silently
rewrote the pre-tip commitment to match. A record that re-issues itself after the result is
known proves nothing. Fixed: `seal()` is now **write-once**; on divergence it appends to an
append-only `data/v3/ledger/seal-divergence-<date>.json` and returns `{"rewritten": False}`.
The authentic 11-15 seal was restored from git *before* the fix, so the published seal is the
original, not a re-issue.

**RR-30 — the v2 pre-registration files re-froze themselves.** `nba2/v2/build.py` re-stamped
`frozen_at_utc` and `frozen_by` with the current build time on every run, so a file whose
entire purpose is to be frozen before the first bet drifted daily. Fixed: first freeze wins;
a later content difference is recorded inside the file as a `content_changed` note rather
than moving the freeze. Verified by `git checkout data/v2/prereg/` followed by two rebuilds:
`git diff data/v2/prereg/` is empty.

**RR-31 — σ double-counted five games.** `_game_totals()` concatenated the history glob with
the 11-15 capture's results rows. The five 11-14 finals lived in both, so
`n_finals_for_sd()` returned 202 against a league that had played 197. Rewritten as a
`game_id`-keyed union that **raises** on a genuine score disagreement between sources rather
than silently preferring one.

**RR-32 — five official finals were in the repository and invisible to the model.** They had
been captured into `data/raw/capture_2026-11-15/results_2026-11-14.json` but never placed
under the `data/raw/history/games_*.json` glob that every backtest, rating and settlement
reads. The standings implied 197 league games while the model saw 192. Corrected by
transcription (no value re-read, no value invented); the source file is named in the new
history file's `meta`.

**RR-33 — a `None` reaching the page renders as an unexplained blank.** `esc(None)` returns
`""`, so a missing value prints as an empty cell with no flag. The lint gate catches it one
step downstream, which is why this survived — but the gate reports the symptom, not the
cause. The injury tables now route every status/reason through `_status_cell` /
`_reason_cell`, which print an explicit `not printed on the row (FLAG-FE0-INJ-NOREASON…)`.
The general `esc()` behaviour is left as-is and recorded as **RR-23, open**.

**RR-34 — the front page asserted counts it should have measured.** "188 official finals",
"34-game window", "167 finals", "0/30 teams outside luck noise" were literal strings in
`build.py`. Each became false the moment the snapshot moved, and nothing failed. All are now
read from the model (`integ['games']`, `len(lines)`, `lab['meta']['n_scored']`, gate G9's
`n_lucky`).

**RR-35 — the injury banner and the injury table could name different releases.** The banner
read one hard-wired transcript while `official.py` carried a newer one. `capture2` now
selects the **freshest committed transcript** by its own `retrieved_at_utc`, so the banner
and the rows can never disagree.

**RR-36 — the v3 tree published a frozen window beside the live window with no label.** v3's
window is 2026-11-15 → 11-18 and *must* stay that way (see RR-29: its ledger is sealed for
that window). A reader landing on `slate.html` from the dashboard would have seen yesterday's
slate with no explanation. Fixed with a self-updating banner that names the newer committed
window and links to it, plus a `— v3 frozen snapshot —` divider in the nav.

**RR-37 — the tests encoded the snapshot, not the invariant.** 188 finals, 172 predictions,
34 slate games, 101 injury rows, 64 ledger rows were all literals in test bodies. They are
now derived: `len(games)`, "every game where both clubs had already played must carry a
prediction", "the count of distinct `game_id`s in the history glob", "the row count of the
transcript actually loaded".

**RR-38 — the staleness detector compared a live table against a dated fixture without
advancing the fixture.** It applied only the five 11-14 finals, so the nine 11-15 finals
landed as `UNEXPLAINED` the moment they were committed — 18 rows of "unexplained drift" that
was simply games the fixture predates. It now applies **every** official final played after
the fixture's last date, unioned by `game_id`: 30/30 match, 0 unexplained.

## 3. Irregularities recorded for the owner (not fixed — each needs a decision)

| ID | Irregularity | Why it is recorded rather than fixed |
|---|---|---|
| I-FE0-01 | Two `fetch_page` probes of the Pages host disagree (v1 root vs v2 `site/`) | Contradicts FLAG-PAGES-01 / F-033. `.github/workflows/pages.yml` uploads `site/`, so v2 is what *should* be served, but this session will not assert a conclusion from two conflicting probes. Re-probe before writing it down. |
| I-FE0-02 | `0022600240` DAL@BOS has `away_quarters: null` with `status: "final"` | Quarter sums are guarded, never back-solved. The cell stays null. |
| I-FE0-03a | `stats/teams/traditional` and `/opponent` were not re-read this session | PF/PA are therefore summed from the 197 official finals and divided by games played — exact, but not the same quantity the stats page prints. Logged in `official.py`'s header. |
| I-FE0-03b | The 11-16 injury PDF lists Ja Morant under **Portland** | Printed verbatim as the PDF has it; not silently corrected. |
| I-FE0-07 | `data/raw/pdf/` is empty — no injury PDF bytes are stored, only labelled text transcripts | Bash egress to `ak-static.cms.nba.com` returns HTTP 000; the binary cannot be retrieved from this sandbox. Requirement 5 cannot be met here. |
| F-043 | The nightly ingest fails at the official-finals fetch | `gh run view --log` returns EOF from this sandbox, so the failure is not diagnosable here. |

## 4. What is still not verifiable, and stays blank

- **No market price feed.** Every stake on the site is 0.00 units and the gate that forces it
  is printed on the row. Gates G-02, G-05, G-09 cannot pass.
- **No player-level official input for props** (R-007). The props page publishes structure and
  the gate, not a projection.
- **No 11-18 or 11-19 injury rows exist in any published report.** Teams file by 5 p.m. local
  the day before. Those cells are blank and flagged — never estimated.
- **No per-possession data**, so garbage time, foul trouble and late-game flow remain
  listed as known-missing rather than modelled.

## 5. Suggestions added

See `suggestions/SUGGESTIONS.json` entries **S-55 … S-59** and the site's
`decision-queue.html`. They are ordered by how much they unblock, not by effort.
