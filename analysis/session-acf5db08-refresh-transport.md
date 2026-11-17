# RQ-8892-01 — the rolling refresh could not read the official pages. Measured, then repaired.

**Session:** `arena/acf5db08-nba2` · **Date:** 2026-11-17 UTC · **Branch:** `arena/acf5db08-nba2`
**Scope:** `nba2/v2/refresh.py`, `nba2/pipeline/refresh.py`, `nba2/v2/test_refresh_pages.py`,
`nba2/tests/test_finals_pages.py`, `.github/workflows/capture-fixtures.yml`,
`data/raw/page_fixtures/**`, this file, and the board record in `COORDINATION.md`.

---

## 1. What was actually wrong (measured on a runner, not inferred)

The nightly job had failed six consecutive scheduled runs (43631377045 … 44107633323).
`data/raw/refresh_verdict.json` recorded `rolling=failure, finals=failure` but no reason: the
job logs and artifacts are served from hosts this repository's review loop cannot reach, so
nobody had read them. The cause in circulation — "stats.nba.com is blocked" — was itself an
inference from a **development sandbox**, where all nba.com egress is TLS-reset.

So the first thing this session did was measure the question from the environment that
matters. `.github/workflows/capture-fixtures.yml` now fetches every page the refresh needs
**from a GitHub-hosted runner** and commits the bytes (gzip, with the SHA-256 and byte length
of the original response) plus a manifest and a transport probe:

* `data/raw/page_fixtures/manifest.json` — one row per page: URL, HTTP status, bytes, ms, SHA-256.
  Run: https://github.com/wingbangboozle1-lang/NBA2/actions/runs/44144007879
* `data/raw/page_fixtures/transport_probe.json` — each endpoint fetched with **two** header sets.

Two findings, both recorded rather than assumed:

**(a) stats.nba.com and cdn.nba.com are unusable from a runner — with every header set.**

| endpoint | repo headers (Chrome UA + `x-nba-stats-origin`/`token`) | plain UA |
|---|---|---|
| `stats.nba.com/stats/leaguestandingsv3` | timeout (20.1 s) | timeout (20.1 s) |
| `stats.nba.com/stats/leaguedashteamstats` | timeout (20.1 s) | timeout (20.1 s) |
| `stats.nba.com/stats/scoreboardv2` | timeout (20.1 s) | timeout (20.1 s) |
| `cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json` | HTTP 403 | HTTP 403 |
| `www.nba.com/standings` | **HTTP 403** | **HTTP 200, 224 760 bytes** |

**(b) The repository's own User-Agent was blocking the pages that were reachable.** The
Chrome-mimicking UA `nba2/v2/refresh.py` sent measured **403** on `www.nba.com/standings` in
the same run where a plain, self-identifying UA measured **200**. The previous code sent that
UA to the one host that would have answered. (The header fix alone is not the whole repair:
the JSON hosts fail either way — but it is why the failure looked like "the league blocks us".)

Other hosts, re-measured and recorded: `official.nba.com` injury index and
`ak-static.cms.nba.com` injury PDFs 200; `data.nba.net` fails TLS hostname verification;
`statsdmz.nba.com/js/data/widgets/standings.json` 404.

**What the pages actually contain** (from the committed bytes, not from memory):

* `www.nba.com/games?date=YYYY-MM-DD` is **server-rendered**: its `__NEXT_DATA__` payload
  carries every game of that date — 10-digit game id, home/away tricode, final score,
  **quarter scores**, status, tip time, a per-game official link
  (`https://www.nba.com/game/<away>-vs-<home>-<id>`), and each club's season W/L beside the game.
* `www.nba.com/standings` and `www.nba.com/schedule?date=` are **shells**: identical bytes for
  every date, no rows. `www.nba.com/teams` is a shell too.
* The standings page *does* print, server-side, its navigation team list: 30 clubs with
  tricode, club name, official team id (in the logo URL) and **division**. That is a real
  official mapping and it is read, not assumed.

---

## 2. What was changed

### `nba2/v2/refresh.py` (rolling refresh: schedule, standings, team stats, injuries)

* **Transport headers** now use the measured User-Agent, verbatim, and a 0.6 s pause between
  requests (the season scan reads ~60 pages; bursting earns a 403 that is indistinguishable
  from a blocked host).
* **Slate** (today … today+3) and **finals** (7-day lookback) are parsed from the
  `games?date=` payload. Finals now carry **quarter scores**, which the old JSON path never
  captured even though the brief asks for them, plus an OT count; a quarter row that does not
  sum to the printed final raises rather than publishes.
* **Standings** are derived, because the standings *table* is client-rendered from the
  unreachable host. Inputs are official: every regular-season final of the season to date
  (60-day scan, `seasonType == "Regular Season"`) plus the club/division list read from
  `nba.com/standings`. Each club's derived record is then **cross-checked against the W/L the
  league prints beside that club's most recent game** — a mismatch raises. The conference
  column stays **blank and flagged**: the league prints divisions, not conferences, and no
  reachable official page was measured to group clubs by conference.
* **Injury index**: the newest release is chosen by the timestamp in the filename. The index
  lists releases **oldest first**, so the old `links[0]` picked the *oldest* release of the
  day: on the committed 2026-11-17 index (52 releases) it returned
  `Injury-Report_2026-11-17_01_00AM.pdf` where the newest is
  `Injury-Report_2026-11-17_12_45PM.pdf` — a banner up to twelve hours stale.
* **Team stats**: the three official pages answer 200 but carry no rows (the browser loads them
  from the unreachable host). Each is recorded as `unavailable` with the measured reason and
  the official URL. **No row is invented.** This is the one surface of the four that still
  cannot be refreshed from a runner, and it is published as such rather than hidden.
* `gate_slate` accepts `www.nba.com/games?date=` as well as `/schedule?date=`: the row must
  cite the page it was actually read from. Nothing else about the five gates changed, and all
  five still fail closed.

### `nba2/pipeline/refresh.py` (finals → settlement)

`FINALS_SOURCES` gains `https://www.nba.com/games?date={date}` as the **first** source, with a
parser producing the same record shape plus quarter scores. Order matters: the reachable page
answers in ~0.3 s, so a nightly run no longer spends 25 s per date waiting on a timeout before
falling through. The JSON endpoints stay as later fallbacks; `cmd_finals` still returns 3 only
when **every** source fails at the network level, and 4 on a schema change.

### Tests

* `nba2/v2/test_refresh_pages.py` — 18 tests. Most parse the **committed fixture bytes** and
  assert the manifest's SHA-256 still matches; synthetic data is used only for the cases the
  real season cannot produce (a game day the scan lost, an out-of-order injury index, a
  quarter row that does not add up) and is labelled as such in the file.
* `nba2/tests/test_finals_pages.py` — 9 tests on the same principle.
* `nba2/v2/test_refresh_gates.py` — exactly one test changed: it mocked `http_json` against the
  dead transport. It now mocks the new one and asserts the same rule (a fetched date counts as
  coverage even with no games). The 12 other gate tests are untouched.

---

## 3. Verification performed (all on a GitHub-hosted runner)

`python3 -m nba2.v2.refresh --check-only`, live, run 44144007879 —
`data/raw/page_fixtures/refresh_checkonly.txt`:

```
[UNAVAILABLE] team_traditional / team_advanced / team_opponent — recorded, not invented
[PASS] freshness/finals:    51 finals across 7 calendar dates
[PASS] freshness/standings: 30 clubs; 205 wins / 205 losses
[PASS] freshness/injuries:  revision 2026-11-17 12:45 PM ET retrieved 2026-11-17T17:52:54Z
[PASS] freshness/slate:     30 games in 2026-11-17..2026-11-20, 30 unique ids; 4/4 dates fetched
[PASS] provenance:          5 documents scanned — every row carries a source URL
exit=0
```

Two independent corroborations of the derived standings: the league's own books balance
(205 W = 205 L), and **205/205 is exactly the league total the 2026-11-17 official capture
recorded** (`analysis/session-8892d20c-capture.md`), reached by a different route.

`python3 -m nba2.pipeline.refresh --finals 2026-11-16`, live, same run:

```
[finals 2026-11-16] expecting 8 sealed-window games
[finals 2026-11-16] wrote finals_2026-11-16.json: 8 games from
  https://www.nba.com/games?date=2026-11-16 (0 window games not in payload)
exit=0
0022600245 ORL 115 @ BOS 105  q [20,30,25,40] [17,24,36,28]
0022600247 MEM 136 @ WAS 120  q [33,26,42,35] [35,34,18,33]
0022600246 CHI 115 @ CLE 126  q [31,17,31,36] [25,32,31,38]
...
```

Locally: 164 v2 tests + 88 pipeline tests pass; the full rebuild chain
(`build_site_data → build_site → backtest → v2 → settlement_page → v3 → v4 → v5 → v6`)
reproduces the committed `site/` tree exactly (that rebuild also regenerated
`site/methodology.html`, because the page counts the repository's tests at build time and this
branch adds 27).

---

## 4. Sources

| Fact | Official source | Evidence |
|---|---|---|
| 2026-27 standings page is a shell; team list is server-rendered | https://www.nba.com/standings | `data/raw/page_fixtures/standings.html.gz` (30 clubs parsed, 6 divisions × 5) |
| Slate, finals, quarter scores, per-game records | https://www.nba.com/games?date=YYYY-MM-DD | `data/raw/page_fixtures/games_*.html.gz`, `future_games_*.html.gz` |
| Newest injury release | https://official.nba.com/nba-injury-report-2026-27-season/ | `data/raw/page_fixtures/injury_index.html.gz` (52 releases; newest `2026-11-17_12_45PM`) |
| Team-stat pages carry no rows server-side | https://www.nba.com/stats/teams/traditional (and opponent, advanced) | `data/raw/page_fixtures/team_*.html.gz` — `pageProps` holds only `layout` |
| Which hosts answer a runner | measured in-run | `data/raw/page_fixtures/transport_probe.json`, `manifest.json` |
| Prior reachability measurement | `data/raw/egress_probe.json` (runner, 2026-11-17T14:28:28Z) | committed |

---

## 5. Flagged — carried forward, not fixed here (they do not block the merge)

1. **The three official team-stat pages cannot be read from a runner.** They are
   client-rendered from stats.nba.com, which times out with every header set. The refresh
   records the surface as unavailable rather than inventing rows. This blocks the brief's
   "re-read the three official team-stat pages and re-cut the model inputs" from ever running
   on the schedule; it is only doable through a platform page-fetch (as
   `data/raw/refresh_2026-11-17` was). **Owner decision needed.**
2. **RQ-8892-02 (the model re-cut to the 2026-11-17 capture) is untouched by this session.**
   It needs `nba2/v2/official.py`, `nba2/v2/report.py` and the v3/v4/v5 repoint — files owned
   by other sessions — and the seven ordered steps in `analysis/session-8892d20c-capture.md`
   §4. Repairing the transport is what makes that re-cut *possible*; it is not a substitute.
3. **The conference column is blank by choice.** No reachable official page was measured to
   group clubs by conference; deriving it from the division names would be an inference.
4. **The arena column of the slate is blank.** `games?date=` does not print it, and no other
   reachable official source was measured to.
5. **The fixture workflow's bot commits re-trigger this branch's pull_request workflows**, and
   runs triggered by a bot commit sit at `action_required` awaiting an approval. The workflow
   therefore commits evidence only on a deliberate `workflow_dispatch`; ordinary pushes report
   to the job summary instead. Worth knowing before anyone re-enables it on push.
