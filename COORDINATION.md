# COORDINATION.md — NBA2 Shared Task Board

Branch: `arena/f0fc8aeb-nba2`, originally branched from `623b4c2fff949848ab272d84871a70ec357f7701` of `main`.
Session: `arena-f0fc8aeb-nba2` (single active session for this branch).

## Situation discovered at start of this session
`origin/main` had already advanced past `623b4c2` due to prior merged sessions:
- Session `arena/36543e84-nba2` (PR #1, merge commit 84f9b94): initial coordination board, dashboard, flagged.html, styles.css, app.js, GitHub Pages workflow. Site deployed to GitHub Pages.
- Session `arena/23927d63-nba2` (PR #3, merge commit 59a01c1): strategies, picks, injuries, game flow, executive summary, suggestions, questions, flagged review, CSS, deploy workflow. All merged into `main`.

So `origin/main` (at 59a01c1) already contains a complete, deployed NBA2 site. My branch `arena/f0fc8aeb-nba2` was based on the stale `623b4c2` and duplicated that work (root-level HTML pages + assets mirroring main's `pages/` + `css/` structure).

## Actions taken by this session
1. Created `COORDINATION.md`, `REPO-REVIEW.md`, `VERIFICATION.md`, `README.md`, `assets/style.css`, `assets/script.js`, and 12 HTML pages (index, lines, strategies, validation-gates, correlation, picks, injuries, executive-summary, suggestions, questions, flagged-review, sources) on branch `arena/f0fc8aeb-nba2`. Committed and pushed (80b3f32).
2. Opened PR #5 (`arena/f0fc8aeb-nba2` → `main`). It was NOT mergeable (conflict on `COORDINATION.md`, `README.md`, `index.html`) because `main` already contained the coordinated, deployed site.
3. **Closed PR #5 as unmerged** to avoid discarding prior sessions' work. The live site is already at https://wingbangboozle1-lang.github.io/NBA2/ .
4. Performed independent line-by-line verification of the deployed `main` content against official NBA sources (see below).

## GitHub Pages deployment (already live on main)
- Pages source: branch `main`, path `/`
- Status: **built** (confirmed via GitHub Pages API)
- Live URL: https://wingbangboozle1-lang.github.io/NBA2/ (confirmed reachable; loads the "NBA Lines Lab" research dashboard)
- This satisfies the "live GitHub Pages site" requirement; no new merge was needed from this session.

## Independent verification results (official sources checked)

| Item | Official source | Reachable? | Verified against deployed data? |
|------|----------------|------------|---------------------------------|
| Injury report | https://official.nba.com/nba-injury-report-2026-27-season/ → PDFs on ak-static.cms.nba.com (NBA CDN) | Yes | Partially — see irregularities |
| Injury report PDF (11/13/26 01:00 PM) | https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_01_00PM.pdf | Yes | Banchero Out (ankle, MIL@ORL) ✓; Haliburton Out (hamstring, NYK@IND) ✓; Butler Out but REASON MISMATCH (see IRR-001) |
| Schedule | https://www.nba.com/schedule | Yes | Week 4 Nov 13 = 9 games; matchups match data/picks.json ✓ |
| Stats | https://www.nba.com/stats/overview, /stats/teams, /stats/players | Yes | Referenced by strategies.json; values themselves unverified |

Deployed `data/picks.json`: 7 picks (slate 2026-11-13..2026-11-16, all actually 11-13 games), all `originatedSpread: null`, `originatedTotal: null`, `recommendedPick: "unverified"`, `strategyId: null` — no lines or picks fabricated. Correct per no-hallucination rule.

Deployed `data/strategies.json`: 8 strategies (STRAT-001…STRAT-008), all `status: "unverified"`; correlations marked `(estimated)`; sources are mixed (some nba.com/stats/help/faq, others rg.org, fantasyteamadvice.com, basketball-reference.com, bestnbabetsystems.com, betus.com.pa — NOT official NBA sources). Correctly not presented as verified.

Deployed `flagged.html`: "Flagged for Review — Open Items · Not Verified"; data policy states no numeric injury/line/odds/correlation/forecast/leaderboard/return value is supplied unless confirmed from an official source. Consistent with no-hallucination rule.

## Irregularities flagged (do not block; published for review)

| Ref | Irregularity | Detail | Source checked |
|-----|--------------|--------|----------------|
| IRR-001 | Jimmy Butler injury-reason mismatch | `data/injuries.json` says Butler III "Right Patella Subluxation"; official NBA injury report PDF (11/13/26 01:00 PM) says "Right ACL Repair / Surgery" for GSW@SAS | official.nba.com injury report PDF |
| IRR-002 | Tyrese Haliburton game-time placeholder | `data/injuries.json` lists Haliburton game as "(game time TBD)"; official schedule/PDF show NYK@IND at 07:00 ET | nba.com/schedule; injury report PDF |
| IRR-003 | Correlation values from non-official sources | strategies.json correlations (r≈0.82, 0.65, 0.58, 0.71, -0.48, etc.) sourced from rg.org, fantasyteamadvice.com, betus.com.pa, bestnbabetsystems.com — not official NBA sources; all marked estimated/unverified | strategies.json sources |
| IRR-004 | Branch duplication | This session's branch duplicated already-merged prior-session work; PR #5 closed unmerged to avoid discarding prior work | git history / PR #3 merge 59a01c1 |

## Sources used for verification
- https://www.nba.com/schedule (official schedule, reachable, matchups confirmed)
- https://official.nba.com/nba-injury-report-2026-27-season/ (official injury report page, reachable)
- https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_01_00PM.pdf (official NBA injury report PDF, reachable)
- https://www.nba.com/stats/overview (official stats, reachable)
- https://github.com/wingbangboozle1-lang/NBA2 (repo)
- https://wingbangboozle1-lang.github.io/NBA2/ (live deployed site)

## Session result
- No new PR/merge created from this session (PR #5 closed as duplicate; `main` already has PR #3 merged and Pages built/live).
- Live site confirmed: https://wingbangboozle1-lang.github.io/NBA2/ (Pages status: built).
- Verification and irregularities recorded above. Nothing was inferred or filled in.
