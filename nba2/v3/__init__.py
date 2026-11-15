"""v3 — the 2026-11-15 rolling-slate build.

Scope note for parallel sessions: this package is owned by `arena/e675ac3d-nba2`.
It does not import from `nba2.v2` and it does not write any file that
`nba2.v2` writes, except that it injects its own navigation links into the
generated `site/*.html` pages (idempotent, and re-applied by CI before the
parity diff).
"""
