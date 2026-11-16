# Session `arena/41bd6ce8-nba2` — per-player game logs, gated and automatable

**Date** 2026-11-15 · **Branch** `arena/41bd6ce8-nba2` · **Base** `main` @ PR #76, rebased
onto #79
**Scope owned** `nba2/v4/**`, `data/raw/capture_2026-11-15-41bd6ce8/**`,
`.github/workflows/player-capture.yml`, `audit/2026-11-15-41bd6ce8/**`,
`requirements/REQUIREMENTS.json` (status / `how` only), `COORDINATION.md` (append-only).

## The gap this session closed

The brief asks for per-player game logs — minutes, points, rebounds, assists and the opponent —
for at least the players who appear on an injury report. Before this session the repository held
**one** game (gid 0022600231) and no per-player season baselines, and R-102 ("capture the
minute/usage column from a licensed or official provider") was recorded as *blocked*.

## What the session measured

| Question | Answer | Evidence |
|---|---|---|
| Is the data reachable? | **Yes, per player** — `nba.com/stats/player/{id}/boxscores-traditional` renders Match Up, W/L, MIN, PTS, REB, AST, STL, BLK, TOV, +/- and the game id | 48 rows captured; `audit/2026-11-15-41bd6ce8/verification-log.md` §1 |
| Is there a league-wide table? | **No.** `nba.com/stats/players/traditional` renders but prints "No data available"; `cdn.nba.com/static/json/**` returns HTTP 500 | `nba2/v4/official.py::UNREACHABLE` |
| Is the capture correct? | mean of the captured rows == the PPG/RPG/APG the same page prints in the player header, for all 5 players (gate G-41-02, ±0.05) | `python -m nba2.v4` → 40 gates, 40 pass |
| Is there a better source? | **Yes** — the official gamebook PDF, one per game, all players: 193 rows / 18 clubs for 2026-11-13. Found by `arena/f8f8f2b8-nba2`, which merged while this session ran | their `data/raw/capture_2026-11-15/gamebooks_2026-11-13.json` |
| Can the sandbox fetch any of it in code? | **No** — no outbound network; captures go through the platform page-fetch tool. GitHub Actions can | smoke run records `URLError: TLS/SSL connection has been closed` |

R-102 is therefore not blocked any more; it is *partial*, and the reason is page budget, not
access.

## Reconciliation with `arena/f8f8f2b8-nba2`

Both sessions worked the same brief line on the same evening. Their capture answers the shared
question better (193 rows, 18 clubs, primary gamebook PDFs) and merged first, so this session
**withdrew** its three pages and its duplicate transcription of the 06:15 PM release rather than
publish a second `player-logs.html` and a second `injury-diff.html` under the same names — the
failure mode the repository already warns about ("shipping six versions of the same dashboard is
how a reader learns not to trust any of them"). Their v3 pages were restored byte-for-byte from
`main`.

What this session kept, because nothing else in the repo does it:

| Kept | Why it is not a duplicate |
|---|---|
| `data/raw/capture_2026-11-15-41bd6ce8/{player_gamelogs,rosters}.json` — 48 season-long rows for 5 players, plus official player ids | the gamebook capture is one night per file; this is each player's whole season to date |
| `nba2/v4/gamelog.py` — the gates (G-41-01…06) | the identity check "mean of captured rows == official season header" only makes sense against a season-long log |
| `nba2/v4/capture.py` — the capture as code, both modes | their capture was a set of ad-hoc scripts under `analysis/`; this is a module with tests and a scheduled workflow |
| `.github/workflows/player-capture.yml` | nothing else in the repo re-captures player data unattended |

## What the automation does

* **players mode** — official club page → player ids → per-player game-log page → rows, re-gated
  before anything is written (row count vs the page's own count, mean vs the official header,
  every row carrying an official game id). A parse that fails writes nothing and records why.
* **gamebooks mode** — official games index → one gamebook PDF per game, archived with a sha256.
  Primary documents only: no rows are parsed out of them, because a layout parser that cannot be
  tested offline would be guesswork. This is what makes the next capture possible without anyone
  at a keyboard.
* An unreachable upstream is reported and writes nothing; the job stays green, and the last good
  capture stays published.

## The rule the session would not break

Minutes-at-risk sums only the players whose log was captured and is labelled a lower bound. It is
never scaled up, and a player whose table printed "No data available" contributes nothing rather
than a modelled number (F-41B-04, F-41B-05).

## Verification

```
python -m nba2.v4                                      # 40 gates, 40 pass
python -m unittest discover -s nba2/v4 -t .            # 21 tests
python -m nba2.v2 && python -m nba2.v3 && python -m nba2.v2.check   # OK — 0 structural, 0 semantic
python -m nba2.pipeline.build_site                     # mirror into pages/
python -m unittest discover -s nba2/v2 -t .            # 136 tests
python -m unittest discover -s nba2/v3 -t .            # 41 tests
python -m unittest discover -s nba2/tests -t .         # 70 tests
python -m unittest discover -s backtest/tests -t .     # 49 tests
python tools/check_links_all.py                        # 124 files, 5759 internal links, ALL OK
python -m nba2.pipeline.lint                           # 1426 rows, every row sourced
```

Order matters: **v3 must run after v2.** A v2 rebuild regenerates its pages without the v3
navigation, and `nba2.v2.check` is then measuring an incomplete tree.

## Cross-scope requests (logged, not edited)

1. `nba2/v3/playerlogs.py` + `site/player-logs.html` (owner `arena/f8f8f2b8-nba2`, merged) —
   consider adding the G-41-02 identity table to the page: for any season-long log it is the one
   check that can actually fail, and it turns "we captured this" into "we checked this".
2. Pages publication (F-033, owner `arena/56b96bf0-nba2`) — GitHub Pages source is `main /` with
   `build_type: legacy`, so the tree Pages serves is the v1 `pages/` directory. The v3 pages
   `arena/f8f8f2b8-nba2` added (`player-logs.html`, `minutes.html`, `injury-diff.html`) live in
   `site/` and are therefore **not live**. Either switch the Pages source or mirror them.
3. `suggestions/SUGGESTIONS.json` / `requirements/QUESTIONS.json` (same owner) — record that the
   per-player endpoint is reachable and the league-wide one is not; R-102's blocker text should
   say so.
