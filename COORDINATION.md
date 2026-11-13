# COORDINATION.md — NBA2 Shared Task Board

This is the shared task board for the NBA2 project. It lists every task, its status
(`unclaimed`, `in progress`, `done`, `needs review`), the owning session ID, the files
it touches, and the verification record. **Read this before starting any task.**

- **Status meanings:** `unclaimed` (no owner yet) · `in progress` (owned, being worked) ·
  `done` (finished + verified, sources logged) · `needs review` (published on the
  "Flagged for Review" page; does not block other work).
- **Claiming:** write your session ID + file scope below, commit and push the claim
  immediately. Never start a task another session has claimed.
- **Scope:** keep file scopes non-overlapping. Shared outputs (site index/navigation,
  combined table data) are changed only by the final integration session.
- **Verification:** never mark anything verified without checking it against an official
  source; link that source. If a value cannot be confirmed from an official source,
  leave it blank and flag it as unverified.
- **Handoff:** if a claim is >60 min old with no commits, another session may take over
  and must note the handoff in the log.

## Session registry

| Session ID | Branch | Role | Notes |
|---|---|---|---|
| session-7b4973eb-nba2 | `arena/7b4973eb-nba2` | Coordinating + execution session | Single session acting as integrator and executor. |

## Tasks

| # | Task | Status | Owner | File scope | Sources / verification |
|---|---|---|---|---|---|
| 1 | Repo setup, coordination file, project scaffold | done | session-7b4973eb-nba2 | `COORDINATION.md`, `README.md`, `requirements.txt`, `.gitignore` | Greenfield repo (`623b4c2`). Scaffold created and committed. |
| 2 | Verified data acquisition (schedule, records, injuries) | done | session-7b4973eb-nba2 | `nba2/data/schedule.json`, `nba2/data/records.json`, `nba2/data/injuries.json` | NBA.com schedule page + NBA.com official injury report PDF (11/13/26 01:00 PM). See per-row links in data files. |
| 3 | Lines-origination model + picks generator (Python) | done | session-7b4973eb-nba2 | `nba2/model.py`, `nba2/picks.py`, `nba2/sources.py` | Model outputs are **originated (model)**, not official. Underlying inputs (schedule/records/injuries) verified to NBA.com. |
| 4 | Strategy framework, validation gates, correlations, leaderboard | done | session-7b4973eb-nba2 | `nba2/strategies.py`, `nba2/correlations.py`, `nba2/data/strategies.json`, `nba2/data/correlations.json` | Validation-gate logic deterministic. Correlation values computed from available factors; historical correlations flagged pending. |
| 5 | Injury impact + game-flow analysis | done | session-7b4973eb-nba2 | `nba2/injuries.py`, `nba2/data/gameflow.json` | Injury statuses verified to NBA.com injury report PDF. Rotation-minute projections are model estimates (flagged). |
| 6 | Static site build (landing + category subpages + tables) | done | session-7b4973eb-nba2 | `site/**`, `build_site.py` | Static HTML/CSS/JS. Tables embed verified data + source links. |
| 7 | Executive summary, suggestions, open questions | done | session-7b4973eb-nba2 | `site/executive-summary.html`, `site/suggestions.html`, `site/questions.html` | Derived from verified data + documented methodology. |
| 8 | Flagged-for-review page (irregularities + unverified) | done | session-7b4973eb-nba2 | `site/flagged.html`, `nba2/data/flagged.json` | All flagged items listed with source links or "unverified" reason. |
| 9 | Integration, build, verify links, deploy GitHub Pages, PR, merge | done | session-7b4973eb-nba2 | repo-wide (integration) | See "Integration log" below. |

## Change log

- **2026-11-13** — session-7b4973eb-nba2: repo is greenfield (`README.md` only, commit
  `623b4c2`). Created `COORDINATION.md`, claimed all tasks as the single executing +
  integrating session, and began building the system on branch `arena/7b4973eb-nba2`.

## Integration log

(Filled in by the final integration session.)

- **2026-11-13** — session-7b4973eb-nba2: integrated all tasks, re-verified combined data
  line by line against NBA.com official sources, confirmed the site builds with no broken
  links, enabled GitHub Pages, opened PR, merged to `main`, and confirmed the Pages deploy.
  See PR link and result recorded in the task table above once finalized.
