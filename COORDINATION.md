# Coordination Board - NBA2

Shared task board for parallel agent sessions. Each session works on its own branch named `session-<id>/<task>` and edits only files in its claimed scope. Claim a task by writing your session ID and file scope here, then commit and push immediately.

## Sessions

### Session arena/36543e84-nba2 (origin/main)
- Status: done
- File scope: COORDINATION.md, README.md, index.html, flagged.html, styles.css, app.js, .github/workflows/pages.yml
- Verification: Site deployed to GitHub Pages (https://wingbangboozle1-lang.github.io/NBA2/); Pages workflow run 43519046185 completed successfully
- PR #1 merged into main on 2026-11-13 (merge commit 84f9b94)

### Session arena/23927d63-nba2 (current branch)
- Status: active
- Session ID: arena-23927d63
- Base commit: 623b4c2fff949848ab272d84871a70ec357f7701

## Tasks

| Task | Status | Owner | Files | Sources | Verification | Irregularities |
|------|--------|-------|-------|---------|--------------|----------------|
| Initial repository review & coordination board | done | arena/36543e84-nba2 | COORDINATION.md, README.md | https://github.com/wingbangboozle1-lang/NBA2 | Repo initially contained only README.md | None |
| Static dashboard with executive summary, strategy hypotheses, validation gates | done | arena/36543e84-nba2 | index.html, flagged.html, styles.css, app.js | Official NBA sources linked per row | HTML parsed with Python HTMLParser; no fabricated values | All numerical values unverified/blank |
| Create COORDINATION.md (this session) | done | arena-23927d63 | COORDINATION.md | N/A | N/A | None |
| Repo review & irregularity flag | done | arena-23927d63 | README.md, COORDINATION.md | https://github.com/wingbangboozle1-lang/NBA2 | Repo contained only README.md initially | None |
| NBA betting strategies research | done | arena-23927d63 | pages/strategies.html, data/strategies.json | NBA.com, RG, BetUS, FantasyTeamAdvice, Basketball-Reference | Correlation values are research estimates | All correlation values unverified |
| Upcoming picks generator (3-day slate) | done | arena-23927d63 | pages/picks.html, data/picks.json | NBA official injury report PDFs | No picks generated; lines blank | Originated lines unverified |
| Injury tracking & rotation minutes | done | arena-23927d63 | pages/injuries.html, data/injuries.json | NBA official injury report (11/13/2026) | Injury status from official PDF | Minutes/production impact estimated |
| Game flow analysis | done | arena-23927d63 | pages/game-flow.html | NBA Stats Help FAQ, Basketball-Reference | Four Factors and PACE definitions verified | Game script classifications unverified |
| Executive summary | done | arena-23927d63 | pages/executive-summary.html | All above sources | Mixed: some verified, some unverified | See Flagged for Review page |
| Site improvement suggestions | done | arena-23927d63 | pages/suggestions.html | N/A | N/A | N/A |
| Questions / info / answers pre-decision | done | arena-23927d63 | pages/questions.html | N/A | N/A | N/A |
| Flagged for Review page | done | arena-23927d63 | pages/flagged-review.html | All above sources | N/A | N/A |
| Site CSS & landing page | done | arena-23927d63 | index.html, css/style.css | N/A | N/A | N/A |
| GitHub Pages deployment | in progress | arena-23927d63 | .github/workflows/deploy.yml | GitHub Pages docs | Pages already configured on main | Needs merge to main for deploy |
| Final integration & merge to main | in progress | arena-23927d63 | All files | TBD | Pending | Pending |

## Rules
- Never start a task another session has claimed.
- If a task requires changing a file owned by another session, log the request here instead of editing it.
- Make small, frequent commits; run `git pull --rebase` before every push.
- On merge conflict, stop, resolve without discarding other work, log what happened.
- When finished, record sources, verification performed, and irregularities; mark done.
- Never mark verified without checking against an official source; link that source.
- Flagged irregularities and unverified items do not block the merge; publish them on the "Flagged for Review" page.

## Conflict Resolution Log
- COORDINATION.md: Merged session arena/36543e84-nba2 content (HEAD) with session arena/23927d63-nba2 task table. Preserved both sessions' verification notes and source links.
