# COORDINATION.md — NBA2 Shared Task Board

Branch: `arena/f0fc8aeb-nba2` (branched from `623b4c2fff949848ab272d84871a70ec357f7701` of `main`)
Session: single active session, ID = `arena-f0fc8aeb-nba2`

## Rules
- Claim a task by writing your session ID and file scope here, then commit and push that claim immediately.
- Never start a task another session has claimed. Keep scopes non-overlapping (each session edits only its claimed files).
- Shared outputs (table data, site index/navigation) are changed only by the final integration session once all other tasks are done.
- Make small, frequent commits; run `git pull --rebase` before every push.
- On merge conflict: stop, resolve without discarding the other session's work, log what happened.
- If a session crashes or its claim is >60 min old with no commits, another session may take over and note the handoff here.
- When a task is finished, record sources, verification performed, and irregularities here; mark it done.
- Never mark anything verified without checking against an official source; link that source.
- Flagged irregularities / unverified items go on the "Flagged for Review" page; they do NOT block the merge.

## Task board

| # | Task | Status | Owner (session ID) | Files touched | Sources / verification | Irregularities |
|---|------|--------|--------------------|---------------|------------------------|----------------|
| 1 | Repo review (line-by-line, flag irregularities) | in progress | arena-f0fc8aeb-nba2 | COORDINATION.md, REPO-REVIEW.md | n/a (local repo) | none yet |
| 2 | NBA originated lines research & signals | unclaimed | — | data/lines.md | — | — |
| 3 | Strategy design: single bets, parlays, player prop combos | unclaimed | — | data/strategies.md | — | — |
| 4 | Validation gates for strategies | unclaimed | — | data/validation-gates.md | — | — |
| 5 | Correlation values between legs/markets | unclaimed | — | data/correlation.md | — | — |
| 6 | Picks generation for upcoming slates (max 3 days ahead) | unclaimed | — | data/picks.md | — | — |
| 7 | Injuries → rotation minutes & production; game flow analysis | unclaimed | — | data/injuries.md, data/game-flow.md | — | — |
| 8 | Executive summary | unclaimed | — | site/executive-summary.md | — | — |
| 9 | Site improvement suggestions + dedicated suggestions section | unclaimed | — | site/suggestions.md | — | — |
| 10 | Questions / information / answers (pre-decision) + missing-info discovery | unclaimed | — | site/questions.md | — | — |
| 11 | Site creation: GitHub Pages landing page + category subpages, tables w/ sources | unclaimed | — | site/*.html, assets/ | — | — |
| 12 | Line-by-line verification: every table row needs official-source link; blank+flag unverified | in progress | arena-f0fc8aeb-nba2 | all data/site files | — | — |
| 13 | Integration: merge branches, re-verify, build check, no broken links, GitHub Pages deploy | unclaimed | — | COORDINATION.md, site/ | — | — |
| 14 | PR to main + merge + record PR link/merge result + confirm Pages deploy | unclaimed | — | COORDINATION.md | — | — |

## Claims log
- arena-f0fc8aeb-nba2 claimed task #1 (repo review) and #12 (verification) on this branch.

## Notes
- Network is restricted to github.com / api.github.com / registry.npmjs.org / pypi.org / files.pythonhosted.org / codeload.github.com. Direct access to NBA official sites (nba.com, stats.nba.com, ESPN, etc.) may not be possible from bash. Use web_search/fetch_page where available; where an official source cannot be reached, leave the value blank and flag it "unverified" with a note. Never infer or fill in values.
