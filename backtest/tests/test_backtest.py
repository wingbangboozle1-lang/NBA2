"""Tests for the measured-skill backtest.

These do not test whether the model is good — they test whether the report is *honest*:

* no leakage between games on the same date,
* the statistics are the estimators they claim to be,
* the leaderboard cannot pay a reward while a gate fails,
* the pipeline is deterministic and every game keeps a source.
"""

from __future__ import annotations

import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backtest.engine import (correlation, gates, leaderboard, skill,  # noqa: E402
                             stats, walkforward)


class TestStats(unittest.TestCase):
    def test_wilson_contains_estimate_and_bounds(self):
        lo, hi = stats.wilson_interval(60, 100)
        self.assertLess(lo, 0.60)
        self.assertGreater(hi, 0.60)
        self.assertGreaterEqual(lo, 0.0)
        self.assertLessEqual(hi, 1.0)

    def test_wilson_unanimous_is_not_degenerate(self):
        lo, hi = stats.wilson_interval(10, 10)
        self.assertLess(lo, 1.0, "a perfect record must not claim certainty")

    def test_wilson_needs_observations(self):
        self.assertIsNone(stats.wilson_interval(0, 0))

    def test_auc_is_half_for_uninformative_score(self):
        # positives and negatives are interleaved, so the score carries no ranking signal
        self.assertAlmostEqual(stats.auc([1, 1, 1, 1], [0, 1, 0, 1]), 0.5, places=9)
        # an anti-correlated score: only 1 of 4 positive/negative pairs is ordered correctly
        self.assertAlmostEqual(stats.auc([3, 4, 1, 2], [1, 0, 1, 0]), 0.25, places=9)

    def test_auc_is_one_for_perfect_score(self):
        self.assertEqual(stats.auc([1, 2, 3, 4], [0, 0, 1, 1]), 1.0)

    def test_auc_handles_ties(self):
        self.assertAlmostEqual(stats.auc([5, 5, 5, 5], [0, 1, 0, 1]), 0.5, places=9)

    def test_pearson_perfect_lines(self):
        self.assertAlmostEqual(stats.pearson([1, 2, 3, 4], [2, 4, 6, 8]), 1.0, places=9)
        self.assertAlmostEqual(stats.pearson([1, 2, 3, 4], [8, 6, 4, 2]), -1.0, places=9)

    def test_pearson_none_on_degenerate(self):
        self.assertIsNone(stats.pearson([1, 1, 1], [1, 2, 3]))

    def test_spearman_ignores_scale(self):
        a = [1, 2, 3, 4, 5]
        b = [10, 20, 30, 40, 50]
        self.assertAlmostEqual(stats.spearman(a, b), 1.0, places=9)

    def test_brier_bounds(self):
        self.assertAlmostEqual(stats.brier([0.5, 0.5], [1, 0]), 0.25, places=9)
        self.assertAlmostEqual(stats.brier([1.0, 0.0], [1, 0]), 0.0, places=9)

    def test_permutation_is_deterministic(self):
        a = [1.0, 2.0, 3.0, 4.0, 5.0]
        b = [6.0, 7.0, 8.0, 9.0, 10.0]
        r1 = stats.permutation_test(a, b, draws=500)
        r2 = stats.permutation_test(a, b, draws=500)
        self.assertEqual(r1, r2, "same seed must give the same p-value")

    def test_permutation_detects_large_shift(self):
        a = [1.0] * 30
        b = [100.0] * 30
        self.assertLess(stats.permutation_test(a, b, draws=1000)["p_value"], 0.01)

    def test_power_increases_with_smaller_edge(self):
        big = stats.power_n(0.5, 0.60)
        small = stats.power_n(0.5, 0.52)
        self.assertLess(big, small, "a larger true edge needs fewer games")
        self.assertGreater(big, 0)

    def test_power_none_for_no_edge(self):
        self.assertIsNone(stats.power_n(0.5, 0.5))


class TestWalkForward(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.games = walkforward.load_games()
        cls.rows = walkforward.walk_forward(cls.games)

    def test_history_loaded(self):
        self.assertGreater(len(self.games), 100)

    def test_no_duplicate_game_ids(self):
        ids = [g["game_id"] for g in self.games]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_game_has_official_source(self):
        for g in self.games:
            self.assertTrue(g["source_url"].startswith("https://www.nba.com/game/"),
                            g["game_id"])

    def test_no_leakage(self):
        # raises AssertionError if any row used information from its own date or later
        walkforward.assert_no_leakage(self.rows, self.games)

    def test_first_team_games_are_blocked(self):
        first_date = min(g["date"] for g in self.games)
        first = [r for r in self.rows if r.date == first_date]
        self.assertTrue(all(r.pred_margin_home is None for r in first),
                        "opening night must have no rating to lean on")
        self.assertTrue(all(r.tier == "BLOCKED" for r in first))

    def test_ratings_are_seeded_not_inherited(self):
        # every team's first game must be unpriced
        seen = set()
        for r in sorted(self.rows, key=lambda r: (r.date, r.game_id)):
            if r.away not in seen or r.home not in seen:
                self.assertIsNone(r.pred_margin_home,
                                  f"{r.game_id}: priced a game with an unplayed team")
            seen.add(r.away)
            seen.add(r.home)

    def test_shrink_is_zero_with_no_evidence(self):
        self.assertEqual(walkforward.shrink(5.0, 0), 0.0)

    def test_shrink_approaches_raw_value(self):
        self.assertAlmostEqual(walkforward.shrink(5.0, 100000), 5.0, places=2)

    def test_hca_starts_neutral(self):
        self.assertEqual(walkforward.estimate_hca([]), 0.0)

    def test_hca_bounded_by_observed(self):
        v = walkforward.estimate_hca([4.0] * 100)
        self.assertLess(v, 4.0, "shrinkage must pull toward zero")

    def test_outcome_arithmetic(self):
        for r in self.rows:
            self.assertEqual(r.actual_margin_home, r.home_pts - r.away_pts)
            self.assertEqual(r.actual_total, r.home_pts + r.away_pts)
            if r.margin_error is not None:
                self.assertAlmostEqual(r.margin_error, r.pred_margin_home - r.actual_margin_home,
                                       places=2)

    def test_deterministic(self):
        again = walkforward.walk_forward(self.games)
        self.assertEqual([r.as_dict() for r in self.rows], [r.as_dict() for r in again])


class TestSkill(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.games = walkforward.load_games()
        cls.rows = [r.as_dict() for r in walkforward.walk_forward(cls.games)]

    def test_accuracy_counts_match(self):
        acc = skill.accuracy_block(self.rows)
        graded = [r for r in self.rows if r["pred_margin_home"] is not None]
        self.assertEqual(acc["n"], len(graded))

    def test_mae_below_rmse(self):
        acc = skill.accuracy_block(self.rows)
        self.assertLess(acc["margin_mae_model"], acc["margin_rmse_model"])

    def test_baseline_uses_same_games(self):
        nb = skill.naive_baselines(self.rows, self.games)
        self.assertEqual(nb["always_home"]["hits"] + 0,
                         sum(1 for r in self.rows
                             if r["pred_margin_home"] is not None and r["actual_margin_home"] > 0))

    def test_calibration_bins_cover_all_graded(self):
        cal = skill.calibration_table(self.rows)
        graded = [r for r in self.rows if r["p_home"] is not None]
        self.assertEqual(sum(c["n"] for c in cal), len(graded))

    def test_ats_reports_self_consistency_caveat(self):
        ats = skill.ats_block(self.rows)
        self.assertIn("Self-consistency only", ats["note"])

    def test_empty_input_is_handled(self):
        self.assertEqual(skill.accuracy_block([])["n"], 0)
        self.assertEqual(skill.ats_block([])["n"], 0)


class TestCorrelation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.games = walkforward.load_games()
        cls.rows = [r.as_dict() for r in walkforward.walk_forward(cls.games)]

    def test_margin_total_uses_all_games(self):
        c = correlation.margin_total_correlation(self.games)
        self.assertEqual(c["n"], len(self.games))

    def test_leg_cells_sum_to_n(self):
        c = correlation.leg_dependence(self.rows)
        self.assertEqual(sum(c["cells"].values()), c["n"])

    def test_rest_requires_history(self):
        r = correlation.rest_effects(self.games[:2])
        self.assertEqual(r["b2b"]["n"], 0, "two games cannot produce a back-to-back")


class TestGatesAndLeaderboard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.games = walkforward.load_games()
        cls.rows = [r.as_dict() for r in walkforward.walk_forward(cls.games)]
        cls.corr = correlation.margin_total_correlation(cls.games)
        cls.gres = gates.evaluate(cls.rows, cls.corr)

    def test_all_registered_gates_are_present(self):
        gids = set(self.gres["gates"])
        for expected in ("G-01", "G-02", "G-04", "G-07"):
            self.assertIn(expected, gids)

    def test_gate_statuses_are_from_the_allowed_set(self):
        for g in self.gres["gates"].values():
            self.assertIn(g["status"], {"PASS", "FAIL", "PARTIAL", "BLOCKED"})

    def test_blocked_gates_are_not_counted_as_passed(self):
        g = self.gres["gates"]
        self.assertNotIn("G-02", self.gres["summary"]["passed"])
        self.assertNotIn("G-09", self.gres["summary"]["passed"])

    def test_small_sample_fails_gate_01(self):
        self.assertEqual(self.gres["gates"]["G-01"]["status"], "FAIL")

    def test_gate_04_is_disputed_not_accepted(self):
        """A pass won against an unshrunk raw differential is a strawman.

        The registered baseline (b) reads up to -66 points in week one, so any sane model beats
        it. Measured against a shrunk differential with no home-court term, the model is WORSE.
        The gate must therefore never be counted as evidence of skill.
        """
        g4 = self.gres["gates"]["G-04"]
        self.assertTrue(g4["disputed"], "G-04 must not be accepted on a strawman baseline")
        self.assertLessEqual(g4["gain_from_home_court"], 0.0)
        self.assertNotIn("G-04", self.gres["summary"]["passed_reliable"])
        self.assertIn("G-04", self.gres["summary"]["passed_disputed"])

    def test_strawman_baseline_is_absurd_on_purpose(self):
        """Documents the defect: the registered baseline is worse than predicting zero."""
        g4 = self.gres["gates"]["G-04"]
        # baseline (b) is worse than the 0.0-spread baseline (a)
        self.assertGreater(g4["baseline_c_shrunk_net_no_hca"] - g4["gain_from_shrinkage"], 0)

    def test_disputed_gates_earn_no_reward_fraction(self):
        board = leaderboard.build(self.rows, self.gres, len(self.games))
        for row in board:
            self.assertNotIn("G-04", row["gates_counted"])
            self.assertIn("G-04", row["gates_disputed_excluded"])

    def test_no_reward_when_any_gate_fails(self):
        board = leaderboard.build(self.rows, self.gres, len(self.games))
        if self.gres["summary"]["failed"]:
            for row in board:
                self.assertEqual(row["reward_units"], 0.0,
                                 f"{row['strategy']} was paid while a gate failed")

    def test_ranking_is_by_deflated_z(self):
        board = leaderboard.build(self.rows, self.gres, len(self.games))
        zs = [r["z_deflated_for_search"] for r in board]
        self.assertEqual(zs, sorted(zs, reverse=True))

    def test_deflation_reduces_z(self):
        board = leaderboard.build(self.rows, self.gres, len(self.games))
        for r in board:
            self.assertLessEqual(abs(r["z_deflated_for_search"]), abs(r["z_vs_coinflip"]) + 1e-9)


class TestPublishedArtefacts(unittest.TestCase):
    """Guards against the site drifting from the pipeline."""

    @classmethod
    def setUpClass(cls):
        cls.report = json.loads((ROOT / "backtest/data/report.json").read_text())

    def test_report_has_no_unsourced_game(self):
        for g in self.report["games"]:
            self.assertTrue(g["source_url"].startswith("https://www.nba.com/game/"))

    def test_report_declares_its_sample(self):
        self.assertGreater(self.report["meta"]["n_games"], 0)
        self.assertGreater(self.report["meta"]["n_graded"], 0)

    def test_no_market_claims(self):
        # the report must never assert an ROI or an edge over a price
        blob = json.dumps(self.report).lower()
        self.assertNotIn('"roi":', blob)
        self.assertNotIn("profit", blob)

    def test_integrity_check_recorded(self):
        integ = self.report["integrity"]
        self.assertEqual(integ["bounded_check"]["violations"], 0)
        self.assertGreater(integ["exact_check"]["checked"], 0)


if __name__ == "__main__":
    unittest.main()
