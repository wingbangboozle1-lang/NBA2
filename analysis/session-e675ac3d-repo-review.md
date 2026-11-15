# Repo review — session `arena/e675ac3d-nba2`, 2026-11-15

Line-by-line review of the repository as it stands at `fc88652` (PR #69), with the
checks that were run and the irregularities found. Every claim below was produced by
running the code or by reading a page, not from memory.

## What the repository is

Six generated site trees plus one Python package tree. Only **one** tree reaches a
reader: `site/`, published at the repository root by `.github/workflows/pages.yml`.
The other trees are retained for history and are not published (`pages/**`, root
`*.html`, `docs/**`, `dashboard/**`, `verified/**`, `originated/**`, `backtest/**`,
`archive/**`). That was verified by probing the live site in an earlier session and
is repeated on the v2 flagged page (F-027); nothing in this session changes it.

## Checkers run, and their results

| Checker | Result |
|---|---|
| `python -m unittest discover -s nba2/tests -t .` | **70 OK** |
| `python -m unittest discover -s nba2/v3 -t . -p 'test_*.py'` | **33 OK** (new this session) |
| `python -m nba2.v3.official` (transcription selftest) | **clean** |
| `python -m nba2.v3.check` | **0 structural, 0 semantic** |
| `python -m nba2.v2.check` | **0 structural, 0 semantic** |
| `tools/check_links_all.py` | 119 files, **5 417 internal links, ALL OK** |
| `python -m nba2.v3` twice, diff committed artefacts | **byte-identical** (deterministic) |
| `nba2.v3.gates` | 7 pass / 1 fail (advisory G-F3) |

## Irregularities found

### I-E675-01 — the published tree is one day stale (freshness, not arithmetic)

`nba2/v2/official.py` carries `AS_OF = 2026-11-14` and `STANDINGS_AS_OF =
2026-11-14`. Its 30 club records sum to **183 wins**. The official standings page
read today (`https://www.nba.com/standings`, 2026-11-15 11:35 UTC) sums to **188
wins**, and 188 is exactly the count implied by the 183 finals committed under
`data/raw/history/` plus the five 11/14 finals read from the official schedule page
this session.

Exactly **10 clubs** differ, and they are precisely the ten that played on 11/14:
MEM 8-4→9-4, MIN 9-3→9-4, DET 8-3→8-4, CLE 6-7→7-7, DAL 7-5→7-6, DEN 6-4→7-4,
MIA 6-6→7-6, NOP 4-9→4-10, BKN 3-8→3-9, CHI 2-9→3-9. So the published numbers were
correct when written and are stale now — the failure mode this project exists to
catch, caught again.

`nba2/v2/official.py` is **not** in this session's claimed scope (open PR #57 and
PR #68 both touch `nba2/v2/`), so it is **not edited here**. It is published on the
v3 verification page as a flag and left for the owning session or the owner.

### I-E675-02 — the standing "player data unreachable" claim is wrong

`nba2/v2/official.py::BLOCKED["player_box"]` says the official players page "renders
season aggregates only for this client". `https://www.nba.com/stats/players/traditional?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame`
returned **469 rows with a MIN column** this session. That converts the rotation and
player-prop blockers from *unavailable* to *not yet captured*. Capturing all ten
pages did not fit this session's budget, so the v3 rotation model ships wired but
empty (F-307) rather than estimated.

### I-E675-03 — HCA: pinned 1.248 today vs 1.53 fitted on 11-14

The v2 page publishes a fitted HCA of 1.53 and discloses that it disagrees with the
≈0.4 implied by the home-win rate (FLAG-PARAM-02). This session measures the
home-win rate directly on 187 non-neutral official finals: **99/187 = 0.5294**, with
a home-margin sd of **16.914**, giving a pinned **h = 1.248** points. The two numbers
answer different questions — one is a least-squares fit to win totals, the other is
the home-win rate restated in points — and the brief asks for the second. Both are
published; neither is reconciled by averaging.

### I-E675-04 — four open pull requests with claims older than the handoff window

PRs **#55**, **#57**, **#59** and **#68** were last committed on 2026-11-14. The
board's takeover rule (claim older than 60 minutes with no commits) is therefore met
at the time this session started. This session takes over the **integration role
only** — adding new pages to the published tree and wiring the rebuild step — and
edits no file those PRs name as their own. Nothing from those branches is discarded.

### I-E675-05 — two official pages disagree about points allowed

The advanced page implies points allowed from `DefRtg x POSS`; the opponent page
prints Opp PTS directly. They differ by up to **0.82 pts/game** (mean 0.26), because
offensive and defensive possession counts are not identical. Both are official. The
v3 model uses the advanced-page pair for internal consistency and prints the
opponent-page figure beside it; it does not average them.

Conversely the derived points-for agrees with the 16 PTS rows read directly from the
traditional page to within **0.09 pts/game** (mean 0.036), which is the check that
makes the derivation trustworthy.

### I-E675-06 — schedule contains a repeat matchup on consecutive days

POR @ MIN is scheduled on both 2026-11-16 (0022600250) and 2026-11-17 (0022600254),
in the same arena; NYK @ TOR repeats inside the window (0022600241, 0022600253).
Recorded as F-301, not resolved; no line is suppressed for it.

### I-E675-07 — game ids are not monotonic in tip order

Inside 2026-11-18, BOS@DEN is 0022600266 but tips at 9:30 PM ET, after GSW@DAL which
is 0022600267 and tips at 8:00 PM ET. Game id is not a date proxy. F-302.

### I-E675-08 — the injury PDF is internally inconsistent about unfiled clubs

The 11/15 06:00 AM ET release prints an explicit `NOT YET SUBMITTED` row for DAL
(DAL@BOS) and **no row at all** for NYK (NYK@TOR). Both mean the club had not filed.
The difference is in the PDF, not in the transcription; both are recorded as
not-filed. F-303.

## Not changed, and why

* `nba2/v2/**`, `nba2/picks.py`, `nba2/model.py`, `nba2/config.py`,
  `nba2/provenance.py`, `nba2/pipeline/**`, `pages/**`, root `*.html`,
  `data/site.json`, `data/v2/**`, `requirements/QUESTIONS.json`,
  `suggestions/SUGGESTIONS.json`, `tools/**`, `.github/workflows/refresh.yml`,
  `backtest/**`, `data/raw/ledger/**` — owned by other sessions or by open PRs.
* The `.github/workflows/pages.yml` and `publish-parity.yml` edits are additive: they
  run `python -m nba2.v3` between the v2 rebuild and the parity diff, because v3
  re-applies its navigation links to the v2 pages and would otherwise be reported as
  drift.
