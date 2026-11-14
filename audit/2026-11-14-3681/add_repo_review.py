"""Append session arena/3681def8-nba2's line-by-line repository findings.

Every finding below was produced by executing something in this session — a command, a
diff, or a fetch — not by reading a summary. The `evidence` field quotes the command or
the document, and the `action` field says what was done or what is being left for the
owner. Findings on files owned by other sessions are logged, never edited.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

NEW = [
    {
        "id": "RR-19",
        "source_key": "git_repo",
        "area": "Verification checker",
        "finding": (
            "crosscheck CC-SEAL-04 reports five sealed predictions as 'not tipped after the "
            "snapshot'. It compares calendar dates, not timestamps, and it is wrong: the "
            "2026-11-14 ledger was sealed 2026-11-14T00:58:54Z and the earliest game in it "
            "tips 2026-11-14 19:00 ET = 2026-11-15T00:00Z. The true minimum lead time across "
            "all 27 predictions is 23.02 hours."
        ),
        "evidence": (
            "`python3` over data/raw/ledger/sealed-2026-11-14.json: header.sealed_at_utc = "
            "2026-11-14T00:58:54Z; min over predictions of (date+time_et at UTC-5) - seal = "
            "23.02 h (0022600231), 23.52 h (0022600232), 24.02 h (0022600233/34)."
        ),
        "action": (
            "Logged, not fixed: tools/crosscheck_site.py is owned by session arena/5b80b88a. "
            "The check should compare datetimes (tip_utc > seal_utc), not dates. This also "
            "answers Q-31's underlying worry in the affirmative for this ledger — it really "
            "was sealed before every tip."
        ),
        "flags": ["FLAG-SEAL-05"],
    },
    {
        "id": "RR-20",
        "source_key": "git_repo",
        "area": "Snapshot schema",
        "finding": (
            "tools/crosscheck_site.py globs data/raw/injury_report_*.json and indexes every "
            "file it finds by ['columns'] + list-of-list ['records'] + ['record_counts']. A "
            "snapshot written in any other shape crashes the whole checker with KeyError, "
            "which silently removes 94 semantic checks from the repo's verification surface."
        ),
        "evidence": (
            "tools/crosscheck_site.py:249 raises KeyError: 'columns' on "
            "data/raw/injury_report_2026-11-14_0500AM.json, which was first written this "
            "session as list-of-dicts with a 'counts_check' key."
        ),
        "action": (
            "Fixed on the data side rather than by editing another session's tool: the new "
            "snapshot is now written in the established schema (columns, list records, "
            "record_counts, attribution), so the checker runs again — 94 checks."
        ),
        "flags": ["FLAG-REPO-01"],
    },
    {
        "id": "RR-21",
        "source_key": "git_repo",
        "area": "Data provenance",
        "finding": (
            "Two independent transcriptions of the same official injury release disagree on "
            "the wording, and only the wording, of the not-yet-submitted Reason cell: one "
            "records the PDF's literal 'NOT YET SUBMITTED', the other a descriptive sentence "
            "'Team submission outstanding at report time'. Status values agree on all 31 rows."
        ),
        "evidence": (
            "audit/2026-11-14-3681/verify_live.py check C3-C: after normalising the two "
            "spellings, 31 rows vs 31 rows, 0 rows only in one, 0 value differences. Before "
            "normalising it reported 5 'differences', all of them this wording."
        ),
        "action": (
            "Both spellings are legitimate renderings of the same cell; the comparison now "
            "normalises them and says so in the code. No value on the site changed."
        ),
        "flags": ["FLAG-REPO-01"],
    },
    {
        "id": "RR-22",
        "source_key": "git_repo",
        "area": "Published site",
        "finding": (
            "Six site trees are served from one Pages origin: the root v1 tree (index.html + "
            "pages/), site/ (v2), docs/, dashboard/, originated/ and backtest/. They overlap "
            "in content and were built at different times, so the same question has several "
            "answers depending on which URL a reader lands on."
        ),
        "evidence": (
            "`gh api repos/wingbangboozle1-lang/NBA2/pages` -> build_type 'legacy', "
            "source main / — so root v1 is what visitors get; the other five are reachable "
            "at /NBA2/<tree>/. Raised as Q-34 and S-32 for the owner."
        ),
        "action": (
            "Not changed: switching the canonical tree changes every page a reader sees. "
            "Logged for an owner decision; the root tree carries all of this session's tables."
        ),
        "flags": ["FLAG-REPO-01"],
    },
    {
        "id": "RR-23",
        "source_key": "git_repo",
        "area": "Derived counts",
        "finding": (
            "The availability-coverage column computed 'no rows yet' as slots - filed - "
            "not_yet_submitted, but filed and not_yet_submitted are not disjoint: a club can "
            "file in one release and still read NOT YET SUBMITTED in another. The result can "
            "go negative, and a value of -5 was live on the site for 2026-11-14."
        ),
        "evidence": (
            "Raised as finding F1 / CR-1 by session arena/5b80b88a against "
            "nba2/pipeline/build_site_data.py:487-491; reproduced again this session as "
            "crosscheck CC-DER-12 once the 11/15 date entered the window."
        ),
        "action": (
            "Fixed: the club is counted as not-submitted only when it has no designation in "
            "any committed release, so the three count columns are disjoint and sum to the "
            "team-slot count exactly. CC-DER-12 now passes."
        ),
        "flags": ["FLAG-REPO-01"],
    },
    {
        "id": "RR-24",
        "source_key": "git_repo",
        "area": "Mislabelled column",
        "finding": (
            "The ratings table's column labelled 'W-L (official NBA.com)' was populated from "
            "the same third-party field as the neighbouring 'W-L (ratings source)' column, so "
            "the table's own guard — 'if they ever disagree, the table is wrong' — could never "
            "fire."
        ),
        "evidence": (
            "nba2/pipeline/build_site_data.py set both `wl` and `wl_official` to "
            "f\"{t.wins}-{t.losses}\" from the basketball-reference snapshot. Measured by "
            "crosscheck CC-DER-05 and logged as CR-4 by session arena/5b80b88a."
        ),
        "action": (
            "Fixed with a genuinely independent source: the official column now reads "
            "data/raw/standings_2026-11-14_official.json (nba.com/standings, captured this "
            "session). A new Difference column shows that the two differ by exactly the "
            "2026-11-13 result for every club that played that night. CC-DER-05 now passes."
        ),
        "flags": ["FLAG-REPO-01"],
    },
    {
        "id": "RR-25",
        "source_key": "git_repo",
        "area": "Hard-coded coverage",
        "finding": (
            "The corroboration table's verdict for uncorroborated games hard-coded the "
            "claimed coverage window as '11/13 + 11/14'. The sentence is currently true but "
            "was written by hand, so it would keep asserting a coverage window that had "
            "moved the moment another release was ingested."
        ),
        "evidence": (
            "nba2/pipeline/build_site_data.py, build_corroboration_rows: the not-covered "
            "verdict was a literal string; crosscheck CC-PUB-05 flagged the 11/15 rows."
        ),
        "action": (
            "Fixed: the coverage dates are now derived from the corroborating snapshots "
            "themselves and rendered into the verdict. CC-PUB-05 now passes."
        ),
        "flags": ["FLAG-REPO-01"],
    },
    {
        "id": "RR-26",
        "source_key": "git_repo",
        "area": "Coordination",
        "finding": (
            "Pull request #21 (arena/79e87c81-nba2, 'Roll the pick window forward to "
            "2026-11-14..11-17 and refresh the official snapshots') has been open since "
            "2026-11-14 00:52 UTC with no commits for roughly ten hours, and its substance "
            "was delivered by PR #38."
        ),
        "evidence": (
            "`gh pr list --state open` at 2026-11-14 ~10:20 UTC -> PR #21 only, opened "
            "2026-11-14T00:52:16Z; the window it asks for is the one currently published."
        ),
        "action": (
            "Left open: the branch belongs to another session and the coordination rules say "
            "a stale claim may be taken over, not that a PR may be closed out from under "
            "someone. Flagged so the owner can close it as superseded."
        ),
        "flags": ["FLAG-REPO-01"],
    },
    {
        "id": "RR-27",
        "source_key": "git_repo",
        "area": "Documentation drift",
        "finding": (
            "README.md hand-copies the artefact counts (pages, tables, rows), and they go "
            "stale on essentially every build: this session found 19 pages / 39 tables / "
            "1124 rows claimed against 20 / 43 / 1223 on disk."
        ),
        "evidence": (
            "crosscheck CC-DOC-01: '3 stale figure(s)'. The same class of drift was logged as "
            "finding F2 / CR-2 / S-27 by session arena/5b80b88a."
        ),
        "action": (
            "Corrected again for this build, and S-27 (generate the block instead of copying "
            "it) is re-recommended. A recurring manual correction is not a fix."
        ),
        "flags": ["FLAG-REPO-01"],
    },
    {
        "id": "RR-28",
        "source_key": "git_repo",
        "area": "Environment",
        "finding": (
            "Direct HTTP egress from this workspace to every nba.com host fails (curl returns "
            "HTTP 000 for www.nba.com, ak-static.cms.nba.com and stats.nba.com), while the "
            "platform page-fetch tool reaches www.nba.com and the referee-operations PDFs. "
            "Prior sessions recorded the official sources as simply 'unreachable'."
        ),
        "evidence": (
            "`curl -s -o /dev/null -w '%{http_code}' --max-time 8 https://www.nba.com/` -> 000 "
            "(github.com -> 200 in the same run); fetch of "
            "https://www.nba.com/schedule?date=2026-11-14 returned the live Week 4 grid, and "
            "Injury-Report_2026-11-14_05_00AM.pdf returned its full table."
        ),
        "action": (
            "Used the working path: every value added this session was read from a document "
            "fetched in this session, and each snapshot records the retrieval method as well "
            "as the URL and time. The 'blocked' labels on stats.nba.com and cdn.nba.com are "
            "still correct — those remain unreachable either way."
        ),
        "flags": ["FLAG-REPO-01"],
    },
]


def main() -> None:
    path = ROOT / "requirements" / "REPO_REVIEW.json"
    doc = json.loads(path.read_text())
    have = {r["id"] for r in doc["requirements"]}
    added = [r for r in NEW if r["id"] not in have]
    doc["requirements"].extend(added)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    print(f"repo review: +{added and len(added) or 0} (now {len(doc['requirements'])})")


if __name__ == "__main__":
    main()
