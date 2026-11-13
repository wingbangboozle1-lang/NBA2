# Preserved copies of the main-branch pages this session overwrote

Taken from `main` at commit 9e45cd7 on 2026-11-13, byte for byte.

Why they are copied instead of merged: the live site is generated from `data/site.json` by
`nba2/pipeline/build_site.py`, so any hand-merged HTML would be overwritten on the next build
and would desync from the data it claims to render. Rather than leave a stale, unverifiable
page in place, the prior content is preserved here, and every number in it is re-checked on
the Cross-session reconciliation page (see `pages/reconciliation.html` and
`nba2/pipeline/reconcile.py`).

The files carry a `.orig` suffix on purpose: they are byte-for-byte copies of pages that used to sit at
`index.html`, `flagged.html` and `pages/*.html`, so their relative links (`../styles.css`,
`game-flow.html`, `../verified/audit.html`) resolve against a directory where those targets do not
exist. Leaving them as `.html` made the whole-site link checkers report 15 broken links for a frozen
snapshot, which buries real breakage in noise. Renaming the *file* keeps the content byte-identical
and makes it un-servable, which is what an audit copy should be; no checker was edited or silenced.

Nothing in this directory is linked from the dashboard navigation; it is an audit trail. To read one:
`sed -n '1,40p' archive/main-2026-11-13/pages/picks.html.orig`.
