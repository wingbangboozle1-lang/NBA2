"""Tests for the trial registry and multiple-testing correction (nba2/v3/trials.py)."""

from __future__ import annotations

import math
import unittest

from nba2.v3 import trials as TR
from nba2.models import gates as V1


class TestDeflatedSharpe(unittest.TestCase):
    def test_matches_v1_gate_function(self):
        # the v3 mirror must agree with the canonical v1 construction to the last bit
        xs = [(i % 2) * 1.0 - 0.5 for i in range(20)]
        for sr in (0.1, 0.25, 0.5, 0.7):
            self.assertAlmostEqual(TR.deflated_sharpe(sr, 9, 139, xs),
                                   V1.deflated_sharpe(sr, 9, 139, xs), places=12)

    def test_more_trials_raises_the_bar(self):
        sr, n_obs = 0.4, 200
        dsr5 = TR.deflated_sharpe(sr, 5, n_obs)
        dsr50 = TR.deflated_sharpe(sr, 50, n_obs)
        self.assertLess(dsr50, dsr5, "more trials must make the same SR less convincing")

    def test_breakeven_is_monotone_in_trials(self):
        b1 = TR.breakeven_sharpe(1, 139)
        b10 = TR.breakeven_sharpe(10, 139)
        self.assertLess(b1, b10, "more trials must raise the required Sharpe")

    def test_breakeven_is_monotone_in_obs(self):
        # more observations lower the bar for a fixed trial count
        self.assertLess(TR.breakeven_sharpe(10, 600), TR.breakeven_sharpe(10, 30))

    def test_dsr_bounds(self):
        # a clearly skillful SR over many obs clears the bar; a zero SR does not
        self.assertGreater(TR.deflated_sharpe(0.6, 10, 139), 0.95)
        self.assertLess(TR.deflated_sharpe(0.0, 10, 139), 0.5)


class TestRegistry(unittest.TestCase):
    def test_registry_is_deterministic(self):
        self.assertEqual(TR.registry(), TR.registry())

    def test_one_trial_per_strategy_plus_backtest(self):
        reg = TR.registry()
        ids = [r["strategy_id"] for r in reg]
        # 9 registered strategies + the model backtest
        self.assertEqual(len(ids), 10)
        self.assertEqual(ids.count("MODEL"), 1)
        self.assertEqual(TR.n_trials(), len(reg))

    def test_every_trial_has_a_source(self):
        for r in TR.registry():
            self.assertTrue(r["source"] and r["source"] != "", f"{r['trial_id']} has no source")

    def test_summary_bar_is_finite(self):
        s = TR.summary()
        self.assertTrue(math.isfinite(s["breakeven_sharpe_139"]))
        self.assertEqual(s["n_trials"], 10)
        # observed SR/DSR are deliberately blank until settled PnL exists
        self.assertIsNone(s["observed_sharpe"])
        self.assertIsNone(s["deflated_sharpe"])


if __name__ == "__main__":
    unittest.main()
