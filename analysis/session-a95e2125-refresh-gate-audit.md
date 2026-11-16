# Session `arena/a95e2125-nba2` — rolling-slate gate audit

**Claim (2026-11-16 UTC).** The branch starts at `32019ac` (PR #88 merge); the worktree was clean. I read `COORDINATION.md` before claiming. Existing v3 deliverables and the earlier refresh implementation are present. This task is limited to a fail-closed defect found in the v2 refresh gate, not a rewrite of the site or refresh pipeline.

## Claimed scope

| ID | Task | Status | File scope | Verification |
|---|---|---|---|---|
| A95-01 | Require official games in all four dates of the requested T+0..T+3 slate; reject empty, missing-date, out-of-window, and malformed game rows before any write/rebuild | in progress | `nba2/v2/refresh.py`, `nba2/v2/test_refresh_gates.py` | Unit tests for positive and negative cases; existing refresh gate test suite |
| A95-02 | Record audit, source/verification details, and remaining gaps | in progress | `analysis/session-a95e2125-refresh-gate-audit.md`, append-only `COORDINATION.md` | Full v2/v3 checks and link/lint checks where feasible |

## Initial finding

`gate_slate()` in `nba2/v2/refresh.py` reported PASS for an empty `games` array: `len(gids) == len(set(gids))` and `all(...)` are both true for an empty list. It also did not require each of the four requested dates to appear, nor confirm game IDs/team/date fields are valid. This contradicted the function docstring and the requirement that a rolling T+0..T+3 slate be covered before rebuilding. No live values are being added by this change; it is gate logic only.

## Source boundary

The gate validates fetched rows against the four requested dates; this does not independently certify NBA source data. The refresh fetcher records official NBA schedule URLs (`https://www.nba.com/schedule?date=<date>`) on each row. Only source-backed rows can satisfy the gate; missing dates remain a hard failure, never inferred from league calendar knowledge.
