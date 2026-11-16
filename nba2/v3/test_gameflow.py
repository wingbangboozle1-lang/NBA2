"""Tests for the late-game / garbage-time decomposition (nba2/v3/gameflow.py).

The decomposition is pure arithmetic over committed official quarter scores, so every
value here is re-derived by hand from the same numbers the module reads.
"""

from __future__ import annotations

import unittest

from nba2.v3 import gameflow as GF


class TestQuarterGames(unittest.TestCase):
    def test_coverage_counts_are_consistent(self):
        d = GF.decomposition()
        s = d["summary"]
        # 9 games of 2026-11-13 (gamebooks) + 5 of 2026-11-14 (LINESCORE) = 14 rows
        self.assertEqual(s["n_games_total"], 14)
        self.assertEqual(s["n_games_with_quarters"] + s["n_games_missing_quarters"],
                         s["n_games_total"])

    def test_missing_quarters_are_flagged_not_inferred(self):
        d = GF.decomposition()
        missing = [r for r in d["rows"] if r["quarters_txt"] is None]
        self.assertTrue(missing, "there must be games without quarters to prove the blank path")
        for r in missing:
            self.assertIsNone(r["adj_total"])
            self.assertIsNone(r["inflation"])
            # a blank must carry an explanation (flag id or blocked phrase)
            self.assertTrue(r["flag"], f"{r['matchup']} blank has no reason")


class TestDecomposition(unittest.TestCase):
    def test_inflation_is_q4_minus_early_mean(self):
        # NYK@IND 2026-11-13: away 27/22/35/20, home 26/32/27/21
        # combined Q1..Q4 = 53, 54, 62, 41 ; early mean = (53+54+62)/3 = 56.333
        # inflation = 41 - 56.333 = -15.333
        rows = {r["matchup"]: r for r in GF.decomposition()["rows"]}
        r = rows["NYK @ IND"]
        self.assertEqual(r["early_total"], 169.0)   # 53+54+62
        self.assertEqual(r["late_total"], 41.0)      # Q4 combined
        self.assertAlmostEqual(r["early_rate"], 56.33, places=2)
        self.assertAlmostEqual(r["inflation"], -15.33, places=2)
        # adj_total = early_total + early_rate
        self.assertAlmostEqual(r["adj_total"], 169.0 + 56.33, places=1)

    def test_overtime_game_uses_regulation_quarters_only(self):
        # ATL@CHI went to OT: away 24/29/30/27/7, home 33/27/24/26/15
        # regulation combined Q1..Q4 = 57, 56, 54, 53 ; OT combined = 22
        rows = {r["matchup"]: r for r in GF.decomposition()["rows"]}
        r = rows["ATL @ CHI"]
        self.assertEqual(r["ot"], 22)
        self.assertEqual(r["early_total"], 167.0)   # 57+56+54
        self.assertEqual(r["late_total"], 53.0)      # regulation Q4 only
        # the OT points must NOT leak into the inflation / adj_total
        self.assertNotIn("ot", [k for k in r if k in ("early_total", "late_total")])

    def test_late_inflated_is_positive_only(self):
        # CLE@MIA: Q4 combined 71 vs early mean 61 -> inflation +10, the largest
        # positive inflation in the window; it must be flagged inflated, not deflated.
        rows = {r["matchup"]: r for r in GF.decomposition()["rows"]}
        r = rows["CLE @ MIA"]
        self.assertGreater(r["inflation"], 0)
        if r["inflation_z"] is not None:
            self.assertEqual(r["late_inflated"], r["inflation_z"] > GF.NOISE_BAND_Z)
            self.assertEqual(r["late_deflated"], r["inflation_z"] < -GF.NOISE_BAND_Z)

    def test_summary_counts_match_rows(self):
        d = GF.decomposition()
        s = d["summary"]
        self.assertEqual(s["n_late_inflated"],
                         sum(1 for r in d["rows"] if r["late_inflated"] is True))
        self.assertEqual(s["n_late_deflated"],
                         sum(1 for r in d["rows"] if r["late_deflated"] is True))
        self.assertEqual(s["n_overtime"], sum(1 for r in d["rows"] if r.get("ot")))

    def test_sources_are_official_urls(self):
        for r in GF.decomposition()["rows"]:
            self.assertTrue(r["source_url"].startswith("https://"),
                            f"{r['matchup']} source is not an official https URL")


if __name__ == "__main__":
    unittest.main()
