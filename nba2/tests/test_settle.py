"""Settlement union: keyed by game_id, conflict-aware, quarter-checked, fail-closed.

Every test writes only to a temporary directory; nothing under data/ is touched.
"""

import json
import tempfile
import unittest
from pathlib import Path

from nba2.pipeline import settle as S


def _write(d: Path, name: str, doc: dict) -> Path:
    p = d / name
    p.write_text(json.dumps(doc))
    return p


class UnionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.d = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_union_reads_every_source_not_just_newest_by_name(self):
        # The IR-1 defect: 'finals_all.json' sorts last by name and hid the 11/15-style feed.
        a = _write(self.d, "finals_all.json", {"records": [
            {"game_id": "0022600034", "home_pts": 106, "away_pts": 104, "source": "u1"}]})
        b = _write(self.d, "results_2026-11-14.json", {"records": [
            {"game_id": "0022600231", "date": "2026-11-14", "away": "DEN", "home": "NOP",
             "away_pts": 116, "home_pts": 108, "away_quarters": [29, 27, 30, 30],
             "home_quarters": [23, 28, 31, 26], "status": "final", "source_url": "u2"}]})
        doc = S.build_union([a, b])
        ids = {r["game_id"] for r in doc["records"]}
        self.assertEqual(ids, {"0022600034", "0022600231"})
        self.assertEqual(doc["conflicts"], [])

    def test_conflicting_scores_exclude_the_game(self):
        a = _write(self.d, "finals_a.json", {"records": [
            {"game_id": "1", "home_pts": 100, "away_pts": 90, "source": "a"}]})
        b = _write(self.d, "finals_b.json", {"records": [
            {"game_id": "1", "home_pts": 101, "away_pts": 90, "source": "b"}]})
        doc = S.build_union([a, b])
        self.assertEqual(doc["records"], [])
        self.assertEqual(doc["conflicts"][0]["game_id"], "1")
        self.assertIn("score", doc["conflicts"][0]["reason"])

    def test_agreeing_duplicates_collapse_to_one_record_listing_both_sources(self):
        a = _write(self.d, "finals_a.json", {"records": [
            {"game_id": "7", "home_pts": 100, "away_pts": 90, "source": "a"}]})
        b = _write(self.d, "finals_b.json", {"records": [
            {"game_id": "7", "home_pts": 100, "away_pts": 90, "source": "b"}]})
        doc = S.build_union([a, b])
        self.assertEqual(len(doc["records"]), 1)
        self.assertEqual(len(doc["records"][0]["sources"]), 2)

    def test_quarter_row_that_does_not_sum_is_rejected_not_used(self):
        a = _write(self.d, "results_x.json", {"records": [
            {"game_id": "9", "away": "AAA", "home": "BBB", "away_pts": 100, "home_pts": 90,
             "away_quarters": [25, 25, 25, 24], "home_quarters": [20, 20, 25, 25], "status": "final"}]})
        doc = S.build_union([a])
        self.assertEqual(doc["records"], [])
        self.assertEqual(len(doc["rejected_quarter_rows"]), 1)

    def test_not_final_status_carries_no_score(self):
        a = _write(self.d, "results_y.json", {"records": [
            {"game_id": "5", "away": "AAA", "home": "BBB", "away_pts": 60, "home_pts": 62,
             "status": "not final at retrieval"}]})
        doc = S.build_union([a])
        self.assertEqual(doc["records"], [])
        self.assertEqual(doc["conflicts"], [])

    def test_overtime_periods_count_toward_the_final(self):
        a = _write(self.d, "results_ot.json", {"records": [
            {"game_id": "10", "away": "NYK", "home": "TOR", "away_pts": 112, "home_pts": 108,
             "away_quarters": [23, 24, 20, 28], "home_quarters": [17, 26, 31, 21],
             "ot_periods": 1, "ot_quarters": {"away": [17], "home": [13]}, "status": "final"}]})
        doc = S.build_union([a])
        self.assertEqual(len(doc["records"]), 1)
        self.assertEqual(doc["rejected_quarter_rows"], [])

    def test_null_quarters_are_allowed_and_not_back_solved(self):
        a = _write(self.d, "results_z.json", {"records": [
            {"game_id": "6", "away": "AAA", "home": "BBB", "away_pts": 94, "home_pts": 131,
             "away_quarters": None, "home_quarters": [42, 25, 37, 27], "status": "final"}]})
        doc = S.build_union([a])
        self.assertEqual(len(doc["records"]), 1)
        self.assertIsNone(doc["records"][0]["away_quarters"])
        self.assertEqual(doc["records"][0]["home_quarters"], [42, 25, 37, 27])

    def test_club_disagreement_excludes_the_game(self):
        a = _write(self.d, "results_p.json", {"records": [
            {"game_id": "8", "away": "AAA", "home": "BBB", "away_pts": 1, "home_pts": 2, "status": "final"}]})
        b = _write(self.d, "results_q.json", {"records": [
            {"game_id": "8", "away": "CCC", "home": "BBB", "away_pts": 1, "home_pts": 2, "status": "final"}]})
        doc = S.build_union([a, b])
        self.assertEqual(doc["records"], [])
        self.assertIn("clubs", doc["conflicts"][0]["reason"])

    def test_a_feed_that_names_its_link_final_source_url_still_carries_one(self):
        """The v4 gamebook feed has no ``source_url``; reading only that spelling lost the link.

        Before this guard the eight 2026-11-16 records reached the union with an empty
        ``source``, so the published results page showed scores with no way back to the league.
        """
        a = _write(self.d, "results_2026-11-16.json", {"records": [
            {"game_id": "0022600249", "date": "2026-11-16", "away": "HOU", "home": "MIA",
             "away_pts": 110, "home_pts": 128, "status": "final",
             "final_source_url": "https://www.nba.com/game/hou-vs-mia-0022600249",
             "gamebook_url": "https://statsdmz.nba.com/pdfs/20261116/20261116_HOUMIA_book.pdf"}]})
        doc = S.build_union([a])
        self.assertEqual(doc["records"][0]["source"],
                         "https://www.nba.com/game/hou-vs-mia-0022600249")

    def test_a_feed_that_spells_quarters_away_q_keeps_them_after_the_sum_check(self):
        """Same defect on the period rows: ``away_q``/``home_q`` were dropped, not checked."""
        a = _write(self.d, "results_2026-11-16.json", {"records": [
            {"game_id": "0022600249", "date": "2026-11-16", "away": "HOU", "home": "MIA",
             "away_pts": 110, "home_pts": 128, "status": "final",
             "away_q": [15, 31, 35, 29], "home_q": [29, 33, 39, 27],
             "final_source_url": "https://www.nba.com/game/hou-vs-mia-0022600249"}]})
        r = S.build_union([a])["records"][0]
        self.assertEqual(r["away_quarters"], [15, 31, 35, 29])
        self.assertEqual(r["home_quarters"], [29, 33, 39, 27])

    def test_a_feed_whose_quarters_do_not_sum_is_still_rejected_in_the_new_spelling(self):
        a = _write(self.d, "results_2026-11-16.json", {"records": [
            {"game_id": "0022600249", "date": "2026-11-16", "away": "HOU", "home": "MIA",
             "away_pts": 110, "home_pts": 128, "status": "final",
             "away_q": [15, 31, 35, 30], "home_q": [29, 33, 39, 27],
             "final_source_url": "https://www.nba.com/game/hou-vs-mia-0022600249"}]})
        doc = S.build_union([a])
        # A bad period row makes the whole reading untrusted, so the game is dropped rather
        # than published with the good half kept: a period-row sum mismatch excludes the game.
        self.assertEqual(len(doc["rejected_quarter_rows"]), 1)
        self.assertEqual(doc["records"], [])

    def test_committed_union_has_no_conflicts_and_only_official_scores(self):
        # Runs against the committed tree: every committed official source must agree.
        doc = S.build_union()
        self.assertEqual(doc["conflicts"], [], doc["conflicts"])
        for r in doc["records"]:
            self.assertTrue(r["source"], f"{r['game_id']} has no source link")


if __name__ == "__main__":
    unittest.main()
