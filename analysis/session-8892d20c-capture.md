# Session `arena/8892d20c-nba2` — capture, diagnosis, and the re-cut that is still owed

Written 2026-11-17. Every claim below is either reproduced by a command in this repository or
fetched from an official NBA page this session. Where neither is true, it says so.

## 1. What was wrong when this session started

Read from the repository and from GitHub, not assumed:

| Fact | Evidence |
|---|---|
| Rebuild was already a fixed point | `python3 -m nba2.v2` (24 pages) → `nba2.v2.check` "0 structural, 0 semantic"; `nba2.v3` "7 pass / 1 fail, publishable"; `nba2.v4` "0 surface-wall, 0 numeric"; `nba2.v5` "8/8"; `git status` clean |
| Published snapshot 3 days stale | `tools/crosscheck_site.py` → `CC-FRESH-01 FAIL: 3 day(s) old` |
| README counts stale | same check → `CC-DOC-01 FAIL: 1423 vs 1436 rows, 70 vs 79 tests` |
| Nightly job failed 6/6 scheduled runs | `gh run list --workflow=refresh.yml` → 43631377045, 43725486781, 43751588814, 43903704042, 43939889279, 44107633323, all `failure` |
| The failing surface is `rolling` | `data/raw/refresh_verdict.json` → `injuries=success, finals=failure, rolling=failure, v4=success` |

## 2. The cause of the nightly failure, measured

`nba2.v2.refresh` fetches three of its four surfaces from `stats.nba.com` JSON endpoints. Run
locally it dies on the first one:

```
RuntimeError: fetch failed after 3 tries:
https://stats.nba.com/stats/leaguestandingsv3?LeagueID=00&Season=2026-27&SeasonType=Regular+Season:
<urlopen error TLS/SSL connection has been closed (EOF) (_ssl.c:992)>
```

That is a *sandbox* result and on its own proves nothing about a runner — which is why the
repository already carries an egress probe measured **on a GitHub runner**
(`data/raw/egress_probe.json`, 2026-11-17T14:28:28Z):

| Endpoint (GitHub runner) | Result |
|---|---|
| `official.nba.com/nba-injury-report-2026-27-season/` | **200**, 41,174 bytes |
| `ak-static.cms.nba.com/.../Injury-Report_2026-11-16_01_00PM.pdf` | **200**, 95,928 bytes |
| `www.nba.com/schedule?date=2026-11-16` | **200**, 232,453 bytes |
| `www.nba.com/standings` | **200**, 254,549 bytes |
| `statsdmz.nba.com/pdfs/20261115/20261115_INDPHI_book.pdf` | **200**, 146,951 bytes |
| `cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json` | **403** |
| `stats.nba.com/stats/scoreboardv2?...` | **TimeoutError** after 25.2 s |

**Conclusion, and it is the useful one:** every surface the brief asks for is reachable from a
runner; the *transport* the refresh uses for three of them is not. The repair is to parse the
rendered official pages (schedule, standings, `/stats/teams/...`) rather than the JSON API —
exactly the path this session's capture used. It is not patched here because
`nba2/v2/refresh.py` is inside a finished session's scope; it is logged as request RQ-8892-01.

## 3. What was captured, and what proves it

`data/raw/refresh_2026-11-17/`, written by `audit/session-8892d20c-nba2/write_capture.py`:

| File | Rows | Source |
|---|---|---|
| `standings_2026-11-17.json` | 30 clubs, all ten printed columns | `nba.com/standings` |
| `team_stats_2026-11-17.json` | 30 clubs × 9 fields across 3 pages | `/stats/teams/traditional`, `/opponent`, `/advanced` |
| `slate_2026-11-17.json` | 5 games (T+0) fully transcribed | `nba.com/schedule?date=2026-11-17` |
| `capture_index.json` | the method, the unread items and why | — |

The writer refuses to write if any of these fail:

1. 30 clubs in each artefact, identical club sets.
2. Every club's home + road + neutral splits reproduce its own W-L.
3. League wins equal league losses — **205 / 205**.
4. Every club's GP on the traditional page equals its W+L on the standings card.
5. Points scored equals points allowed league-wide within the 0.1 rounding bound —
   **46,669.6 vs 46,668.8, diff 0.8, bound 41.0**.
6. No duplicate game id, and no club twice on tonight's slate.

All six pass. `margin_vs_netrtg_max_abs` is also published: **0.85 pts/game** (ORL −0.85,
NYK +0.64, DET +0.53). Those are the *official pages* disagreeing with each other under
independent rounding, not a transcription error; the residual table is on the site and a value
above 1.5 fails the capture. Nothing was adjusted to make the three pages agree.

Corroboration that this is the right week: the 11/16 capture records 197 league games
(30 clubs, 394 team-games); this capture records 205 (410 team-games) — a delta of 8 games,
which matches the eight games listed on the official 11/16 card.

## 4. The gap this session deliberately did not close

**The published model is still dated 2026-11-15 while a verified 2026-11-17 capture sits in the
tree.** That is deliberate.

`nba2.v2.official.TEAMS` is a static transcription consumed by v2 (team table, two estimators,
lines, picks), v3 (its own `official.py`), v4 (`capture.py` transcribes its own rows) and v5
(reads v4's injury directory by path). A v2-only promotion would move one surface and leave the
published pages on four different dates — the defect the README already names. Two further
reasons it is not a copy-paste:

- `nba2/v2/report.py` reconstructs every W-L from `data/raw/history/games_*.json` and asserts no
  club *exceeds* the official card. A fresher card makes every reconstructed record fall short by
  more than the old 19-game hole, so the check's arithmetic has to change from "≤" to "= card
  minus the recorded hole", not be silently retuned.
- `slug`-wide arithmetic that reads `TEAMS` must be re-run, not assumed: `integrity()`
  (home-win rate, which pins HCA), `home_win_rate_se()`, and the luck z-scores in
  `nba2/v2/model.py` all move when W/L and PF/PA move.

### The cut, in order, for whoever does it

1. Re-run `audit/session-8892d20c-nba2/write_capture.py`; require `selftest CLEAN`.
2. Replace `nba2/v2/official.py::TEAMS` field by field from
   `data/raw/refresh_2026-11-17/team_stats_2026-11-17.json` and
   `standings_2026-11-17.json`; bump `AS_OF`, `RETRIEVED_AT_UTC`, `RETRIEVED_BY`, and
   `WINDOW_START`/`WINDOW_END` to the new anchor (+3 days).
3. Disclose the PF/PA re-basing explicitly: the old PF/PA were *summed from committed finals*;
   the new ones are the official per-game page values. Say which is which on the page rather
   than letting the definition change quietly.
4. Update `nba2/v2/report.py`'s reconstruction assertion to compare against the card minus the
   committed-finals hole, and print that hole.
5. Re-run every downstream surface in CI order (`v2 → v2.check → settlement_page → v3 →
   v3.check → v4 → v4.check → v5 → v5.check`), plus each suite's tests.
6. Repoint `nba2/v3/official.py`, `nba2/v4/capture.py` and the v5 window in the same change —
   otherwise the dates diverge again.
7. Only then is `CC-FRESH-01` legitimately passable.

## 5. Irregularities logged

| ID | Severity | What |
|---|---|---|
| F-059 | high | Nightly refresh 6/6 failures; cause measured as transport, not sources (RQ-8892-01). |
| F-060 | medium | Published 11/15 snapshot vs a verified 11/17 capture in the tree; re-cut owed, spec above. |
| F-061 | low | Three official team-stat pages do not reconcile exactly (max 0.85 pts/game); residual published per club. |

## 6. Reproduce this session

```bash
python3 audit/session-8892d20c-nba2/write_capture.py     # rewrite the capture, run the self-test
python3 -m nba2.v2 && python3 -m nba2.v2.check           # 25 pages; 0 structural / 0 semantic
python3 -m nba2.settlement_page && python3 -m nba2.v3 && python3 -m nba2.v3.check
python3 -m nba2.v4 && python3 -m nba2.v4.check           # 8/8 gates
python3 -m nba2.v5 && python3 -m nba2.v5.check           # 8/8 gates
python3 tools/check_links_all.py                         # all internal links
python3 tools/crosscheck_site.py                         # 97 checks
```
