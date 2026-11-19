"""v7 — fresh official inputs, re-cut model, gated strategies, and the 3-day originated slate.

Why a new layer rather than an edit to v3
-----------------------------------------
v3, v4 and v5 are cut from hand-transcribed snapshots taken on 2026-11-15 / 11-16 / 11-17.
On 2026-11-19 those snapshots are measurably stale: `nba2/v3/official.py` prices ATL at 8-6
while the live standings page prints 9-6, and it has no 11/18 finals at all, so rest,
back-to-back and the luck z-scores are computed on a window that stops two game days early.
Re-cutting them in place would silently change what the published v3/v4/v5 pages mean, which
is another session's scope. v7 is therefore additive: its own module, its own data files,
its own pages, its own gate ids, and its own verification page.

What is in here
---------------
    common        paths and escaping
    official      the 2026-11-19 official snapshot, with the arithmetic identities that
                  check the transcription
    model         two estimators, pinned home court, luck z, rho, walk-forward skill
    strategies    ten strategies, ten gates, pre-registration, parlays, props
    slate         the 3-day originated slate with rest, availability and provenance
    build         renders site/*.html and writes data/v7/*.json
    check         the gates over the emitted tree (fail-closed)
    nav           adds the v7 category to the shared sidebar without removing a link
    capture       the stored-bytes reader for the official pages (used by the parser tests)
"""

__all__ = ["official", "model", "strategies", "slate", "build", "check", "nav", "capture"]
