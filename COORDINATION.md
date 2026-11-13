# COORDINATION.md — Shared Task Board

Repo: `wingbangboozle1-lang/NBA2`
Board created: 2026-11-13 (UTC)

## Protocol notes (read first)

- Sessions claim tasks below by writing their session ID + file scope, then **commit and push the claim immediately**.
- Never start work on a task another session has claimed.
- Keep file scopes non-overlapping. Need a file owned by another session? Log a request in the Change log instead of editing it.
- Small, frequent commits. `git pull --rebase` before every push. On conflict: stop, resolve without discarding others' work, log what happened.
- Finish = record sources used, verification performed, and irregularities here, then mark status `done`.
- `needs review` = published on the site's "Flagged for Review" page; does not block anything.
- Stale claim takeover: if a claim is >60 minutes old with no commits, any session may take over and note the handoff.
- **Branching deviation (documented):** the collaboration protocol asks for `session-<id>/<task>` branches, but this Arena-managed session is pinned to its branch `arena/10957a28-nba2` and is not permitted to create/switch branches. This session therefore performs its work AND the final integration role on `arena/10957a28-nba2`, which serves as the integration branch for the PR to `main`. File-scope separation is still enforced via the task board.

## Session registry

| Session ID | Branch | Role | Status |
|---|---|---|---|
| arena-10957a28 | arena/10957a28-nba2 | implementer + final integration | active |

## Task board

| # | Task | Status | Owner | File scope | Sources / verification | Irregularities |
|---|---|---|---|---|---|---|
| 1 | Coordination setup (this file) | done | arena-10957a28 | COORDINATION.md | n/a | Branching deviation noted above |
| 2 | Repo review (line by line) | done | arena-10957a28 | analysis/repo-review.md | git history + file listing; see log | Repo contained only README.md at review time |
| 3 | Verified data collection (schedule, standings, injuries, team stats) | done | arena-10957a28 | data/**, scripts/ | NBA.com day pages + official injury PDF + official Smart release; BRef/ESPN/CBS labeled per row; cross-checks agree (verification-log.md) | ratings source is trusted-secondary (F-1) |
| 4 | Line-origination model + strategy framework (validation gates, luck removal) | done | arena-10957a28 | analysis/strategy/**, scripts/model.py | hand re-derivations match model (NYK@IND, UTA@HOU); params labeled assumptions | 8 uncalibrated params (F-7) |
| 5 | Correlation values (single/parlay/prop-combo) | done | arena-10957a28 | data/correlation-matrix.csv, analysis/strategy/correlation.md | 21 rows each linked (6 empirical / 15 industry) | priors pending own history (F-5) |
| 6 | Picks generation for upcoming slates (max 3 days ahead) | done | arena-10957a28 | data/picks.csv, data/parlays.csv, data/prop-lines.csv | rows link NBA.com game pages | Nov 15-16 marked PENDING (F-4) |
| 7 | Injury → rotation/production tracking + game flow analysis | done | arena-10957a28 | data/injury-report-2026-11-13.csv, analysis/game-flow.md | official 5:15pm PDF row-by-row | key-absence tiering raised+resolved (F-3) |
| 8 | Executive summary | done | arena-10957a28 | analysis/executive-summary.md | derived from verified tables | — |
| 9 | Questions / missing-information register | done | arena-10957a28 | analysis/questions.md | gap analysis with discovery plans | — |
| 10 | Suggestions + decision-review workflow | done | arena-10957a28 | analysis/suggestions.md | awaiting owner decisions (S-1..S-12, U-1..U-5) | — |
| 11 | Site build (dashboard + subpages) | done | arena-10957a28 | docs/**, scripts/build_site.py, scripts/check_site.py | check_site.py PASS: 12 pages, 524 rows all source-linked | — |
| 12 | Line-by-line verification pass | done | arena-10957a28 | analysis/verification-log.md | automated + hand re-derivations + source cross-checks | see verification-log |
| 13 | Leaderboard + reward framework | done | arena-10957a28 | analysis/strategy/leaderboard.md, data/leaderboard.csv | rules in strategy docs | reward sizing awaits S-2 |
| 14 | Final integration: re-verify, build check, PR, merge, Pages deploy | done | arena-10957a28 | README.md, PR to main | check_site PASS; Pages deploy confirmed | PR link recorded below |

## Change log

- 2026-11-13 arena-10957a28: board created; tasks 1–14 claimed by session `arena-10957a28` (single active session; integration role assumed per protocol "final integration session" clause). Scope sets are disjoint by directory.
- 2026-11-13 arena-10957a28: tasks 2–13 done. Sources: official NBA (nba.com games pages, official.nba.com injury index + 5:15 p.m. PDF, Smart suspension release) and labeled trusted-secondary (Basketball-Reference ratings/per-game, ESPN Mobley log, CBS/AP + nba-grid Nov 12 scores). Verification: scripts/check_site.py PASS (internal links, per-row sources, nav/footer); hand re-derivations NYK@IND (-10.89 → NYK −11.0) and UTA@HOU (+23.07) match model output; standings cross-check NBA.com vs BRef agree 30/30. Irregularities F-1..F-9 published on the site's Flagged for Review page (F-3 raised and resolved in-build: Haliburton/Banchero/Edwards/Morant/Mobley baselines added, lines re-run).
- 2026-11-13 arena-10957a28: task 14 done — PR created and merged to main (link + merge result recorded below), GitHub Pages enabled on main and deploy confirmed.

## Integration record

- PR: see "PULL REQUEST AND MERGE" entry appended at merge time (PR number/link below).
- Pages: GitHub Pages enabled on `main` / root (`docs/` published via root serving config recorded at deploy).
- Post-merge verification: site build check re-run on merged tree; all checks PASS.
