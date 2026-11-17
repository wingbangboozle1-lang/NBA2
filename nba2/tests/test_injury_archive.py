"""Tests for the official injury-report archive (session arena/3a56251c-nba2, task 3A-03).

Tests that re-parse the PDFs need the optional ``pypdf`` package and skip without it, so the
standard-library CI run still checks the committed archive.json.
"""
import json
import unittest
from pathlib import Path

from nba2.injury_archive import archive as A
from nba2.injury_archive import view as V

try:
    import pypdf  # noqa: F401
    HAVE_PYPDF = True
except ImportError:  # pragma: no cover - depends on the environment
    HAVE_PYPDF = False

ROOT = Path(__file__).resolve().parents[2]


class StoredArchive(unittest.TestCase):
    """Checks that need only the committed JSON."""

    @classmethod
    def setUpClass(cls):
        cls.arch = json.loads((ROOT / "data/injuries/archive/archive.json").read_text())

    def test_four_releases_in_revision_order(self):
        ids = [r["release_id"] for r in self.arch["releases"]]
        self.assertEqual(ids, list(A.ORDER))
        times = [r["revision_time_et"] for r in self.arch["releases"]]
        self.assertEqual(times, sorted(times))

    def test_pdf_creation_time_matches_header_to_the_minute(self):
        for r in self.arch["releases"]:
            self.assertTrue(r["checks"]["pdf_creation_utc_matches_header"], r["release_id"])

    def test_zero_parse_problems_and_plain_text_counts(self):
        for r in self.arch["releases"]:
            c = r["checks"]
            self.assertEqual(c["parse_problems"], 0, r["release_id"])
            self.assertTrue(c["status_count_matches_plain_text"], r["release_id"])
            self.assertTrue(c["not_yet_submitted_matches_plain_text"], r["release_id"])
            self.assertTrue(c["every_player_name_in_plain_text"], r["release_id"])
            self.assertTrue(c["every_row_has_date_matchup_team"], r["release_id"])

    def test_statuses_are_printed_vocabulary_only(self):
        for r in self.arch["releases"]:
            for row in r["rows"]:
                self.assertIn(row["status"], A.STATUSES)

    def test_blank_time_is_never_borrowed(self):
        for r in self.arch["releases"]:
            blank = set(r["checks"]["blocks_without_printed_time"])
            for row in r["rows"] + r["team_not_submitted"]:
                if row["matchup"] in blank:
                    self.assertIsNone(row["time_et"], (r["release_id"], row["matchup"]))

    def test_newest_release_flags_new_york_knicks_absence(self):
        latest = self.arch["releases"][-1]
        self.assertIn("NYK@TOR", latest["checks"]["games_with_one_team_only"])
        teams = {row["team"] for row in latest["rows"] + latest["team_not_submitted"] if row["matchup"] == "NYK@TOR"}
        self.assertNotIn("New York Knicks", teams)

    def test_retrieval_only_where_recorded(self):
        by_id = {r["release_id"]: r for r in self.arch["releases"]}
        self.assertEqual(by_id["2026-11-16_0930AM"]["retrieved_at_utc"], "2026-11-16T14:52:00Z")
        self.assertEqual(by_id["2026-11-16_0100PM"]["retrieved_at_utc"], "2026-11-16T18:38:00Z")
        self.assertIsNone(by_id["2026-11-16_0215PM"]["retrieved_at_utc"])
        self.assertIsNone(by_id["2026-11-17_0945AM"]["retrieved_at_utc"])

    def test_committed_diffs_recompute_from_committed_rows(self):
        rels = {r["release_id"]: r for r in self.arch["releases"]}
        for d in self.arch["diffs"]:
            fresh = A.diff(rels[d["from"]], rels[d["to"]])
            self.assertEqual(fresh["counts"], d["counts"], (d["from"], d["to"]))
            self.assertEqual(fresh["status_changed"], d["status_changed"])
            self.assertEqual(fresh["added"], d["added"])
            self.assertEqual(fresh["removed"], d["removed"])

    def test_render_cites_every_release_pdf(self):
        def esc(x):
            return str(x)

        def srclink(url, label=None):
            return f'<a href="{url}">{label or url}</a>'

        def table(headers, rows, caption, **kw):
            return "\n".join(" | ".join(str(c) for c in r["cells"]) for r in rows)

        def badge(t, k="info"):
            return str(t)

        html = V.section_html(self.arch, esc, srclink, table, badge)
        for r in self.arch["releases"]:
            self.assertIn(r["pdf_url"], html)
        banner = V.banner_html(self.arch, esc, srclink)
        self.assertIn("2026-11-17 09:45 AM ET", banner)
        self.assertIn("not recorded", banner)


class DiffLogic(unittest.TestCase):
    """Pure logic on synthetic releases (no PDFs)."""

    def _rel(self, rid, rows, nys=()):
        return {"release_id": rid, "revision_time_et": rid, "rows": rows, "team_not_submitted": list(nys)}

    def test_added_removed_status_reason(self):
        base = dict(game_date="11/16/2026", matchup="A@B", team="Team A")
        old = self._rel("o", [
            dict(base, player="X, One", status="Out", reason="Ankle"),
            dict(base, player="Y, Two", status="Questionable", reason="Knee"),
        ])
        new = self._rel("n", [
            dict(base, player="X, One", status="Available", reason="Ankle"),
            dict(base, player="Y, Two", status="Questionable", reason="Hip"),
            dict(base, player="Z, Three", status="Out", reason="Calf"),
        ])
        d = A.diff(old, new)
        self.assertEqual(d["counts"]["added"], 1)
        self.assertEqual(d["counts"]["removed"], 0)
        self.assertEqual(d["counts"]["status_changed"], 1)
        self.assertEqual(d["counts"]["reason_changed"], 1)

    def test_not_submitted_transitions(self):
        nys = [{"game_date": "11/16/2026", "matchup": "A@B", "team": "Team B", "status_line": "NOT YET SUBMITTED"}]
        old = self._rel("o", [], nys)
        new = self._rel("n", [dict(game_date="11/16/2026", matchup="A@B", team="Team B", player="Q, R",
                                   status="Out", reason="x")])
        d = A.diff(old, new)
        self.assertEqual(d["team_newly_submitted"], [["11/16/2026", "A@B", "Team B"]])


@unittest.skipUnless(HAVE_PYPDF, "pypdf not installed: PDF re-parse tests skipped (CI runs the stored-JSON tests)")
class ReparsePDFs(unittest.TestCase):
    def test_fresh_build_equals_committed_archive(self):
        fresh = json.loads(json.dumps(A.build_all()))  # JSON round-trip: tuples become lists
        committed = json.loads((ROOT / "data/injuries/archive/archive.json").read_text())
        self.assertEqual(fresh["releases"], committed["releases"])
        self.assertEqual(fresh["diffs"], committed["diffs"])

    def test_stored_txt_agrees_where_present(self):
        for rid in A.ORDER:
            rel = A.build_release(rid)
            if rel["checks"]["stored_txt_present"]:
                self.assertTrue(rel["checks"]["stored_txt_matches_parsed"], rid)


if __name__ == "__main__":
    unittest.main()
