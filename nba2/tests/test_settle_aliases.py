"""Regression tests for 0B9-7: settlement union reads each official feed's own key names,
and quarter rows are taken per side across sources.

Defect (measured on the committed tree, 2026-11-19): data/raw/finals_2026-11-17.json uses
away_team / home_team / away_q / home_q / final_source_url, which normalise_source did not
read, so games 0022600253-57 lost their clubs and quarter rows. Every test writes only to a
temporary directory; nothing under data/ is touched.
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


class FeedAliasTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.d = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_feed_with_team_and_quarter_aliases_keeps_clubs_and_quarters(self):
        # Shape of data/raw/finals_2026-11-17.json (sums checked: 23+31+26+31=111, 29+21+33+19=102)
        p = _write(self.d, "finals_2026-11-17.json", {"records": [{
            "game_id": "0022600253", "date": "2026-11-17", "home_team": "TOR", "away_team": "NYK",
            "home_pts": 102, "away_pts": 111, "status": "final",
            "final_source_url": "https://www.nba.com/game/nyk-vs-tor-0022600253",
            "home_q": [29, 21, 33, 19], "away_q": [23, 31, 26, 31], "ot_periods": 0,
            "source": "https://www.nba.com/game/nyk-vs-tor-0022600253"}]})
        u = S.build_union([p])
        self.assertEqual(u["conflicts"], [])
        self.assertEqual(u["rejected_quarter_rows"], [])
        r = u["records"][0]
        self.assertEqual((r["away"], r["home"]), ("NYK", "TOR"))
        self.assertEqual(r["away_quarters"], [23, 31, 26, 31])
        self.assertEqual(r["home_quarters"], [29, 21, 33, 19])
        self.assertEqual(r["source"], "https://www.nba.com/game/nyk-vs-tor-0022600253")

    def test_quarter_rows_are_merged_per_side_across_sources(self):
        # Source A carries only the away row, source B only the home row (the 0022600240 shape).
        a = _write(self.d, "a.json", {"records": [{
            "game_id": "G1", "away": "DAL", "home": "BOS", "away_pts": 94, "home_pts": 131,
            "status": "final", "away_quarters": [9, 28, 34, 23], "home_quarters": None}]})
        b = _write(self.d, "b.json", {"records": [{
            "game_id": "G1", "away": "DAL", "home": "BOS", "away_pts": 94, "home_pts": 131,
            "status": "final", "away_quarters": None, "home_quarters": [42, 25, 37, 27]}]})
        r = S.build_union([a, b])["records"][0]
        self.assertEqual(r["away_quarters"], [9, 28, 34, 23])
        self.assertEqual(r["home_quarters"], [42, 25, 37, 27])
        self.assertEqual(sum(r["away_quarters"]), r["away_pts"])
        self.assertEqual(sum(r["home_quarters"]), r["home_pts"])

    def test_a_quarter_row_that_does_not_sum_is_still_rejected(self):
        p = _write(self.d, "bad.json", {"records": [{
            "game_id": "G2", "away": "A", "home": "B", "away_pts": 90, "home_pts": 100,
            "status": "final", "away_quarters": [20, 20, 20, 20], "home_quarters": [25, 25, 25, 25]}]})
        # Existing rule: the source is ignored for this game, so with no other source there is no record.
        u = S.build_union([p])
        self.assertEqual(len(u["rejected_quarter_rows"]), 1)
        self.assertEqual(u["records"], [])
        # With a second source that checks out, the record exists and carries only checked rows.
        good = _write(self.d, "good.json", {"records": [{
            "game_id": "G2", "away": "A", "home": "B", "away_pts": 90, "home_pts": 100,
            "status": "final", "away_quarters": [22, 22, 23, 23], "home_quarters": [25, 25, 25, 25]}]})
        r = S.build_union([p, good])["records"][0]
        self.assertEqual(r["away_quarters"], [22, 22, 23, 23])
        self.assertEqual(r["home_quarters"], [25, 25, 25, 25])

    def test_missing_value_in_one_feed_does_not_erase_another_feeds_club(self):
        a = _write(self.d, "a.json", {"records": [{
            "game_id": "G3", "away": None, "home": None, "away_pts": 1, "home_pts": 2, "status": "final"}]})
        b = _write(self.d, "b.json", {"records": [{
            "game_id": "G3", "away_team": "IND", "home_team": "NYK", "away_pts": 1, "home_pts": 2,
            "status": "final"}]})
        r = S.build_union([a, b])["records"][0]
        self.assertEqual((r["away"], r["home"]), ("IND", "NYK"))


if __name__ == "__main__":
    unittest.main()
