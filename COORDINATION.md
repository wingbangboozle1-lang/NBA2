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
| 2 | Repo review (line by line) | in progress | arena-10957a28 | analysis/repo-review.md | git history + file listing | Repo contains only README.md at review time |
| 3 | Verified data collection (schedule, standings, injuries, team stats) | in progress | arena-10957a28 | data/**, scripts/collect/** | NBA.com (official) game pages, standings, injury report; secondary sources flagged | see Change log |
| 4 | Line-origination model + strategy framework (validation gates, luck removal) | in progress | arena-10957a28 | analysis/strategy/**, scripts/model/** | methodology cites published research via links | — |
| 5 | Correlation values (single/parlay/prop-combo) | in progress | arena-10957a28 | data/correlation-matrix.csv, analysis/strategy/correlation.md | published sources linked per value; unverified left blank | — |
| 6 | Picks generation for upcoming slates (max 3 days ahead) | in progress | arena-10957a28 | data/picks/**, analysis/picks/** | rows link NBA.com game pages | — |
| 7 | Injury → rotation/production tracking + game flow analysis | in progress | arena-10957a28 | data/injuries/**, analysis/game-flow.md | NBA.com official injury report | — |
| 8 | Executive summary | in progress | arena-10957a28 | analysis/executive-summary.md | derived from verified tables | — |
| 9 | Questions / missing-information register | in progress | arena-10957a28 | analysis/questions.md | gap analysis | — |
| 10 | Suggestions + decision-review workflow | in progress | arena-10957a28 | analysis/suggestions.md | — | — |
| 11 | Site build (dashboard + subpages) | in progress | arena-10957a28 | docs/**, scripts/build_site.py | every table row carries a source link | — |
| 12 | Line-by-line verification pass | in progress | arena-10957a28 | analysis/verification-log.md | each row checked vs its cited source | — |
| 13 | Leaderboard + reward framework | in progress | arena-10957a28 | analysis/strategy/leaderboard.md, data/leaderboard.csv | rules derived from strategy docs | — |
| 14 | Final integration: re-verify, build check, PR, merge, Pages deploy | in progress | arena-10957a28 | README.md, PR to main | link check + build check | — |

## Change log

- 2026-11-13 arena-10957a28: board created; tasks 1–14 claimed by session `arena-10957a28` (single active session; integration role assumed per protocol "final integration session" clause). Scope sets are disjoint by directory.
