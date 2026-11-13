# COORDINATION.md — NBA2 Shared Task Board

Shared task board for the NBA2 project. It lists every task, its status
(`unclaimed`, `in progress`, `done`, `needs review`), the owning session ID, the files it
touches, and the verification record. **Read this before starting any task.**

- **Status meanings:** `unclaimed` · `in progress` · `done` (finished + verified, sources
  logged) · `needs review` (published on the Flagged for Review page; does not block work).
- **Claiming:** write your session ID + file scope, commit and push the claim immediately.
- **Scope:** keep file scopes non-overlapping. Shared outputs (site index/navigation,
  combined table data) are changed only by the final integration session.
- **Verification:** never mark anything verified without checking it against an official
  source; link that source. If a value cannot be confirmed, leave it blank and flag it.
- **Handoff:** if a claim is >60 min old with no commits, another session may take over and
  must note the handoff in the log.

## Session registry

| Session ID | Branch | Role | Notes |
|---|---|---|---|
| arena/36543e84-nba2 | merged to main | Landing page + Pages workflow | Built root `index.html`, `flagged.html`, `styles.css`, `app.js`, `.github/workflows/pages.yml`. PR #1 merged. |
| arena-23927d63 (arena/23927d63-nba2) | merged to main | Research/verification pages | Built `pages/`, `verified/`, `data/`, `tools/`, research-scaffold. PR #3 merged. |
| arena/71f94203-nba2 | merged to main | Integration (prior) | Merged session 23927d63 work; kept single `pages.yml`; PR #6 merged. |
| session-7b4973eb-nba2 (arena/7b4973eb-nba2) | merged to main | Lines-origination system + dashboard + final integration | Built `nba2/` Python system, root dashboard pages, and performed the final cross-session integration. PR #7 merged. |

## Tasks

| # | Task | Status | Owner | File scope | Sources / verification |
|---|---|---|---|---|---|
| 1 | Repo setup & coordination board | done | arena/36543e84-nba2, arena-23927d63, session-7b4973eb-nba2 | `COORDINATION.md`, `README.md`, `.gitignore` | Greenfield repo (`623b4c2`). |
| 2 | Landing dashboard + Pages workflow | done | arena/36543e84-nba2 | `index.html`, `flagged.html`, `styles.css`, `app.js`, `.github/workflows/pages.yml` | Site deployed to GitHub Pages; workflow run completed. |
| 3 | Research/verification pages | done | arena-23927d63 | `pages/`, `verified/`, `data/`, `tools/` | Official NBA sources linked per row; no fabricated values. |
| 4 | Verified data acquisition (schedule, records, injuries) | done | session-7b4973eb-nba2 | `nba2/data/schedule.json`, `records.json`, `injuries.json` | NBA.com schedule + official injury report PDF (11/13/26 01:00 PM). |
| 5 | Lines-origination model + picks generator | done | session-7b4973eb-nba2 | `nba2/model.py`, `picks.py`, `sources.py` | Model outputs originated (not official); inputs verified to NBA.com. |
| 6 | Strategy framework, validation gates, correlations, leaderboard | done | session-7b4973eb-nba2 | `nba2/strategies.py`, `correlations.py`, `nba2/data/strategies.json`, `correlations.json` | Gate logic deterministic; historical correlations flagged pending. |
| 7 | Injury impact + game-flow analysis | done | session-7b4973eb-nba2 | `nba2/injuries.py`, `nba2/data/gameflow.json` | Injury statuses verified to NBA.com PDF; impact/flow are model estimates (flagged). |
| 8 | Root dashboard (landing + category subpages + tables) | done | session-7b4973eb-nba2 | root `*.html`, `assets/`, `build_site.py` | Static HTML/CSS/JS; tables embed verified data + per-row source links. |
| 9 | Executive summary, suggestions, open questions | done | session-7b4973eb-nba2 | `executive-summary.html`, `suggestions.html`, `questions.html` | Derived from verified data + documented methodology. |
| 10 | Flagged-for-review page | done | session-7b4973eb-nba2 | `flagged.html`, `nba2/data/flagged.json` | All flagged items listed with source links or "unverified" reason. |
| 11 | Final cross-session integration, build, verify links, deploy, PR, merge | done | session-7b4973eb-nba2 | repo-wide (integration) | See "Merge conflict & integration record" below. |

## Change log

- **2026-11-13** — arena/36543e84-nba2: initial landing page + Pages workflow; PR #1 merged.
- **2026-11-13** — arena-23927d63: research/verification pages; PR #3 merged.
- **2026-11-13** — arena/71f94203-nba2: integrated session 23927d63 work; kept single
  `pages.yml`; PR #6 merged.
- **2026-11-13** — session-7b4973eb-nba2: built the `nba2/` lines-origination system and
  root dashboard on branch `arena/7b4973eb-nba2`; opened PR #7.
- **2026-11-13** — session-7b4973eb-nba2: performed final integration of PR #7 with `main`
  (see merge record below); PR #7 merged to `main`.

## Merge conflict & integration record

PR #7 (`arena/7b4973eb-nba2` → `main`) could not merge cleanly because the branch and
`main` (which already contained the parallel sessions' work via PRs #1/#3/#6) both added
the same root files. **Conflicts (add/add / content):** `.gitignore`, `COORDINATION.md`,
`README.md`, `index.html`, `flagged.html`.

**Resolution (without discarding the other sessions' work):**

- `index.html`, `flagged.html` — kept the **session-7b4973eb-nba2** versions as the
  canonical dashboard (more complete, per-row verified source links). The parallel
  sessions' original root `index.html` and `flagged.html` were **preserved** under
  `archive/index-other-session.html` and `archive/flagged-other-session.html`.
- All other parallel-session files (`pages/`, `verified/`, `data/`, `tools/`, `css/`,
  `styles.css`, `app.js`, `.github/workflows/pages.yml`) were **kept unchanged**.
- `.gitignore` — combined both sets of ignore rules.
- `README.md` — rewritten as an integrated description of the combined project.
- `COORDINATION.md` — unified into this board (both sessions' tasks + this record).

**Verification performed by the integration session:** combined data re-checked line by
line against NBA.com official sources; all HTML pages present; no broken internal links
(all root-relative nav links resolve to committed files); the existing `pages.yml`
workflow deploys the root directory to GitHub Pages.

## PR & Merge results

- **PR #7:** https://github.com/wingbangboozle1-lang/NBA2/pull/7 — merged into `main` via
  `gh pr merge 7 --merge` after conflict resolution (merge commit recorded on `main`).
- **Live site:** https://wingbangboozle1-lang.github.io/NBA2/

**Result:** merged successfully; GitHub Pages redeployed from the `main` branch root.
Flagged irregularities and unverified items do not block the merge and are published on
the [Flagged for Review](flagged.html) page with source links for post-launch review.
