"""nba2.v4 — the player-level capture and the machinery that extends it
(session ``arena/41bd6ce8-nba2``, 2026-11-15).

What this package is for
------------------------
The brief asks for per-player game logs — minutes, points, rebounds, assists and the
opponent — for at least the players who appear on an injury report. This package

* holds one *gated* capture (``data/raw/capture_2026-11-15-41bd6ce8/``): 5 players,
  48 official player-games, every row read from the player's own nba.com game-log
  page, every player's mean checked against the rates the same page prints;
* implements the gates themselves (:mod:`nba2.v4.gamelog`), so a future capture can
  only enter the repository if it reproduces the official numbers;
* implements the capture as code (:mod:`nba2.v4.capture`), so a scheduled run can
  extend it beyond what a human session can read, and archives the official gamebook
  PDFs that session ``arena/f8f8f2b8-nba2`` showed to be the higher-yield source.

What it deliberately does not do
--------------------------------
* It publishes no pages of its own. The v3 tree already publishes ``player-logs.html``,
  ``minutes.html`` and ``injury-diff.html`` from the official gamebooks (193 rows,
  18 clubs) — a bigger capture of the same question. A second page answering the same
  question under the same name is how a reader learns not to trust either.
* It never estimates. A player whose log was not captured is listed with the reason;
  the minutes-at-risk totals elsewhere on the site are lower bounds, not scaled up.

Run ``python -m nba2.v4`` to measure the gates, ``python -m nba2.v4.capture --help``
for the unattended capture.
"""
