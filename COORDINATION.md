# NBA2 — Coordination & Task Board

Shared task board for parallel agent sessions. Each session works on its own branch
(or git worktree) named `session-<id>/<task>` and edits only the files in its claimed scope.
Claims must be committed and pushed immediately. A claim older than 60 minutes with no
commits may be taken over by another session (note the handoff in the log below).

Repo: https://github.com/wingbangboozle1-lang/NBA2.git
Working branch: arena/20ee3521-nba2 (session id: arena-20ee3521-nba2)
Base commit: 623b4c2 (Initial commit)

## Claimed tasks (this session)

| # | Task | Status | Scope (files) | Owner | Sources verified | Notes |
|---|------|--------|---------------|-------|------------------|-------|
| 1 | Create COORDINATION.md task board | done | COORDINATION.md | arena-20ee3521-nba2 | — | — |
| 2 | Repo review: line-by-line review of existing repo contents, flag irregularities | done | README.md | arena-20ee3521-nba2 | — | README.md is 6 bytes ("# NBA2"). No other source files. Irregularity: empty repo, nothing to verify. |
| 3 | Build GitHub Pages site structure: landing page + dashboard nav + shared CSS/JS | in progress | index.html, assets/css/style.css, assets/js/main.js, _config.yml | arena-20ee3521-nba2 | — | Clean, simple dashboard UI |
| 4 | Subpage: Strategies (signal generation, leaderboard, validation gates, correlations, single/parlay/player-prop combos) | unclaimed | strategies.html | — | NBA.com (official) | Every row needs official source link or "unverified" flag |
| 5 | Subpage: Picks (upcoming slates up to 3 days ahead, originated lines) | unclaimed | picks.html | — | NBA.com (official) | Every row needs official source link or "unverified" flag |
| 6 | Subpage: Injuries & Game Flow (rotation minutes, production impact, game flow analysis) | unclaimed | injuries.html | — | ak-static.cms.nba.com official injury-report PDFs | Every row needs official source link or "unverified" flag |
| 7 | Subpage: Executive Summary | unclaimed | executive-summary.html | — | — | Summary of important details |
| 8 | Subpage: Suggestions (site improvement suggestions + decision/review path) | unclaimed | suggestions.html | — | — | Review-before-implement process |
| 9 | Subpage: Questions / Information / Answers (pre-decision checklist) | unclaimed | questions.html | — | — | Clear list of what must be addressed before decisions |
| 10| Subpage: Flagged for Review (irregularities + unverified items) | unclaimed | flagged-review.html | — | — | Labeled page; does not block merge |
| 11| Verification pass: every table row line-by-line against official source | unclaimed | all .html | arena-20ee3521-nba2 | — | Blank + "unverified" flag where unconfirmed; never infer |
| 12| Integration: merge branches, re-verify combined data, confirm site builds, no broken links | unclaimed | all | arena-20ee3521-nba2 | — | Final integration session |
| 13| GitHub Pages: enable + confirm deploy succeeds | unclaimed | — | arena-20ee3521-nba2 | — | Do not merge a broken site |
| 14| Pull Request: integration -> main with summary, sources, irregularities; merge | unclaimed | — | arena-20ee3521-nba2 | — | Record PR link + merge result here |

## Handoff log

- (none yet)

## Rules recap
- Claim a task by writing your session ID + file scope, commit + push immediately.
- Never start a task another session has claimed.
- If a task requires changing a file owned by another session, log the request here instead of editing it.
- Small, frequent commits; run `git pull --rebase` before every push.
- On merge conflict: stop, resolve without discarding other work, log what happened.
- Never mark anything verified without an official source; link that source.
- Shared outputs (table data, index, navigation) changed only by the final integration session.
