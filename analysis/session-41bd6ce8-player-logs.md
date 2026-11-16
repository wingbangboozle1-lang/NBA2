# Session `arena/41bd6ce8-nba2` — per-player game logs, rotation impact, release diff

**Date** 2026-11-15 · **Branch** `arena/41bd6ce8-nba2` · **Base** `main` @ PR #76
**Scope owned** `nba2/v4/**`, `data/raw/capture_2026-11-15-41bd6ce8/**`,
`site/{player-logs,rotation-impact,injury-diff}.html`, the same three files mirrored into
`pages/`, `.github/workflows/player-capture.yml`, `audit/2026-11-15-41bd6ce8/**`,
`requirements/REQUIREMENTS.json` (status / `how` only), `COORDINATION.md` (append-only).

## The gap

The brief asks for per-player game logs — minutes, points, rebounds, assists and the opponent —
for at least the players who appear on an injury report. Before this session the repository held
**one** game (gid 0022600231) and no per-player season baselines at all, and the board carried
R-102 ("capture the minute/usage column from a licensed or official provider") as *blocked*.

## What the session measured

| Question | Answer | Evidence |
|---|---|---|
| Is the data reachable? | **Yes, per player** — `nba.com/stats/player/{id}/boxscores-traditional` renders Match Up, W/L, MIN, PTS, REB, AST, STL, BLK, TOV, +/- and the game id | 48 rows captured; `audit/2026-11-15-41bd6ce8/verification-log.md` §1 |
| Is there a league-wide table? | **No.** `nba.com/stats/players/traditional` renders but prints "No data available"; `cdn.nba.com/static/json/**` returns HTTP 500 | `nba2/v4/official.py::UNREACHABLE`, published on the page |
| Is the capture correct? | mean of the captured rows == the PPG/RPG/APG the same page prints in the player header, for all 5 players (gate G-41-02, ±0.05) | same table, computed column |
| Can the sandbox fetch it in code? | **No** — no outbound network; captures go through the platform page-fetch tool | smoke run of `nba2.v4.capture` records `URLError: TLS/SSL connection has been closed` |

So R-102 is not blocked any more; it is *partial*, and the reason it is partial is page budget,
not access.

## What was published

Three pages, in both trees that can be served:

* **`player-logs.html`** — 48 official player-games for 5 players, every row linking to the
  player's own game-log page, plus the 40 gate measurements, the two players whose table would
  not render, the 26 release players with no log, and the four endpoints that do not work.
* **`rotation-impact.html`** — minutes and production designated *out* for GSW and NOP on the
  11/16 slate, expressed as a share of the club's 240 team-minutes, with the official roster of
  players who would have to absorb it. Their minutes are deliberately blank: the redistribution
  rule needs Σ(available mpg) as its denominator and that is not captured, so the rule is
  published with an empty denominator rather than a proxy.
* **`injury-diff.html`** — the 06:15 PM release diffed against the 06:15 AM release already in
  the repository: what was added, what changed status and in which direction.

## The rule the session would not break

Minutes-at-risk sums only the designated players whose log was captured and is labelled a lower
bound. It is never scaled up to the players who were not captured, and a player whose table
printed "No data available" contributes nothing rather than a modelled number. This is why the
coverage flag (F-41B-05, 5 of 31 players) is printed next to the totals instead of being
corrected away.

## Scaling it

`nba2/v4/capture.py` expresses the same capture as code (official club page → player ids →
per-player game-log page → rows), re-gates every parsed player before writing, and records a
capture failure instead of a number when a page cannot be read. `.github/workflows/player-capture.yml`
runs it twice daily, rebuilds `v2 → v3 → v4 → pages/`, and commits only if something changed and
`nba2.v2.check` passes. Its first run is supervised: see F-41B-06.

## Cross-scope requests (not edited here)

* `suggestions/SUGGESTIONS.json` (owner `arena/56b96bf0-nba2`) — a new suggestion follows from
  this session: *promote the per-player game log to the standing nightly ingest so minutes-at-risk
  stops being a lower bound*, with the measured page-budget cost (≈7 pages per club).
* `requirements/QUESTIONS.json` (same owner) — R-102's blocker text should be replaced with the
  measured reachability result above.
* `nba2/pipeline/**` — three additive nav entries were made in `build_site.py` so the v1 tree
  Pages actually serves links to the new pages; logged here rather than changing shared
  navigation unilaterally.

## Verification commands

```
python -m nba2.v2 && python -m nba2.v2.check          # 24 pages, OK — 0 structural, 0 semantic
python -m nba2.v3 && python -m nba2.v3.check          # 7 pages, 7 pass / 1 fail (G6, no price)
python -m nba2.v4                                     # 3 pages
python -m nba2.pipeline.build_site                    # mirror into pages/
python -m unittest discover -s nba2/v4 -t .           # 37 tests
python -m unittest discover -s nba2/v3 -t .           # 33 tests
python -m unittest discover -s nba2/v2 -t .           # 129 tests
python tools/check_links_all.py                       # 127 files, all internal links OK
python -m nba2.pipeline.lint                          # 1423 rows, every row sourced
```

Order matters: **v4 must run last.** A v2 rebuild strips the v3 and v4 navigation from
`site/*.html`; the chain above leaves the tree complete, and `nba2.v4` now also repairs pages
that lost links.
