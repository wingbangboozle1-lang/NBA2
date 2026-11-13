# Coordination board

Session: `arena/36543e84-nba2` (current active branch `arena/36543e84-nba2`). Repository baseline was a single-file stub (`README.md`); no other task claims were present at start.

| Task | Status | Owner session | File scope |
|---|---|---|---|
| Initial repository review, source-backed requirements, decision gaps, and static dashboard | done | arena/36543e84-nba2 | COORDINATION.md, README.md, index.html, flagged.html, styles.css, app.js, .github/workflows/pages.yml |

## Verification and source log
- Initial repository review: `git ls-files` initially listed only `README.md`; no application, tests, data, model, source connector, deployment workflow, or existing coordination board was present.
- Official sources checked directly (2026-11-13): [NBA Stats](https://www.nba.com/stats/) (official stats interface); [NBA Schedule](https://www.nba.com/schedule) (official schedule and game listings); [NBA official injury reporting](https://official.nba.com/nba-injury-report-2026-27-season/) (explains team reporting deadlines and continual updates); [GitHub Pages documentation](https://docs.github.com/en/pages) (Pages supports publishing from a branch or Actions workflow).
- Files added: a dependency-free dashboard with executive summary, candidate strategy hypotheses, validation gates, system requirements and staged recommendations; separate Flagged for Review table; source/readme. Every table row in the site has a link to a relevant official NBA reference, except Pages configuration row which links to official GitHub documentation. Links indicate reference material, not confirmation of numerical findings.
- Verification performed: Python `HTMLParser` parsed both HTML documents; checked fragment targets and local `.html` links. No build tool or test suite exists. No picks, model parameters, line values, market odds, correlations, player-specific injury impacts, results, or leaderboard ranks are fabricated; all unavailable values are explicitly unverified/blank in substance.
- Known irregularities: official NBA Stats and schedule pages are interfaces, not evidence of a historical odds feed, data use rights, archived revisions, or model validity. The linked live injury report changes continually. Correlation/skill and rotation effects require properly timestamped raw data and reproducible analysis; no values could be verified. A standard GitHub Pages Actions workflow is now included; repository Pages/Actions settings and deployment success still require checking after merge. User's requests to originate live picks and publish a live site cannot be completed truthfully from this empty starter repository alone.
- PR #1: https://github.com/wingbangboozle1-lang/NBA2/pull/1 — merged into `main` on 2026-11-13 (merge commit `84f9b94`).
- Deployment verification: GitHub Actions Pages workflow run `43519046185` completed successfully; GitHub Pages API reports `status: built`, public site URL https://wingbangboozle1-lang.github.io/NBA2/ (2026-11-13). The site is live. No failure was observed.

---

## Session arena-71f94203 (branch `arena/71f94203-nba2`, base `623b4c2`, synced to `main` @ `c3a000b`)

Claimed on 2026-11-13 (UTC ~22:40). Scope is deliberately narrow to avoid editing other sessions' files.

| Task | Status | Owner | File scope | Notes |
|---|---|---|---|---|
| Official-source 3-day slate dataset (Fri 11/13 – Mon 11/16, 31 games) with per-row source links | in progress | arena-71f94203 | `data/verified/schedule_2026-11-13_to_16.json` | Source: nba.com/schedule (fetched 2026-11-13) |
| Official injury-report rows for 11/13 5:15 PM ET report with explicit game attribution + unattributed review list | in progress | arena-71f94203 | `data/verified/injuries_2026-11-13_0515PM.json` | Source: ak-static.cms.nba.com PDF linked from official.nba.com |
| Audit of PR #3 branch `arena/23927d63-nba2` data files (`data/injuries.json`, `data/picks.json`, `data/strategies.json`) against official sources | in progress | arena-71f94203 | `data/verified/audit_arena-23927d63.json` | Findings logged below; NOT edited in that branch |
| Verification tooling + pick-gate generator (outputs gated "no pick" rows; no values invented) | in progress | arena-71f94203 | `tools/verify_data.py`, `tools/build_verified.py`, `tools/generate_picks.py` | Validator enforces source links, official domains, team-to-matchup consistency |
| Static pages for verified data | in progress | arena-71f94203 | `verified/*.html` (new folder only) | Reuses `styles.css` read-only; does NOT touch `index.html`, `flagged.html`, `app.js` |

### Claims that overlap other sessions (logged, not silently duplicated)
- **Repo review / dashboard** — completed by `arena/36543e84-nba2` (merged, PRs #1 and #2). This session does not redo it.
- **Strategies research (`data/strategies.json`, `pages/strategies.html`)** — claimed in progress by `arena/23927d63-nba2` (PR #3 open). This session does not edit it; see audit findings.
- **Verification (#12)** — claimed in progress by `arena/f0fc8aeb-nba2`; that branch has only this board. This session verifies only its own rows.
- **Final integration / merge** — not claimed here until the other PRs are resolved; see the integration section below.

### Verification log (arena-71f94203)
- **Schedule** — https://www.nba.com/schedule fetched 2026-11-13 (pages 0–2 of 9). Window = Fri 11/13 to Mon 11/16 (today + 3 days). Counted: Fri 9, Sat 5, Sun 9, Mon 8 = 31 games. Each game ID, time (ET), arena, city and preview URL was read from the page text.
- **Injury report** — https://official.nba.com/nba-injury-report-2026-27-season/ lists reports up to `Injury-Report_2026-11-13_05_15PM.pdf` (latest in the list at check time). PDF fetched (2 chunks). Rows are included only if the matchup is printed on the same row; other rows go to a review list. Team/matchup pairs are checked against the schedule by the validator.
- **Redirect check** — `official.nba.com/nba-injury-report-2024-25-season/` resolves to the 2026-27 page (the fetch tool reports the final URL). Any link to the 2024-25 URL is stale.
- **Cross-check of PR #3 data** — see `data/verified/audit_arena-23927d63.json`.

### Irregularities (arena-71f94203)
1. PR #3 (`arena/23927d63-nba2`) `data/injuries.json`: 10 entries; 9 of 10 carry `"verified": false`, but 6 have wrong team, game, or time against the official PDF/schedule (see audit file). Per-player `minutesImpact` values (for example "~34 MPG season avg") have no source in any retrieved official document.
2. PR #3 `data/picks.json`: game IDs (`GAME-20261113-00x`) are not NBA game IDs. Two Friday games are missing (NYK@IND, POR@SAC). Times wrong for MEM@NOP (8:30 vs 8:00 PM ET) and CLE@MIA ("TBD" vs 8:00 PM ET).
3. PR #3 `data/strategies.json`: correlation values (for example r ≈ 0.82, r ≈ 0.65, r ≈ 0.58, r ≈ 0.71, r ≈ -0.48) and "~1.5 possessions" have no source. Several cited sources are not official (rg.org, fantasyteamadvice.com, bestnbabetsystems.com, betus.com.pa, basketball-reference.com).
4. Live Pages URL served an earlier dashboard; `main` is now the source of truth (PRs #1, #2).
5. The task brief's branch naming (`session-<id>/<task>`) conflicts with the system-assigned naming (`arena/<session>-nba2`). This session follows the system naming and pushes only to its own branch.
6. The brief's HTML-escaped placeholder `session-&amp;amp;lt;id&amp;amp;gt;` is malformed; it was treated as `session-<id>/<task>`.
