"""The v4 irregularity register, in one leaf module.

Why this module exists (CR-V4-2, session arena/7bfb0276-nba2):

The v4 gated surfaces used to publish their own irregularities on ``site/v4-verify.html``
and ``site/v4-injuries.html`` only. The brief asks for every unverified item to be on the
canonical *Flagged for review* page, and that page is generated from
``nba2/v2/content.py::FLAGS``. The register therefore lives HERE, in a leaf module that
imports nothing but the capture, so both the v2 page and the v4 pages can read the same
list without an import cycle and without the two drifting apart.

Shape, matching ``nba2/v2/content.py::FLAGS``:

    (id, severity, area, finding, disposition, source_url)

Severity vocabulary is the v2 one: ``high`` / ``medium`` / ``low`` / ``info``.
"""

from __future__ import annotations

from . import capture as C

V4_FLAGS = [
    ("F-V4-01", "high", "Injury releases",
     "The injury releases are stored as transcribed text, not as the original PDF bytes: "
     "bash egress to ak-static.cms.nba.com returns HTTP 000 from this sandbox, and the "
     "page-fetch tool returns the PDF as text rather than as bytes.",
     "Every release carries its official URL, its revision stamp, the time the league index "
     "was checked, this session's retrieval stamp, and a sha256 over the transcribed text "
     "(a content hash). The original file hash is not available and is not claimed.",
     "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-16_01_00PM.pdf"),
    ("F-V4-02", "medium", "Player logs",
     "Per-player game logs for the 11/15 and 11/16 games were not transcribed: 9 games x "
     "roughly 26 player rows was outside the capture budget of the session that read them.",
     "The committed 11/13 and 11/14 logs stand unchanged and are labelled with their own "
     "dates. Nothing is back-filled and no player row is inferred from a team sheet.",
     "https://statsdmz.nba.com/pdfs/20261115/20261115_INDPHI_book.pdf"),
    ("F-V4-03", "medium", "Travel distance",
     "Travel mileage is a great-circle distance over arena coordinates sourced from "
     "Wikimedia/Wikidata (P625). NBA.com publishes arena name, city and state but no "
     "coordinates, so no official coordinate source exists to check against.",
     "Every travel row is labelled THIRD-PARTY and carries the date its coordinates were "
     "read. The travel distance is never presented as an official value.",
     "https://www.nba.com/schedule"),
    ("F-V4-04", "high", "Bet surface",
     "No licensed odds feed is connected, so there is no market price anywhere in this "
     "repository: no edge, no stake, no Kelly fraction and no closing-line value can be "
     "computed, and the market-anchored prior's weight is undefined.",
     "The bet surface publishes 0 rows and an explicit refusal for every game, and every "
     "stake is held at 0.00 units. The gate that refused it is named on the page.",
     "https://www.nba.com/games"),
    ("F-V4-05", "medium", "Injury releases",
     "Continuation rows in the official PDF lose their date, time, matchup and sometimes "
     "their team cell at a page break, so those cells are not directly readable.",
     "Each affected row is keyed off the block the PDF prints it in, and the "
     "reconstruction is written into the row's own note so a reader can see that it was "
     "reconstructed rather than read. A player is never assigned a team by inference from "
     "the club they normally play for.",
     "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-16_01_00PM.pdf"),
    ("F-V4-06", "medium", "Injury releases",
     "One GSW@NOP row in the 01:00 PM release (Jimmy Butler III) prints no Current Status "
     "cell at all: only the reason is legible. In the earlier 09:15 AM release the same "
     "block lost the status column for all six rows, so five of the six are now readable "
     "and this one is not.",
     "The status is left blank and flagged on the row, and the row is counted separately "
     "from the status tally. It is never back-filled and never treated as Available.",
     "https://official.nba.com/nba-injury-report-2026-27-season/"),
    ("F-V4-07", "medium", "Injury releases",
     "POR@MIN appears under two different dates in the same release (the 11/16 and the "
     "11/17 filing), so a date-only key would merge two distinct filings.",
     "The diff key is (date, matchup, team, player), so both filings stay distinct and "
     "each is diffed against its own earlier state.",
     "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-16_01_00PM.pdf"),
    ("F-V4-08", "medium", "Rotation availability",
     "Rotation impact is not published as a number: the official injury report states a "
     "status and a reason, never minutes, and no matched before/after pair of games has "
     "been captured for the affected clubs.",
     "Status counts only, with production impact explicitly blank and flagged. Minutes "
     "shares and replacement shares are not invented, and the availability column names "
     "its reason instead of showing a bare dash.",
     "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-16_01_00PM.pdf"),
    ("F-V4-09", "low", "Injury releases",
     "The 09:30 AM release is identical row-for-row to the 09:15 AM release.",
     "It is declared with an explicit identical_to and a basis, so it is not counted as a "
     "change and does not inflate the diff ledger.",
     "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-16_09_30AM.pdf"),
    ("F-V4-10", "medium", "Injury releases",
     "The newest official release (11/16/26 01:00 PM ET) prints no Current Status for one "
     "GSW@NOP row, so that player's status cannot be read from the official text.",
     "The status cell is left blank, the reason that IS legible is kept, and the row "
     "carries a note naming this flag. It is not inferred from the club's other rows.",
     "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-16_01_00PM.pdf"),
    ("F-V4-11", "low", "Injury releases",
     "Five GSW@NOP rows in the newest release print a legible Current Status but an empty "
     "Reason cell, so their reason cannot be read from the official text.",
     "The status is published as printed and the reason is left blank. No reason is "
     "carried over from an earlier release or written from a player's known injury.",
     "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-16_01_00PM.pdf"),
    ("F-V4-12", "medium", "Injury releases",
     "A captured injury release is a point-in-time reading and ages within the hour: the "
     "league index publishes a new release every fifteen minutes. The committed capture "
     "stopped at 09:15 AM ET while the index already listed releases up to 01:00 PM ET, "
     "so a capture can be stale by fourteen releases without anything in the repository "
     "noticing.",
     "The release ledger now stores every release with its revision stamp, the time the "
     "index was checked, and the retrieval time, and the diff between consecutive "
     "releases is published. The gap is still possible; what changed is that the age of "
     "the newest release is printed on the page and the index is checked at read time.",
     "https://official.nba.com/nba-injury-report-2026-27-season/"),
    ("F-V4-13", "low", "Cross-surface",
     "The shared official finals history advances every game night, while the frozen v1 "
     "slate snapshot it was once anchored to does not. A checker that compared the two "
     "reported a category error as a look-ahead leak.",
     "The check is now anchored to the report's own declared cutoff, and the cross-tree "
     "offset is disclosed as its own line rather than being hidden or used to fail a "
     "build. The v1 tree remains a self-contained 2026-11-14 build that never reads "
     "data/raw/history.",
     "https://www.nba.com/games"),
]

# The v4 surface renders its own register on site/v4-verify.html with a link to the
# page and a source link per row, which is the shape (id, severity, (page, fragment,
# label, url), finding, disposition). The canonical v2 register uses
# (id, severity, area, finding, disposition, url). The conversion below keeps one
# source of truth and two renderings.
#
# The (page, fragment, label) target is where a reviewer should go to settle the item.
# The fragment is a real anchor on the target page: the v2 link checker was fixed in
# CR-V4-1 to split the fragment off, resolve the file, and then verify the anchor
# exists, so a section-level link is checked rather than merely tolerated.
_V4_TARGETS = {
    "F-V4-01": ("v4-injuries.html", "binary-not-stored", "Injury releases"),
    "F-V4-02": ("v4-verify.html", "", "This page"),
    "F-V4-03": ("projection.html", "flow", "Schedule flow"),
    "F-V4-04": ("bet.html", "g6", "Bet surface"),
    "F-V4-05": ("v4-injuries.html", "layout", "Layout artefacts"),
    "F-V4-06": ("v4-injuries.html", "layout", "Layout artefacts"),
    "F-V4-07": ("v4-injuries.html", "cross-day", "Cross-day diff"),
    "F-V4-08": ("projection.html", "availability", "Rotation availability"),
    "F-V4-09": ("v4-injuries.html", "releases", "Release diff"),
    "F-V4-10": ("v4-injuries.html", "layout", "Layout artefacts"),
    "F-V4-11": ("v4-injuries.html", "layout", "Layout artefacts"),
    "F-V4-12": ("v4-injuries.html", "releases", "Release diff"),
    "F-V4-13": ("v4-verify.html", "", "This page"),
}

V4_SURFACE_ROWS = [
    (fid, "blocking" if sev == "high" else "gap",
     (_V4_TARGETS[fid][0], _V4_TARGETS[fid][1], _V4_TARGETS[fid][2], url),
     finding, disposition)
    for fid, sev, area, finding, disposition, url in V4_FLAGS
]
