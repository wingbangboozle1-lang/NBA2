"""Statistical machinery tests. These are the numbers the whole site rests on, so they are
checked against hand-computable values rather than against the implementation itself.
"""

from __future__ import annotations

import math
import unittest
from pathlib import Path

from nba2.models import gates as G
from nba2.models import correlation as C
from nba2.models import props as PR

ROOT = Path(__file__).resolve().parents[2]


class TestNormal(unittest.TestCase):
    def test_inv_norm_cdf_known_quantiles(self):
        for p, z in ((0.975, 1.959964), (0.025, -1.959964), (0.5, 0.0),
                     (0.9, 1.281552), (0.999, 3.090232)):
            self.assertAlmostEqual(G.inv_norm_cdf(p), z, places=5, msg=f"p={p}")

    def test_scores(self):
        self.assertAlmostEqual(G.brier([0.5, 0.5], [0, 1]), 0.25, places=12)
        self.assertEqual(G.brier([1.0, 0.0], [1, 0]), 0.0)
        self.assertAlmostEqual(G.log_loss([0.5], [1]), math.log(2), places=12)
        self.assertTrue(math.isnan(G.brier([], [])))

    def test_bootstrap_is_deterministic(self):
        xs = [1.0, 2.0, 3.0, 4.0, 5.0, 6.5, -2.0]
        a = G.bootstrap_ci(xs, n=2000, seed=7)
        b = G.bootstrap_ci(xs, n=2000, seed=7)
        self.assertEqual(a, b, "same seed must give the same interval (reproducibility)")
        self.assertLess(a[1], a[0])
        self.assertGreater(a[2], a[0])

    def test_holm(self):
        out = dict((k, (adj, rej)) for k, adj, rej in G.holm([("a", 0.01), ("b", 0.04), ("c", 0.5)]))
        self.assertAlmostEqual(out["a"][0], 0.03, places=10)     # 0.01 * 3
        self.assertAlmostEqual(out["b"][0], 0.08, places=10)     # 0.04 * 2
        self.assertAlmostEqual(out["c"][0], 0.5, places=10)  # 0.5 * 1, no further inflation
        self.assertTrue(out["a"][1] and not out["c"][1])

    def test_deflated_sharpe_shrinks_with_trials(self):
        xs = [0.2, -0.1, 0.3, 0.05, -0.05, 0.15, 0.1, -0.2, 0.25, 0.1]
        sr = G.mean(xs) / G.stdev(xs)
        d5 = G.deflated_sharpe(sr, 5, len(xs), xs)
        d500 = G.deflated_sharpe(sr, 500, len(xs), xs)
        self.assertGreater(d5, d500, "more trials must make the same result less convincing")
        self.assertTrue(0.0 <= d500 <= 1.0)


class TestCorrelation(unittest.TestCase):
    def test_pearson_spearman(self):
        self.assertAlmostEqual(C.pearson([1, 2, 3], [2, 4, 6]), 1.0, places=12)
        self.assertAlmostEqual(C.pearson([1, 2, 3], [3, 2, 1]), -1.0, places=12)
        self.assertAlmostEqual(C.spearman([1, 2, 3], [10, 20, 25]), 1.0, places=12)
        self.assertIsNone(C.pearson([1, 2], [1, 2]), "n<3 must refuse, not return 0")

    def test_bivariate_independence(self):
        # at rho=0 the joint tail must equal the product of marginal tails
        p_a = 1 - C._ncdf(0.0)
        p_b = 1 - C._ncdf(0.5)
        joint = C.bivariate_upper_tail(0, 1, 0, 1, 0.0, 0.0, 0.5, n=1201)
        self.assertAlmostEqual(joint, p_a * p_b, places=3)

    def test_positive_rho_raises_same_game_joint(self):
        base = C.bivariate_upper_tail(0, 1, 0, 1, 0.0, 0.3, 0.3, n=1201)
        corr = C.bivariate_upper_tail(0, 1, 0, 1, 0.4, 0.3, 0.3, n=1201)
        self.assertGreater(corr, base)

    def test_jaccard(self):
        self.assertEqual(C.overlap_jaccard(["a", "b"], ["a", "b"]), 1.0)
        self.assertEqual(C.overlap_jaccard([], []), 0.0)
        self.assertAlmostEqual(C.overlap_jaccard(["a", "b"], ["b", "c"]), 1 / 3)


class TestProps(unittest.TestCase):
    def test_nb_pmf_normalises(self):
        tot = sum(PR.negbinom_pmf(k, 8.0, 24.0) for k in range(0, 120))
        self.assertAlmostEqual(tot, 1.0, places=3)

    def test_p_over_monotone_decreasing_in_line(self):
        ps = [PR.p_over(line, 22.0, 90.0) for line in (15.5, 20.5, 25.5, 30.5)]
        self.assertTrue(all(a > b for a, b in zip(ps, ps[1:])), f"{ps}")
        self.assertTrue(all(0.0 <= p <= 1.0 for p in ps))

    def test_count_skew_moves_the_mean_line(self):
        """Over-dispersed counts are right-skewed, so P(X >= mean) < 0.5 even though the mean
        is 22. A Poisson (symmetric-ish) model would not show this, which is exactly why prop
        lines priced off a Poisson are systematically wrong on the over side."""
        self.assertLess(PR.p_over(22.0, 22.0, 90.0), 0.5)
        self.assertLess(PR.p_over(21.5, 22.0, 90.0), 0.5)
        self.assertGreater(PR.p_over(20.5, 22.0, 90.0), 0.5)
        poisson_like = PR.p_over(22.0, 22.0, 22.0001)   # var≈mean -> approximately Poisson
        self.assertTrue(0.40 < poisson_like < 0.52, poisson_like)

    def test_minutes_floor(self):
        self.assertAlmostEqual(PR.implied_minutes(22.0, 0.8), 27.5, places=6)
        self.assertIsNone(PR.implied_minutes(22.0, 0.0))

    def test_combo_error_grows_with_rho(self):
        e0 = PR.combo_correlation_effect(0.55, 0.55, 0.0)["error_factor"]
        e4 = PR.combo_correlation_effect(0.55, 0.55, 0.40)["error_factor"]
        em4 = PR.combo_correlation_effect(0.55, 0.55, -0.40)["error_factor"]
        self.assertAlmostEqual(e0, 1.0, places=2)
        self.assertGreater(e4, 1.05)
        self.assertLess(em4, 0.95)


class TestGateEngine(unittest.TestCase):
    def test_missing_measurements_are_blocked_not_zero(self):
        res = {r.gate_id: r for r in G.evaluate({})}
        self.assertEqual(res["G-01"].result, G.BLOCKED)
        self.assertEqual(res["G-03"].result, G.BLOCKED)
        for r in res.values():
            self.assertNotEqual(r.result, G.PASS, "no measurement may ever produce a PASS")

    def test_all_pass_needs_every_measurement(self):
        m = {"settled_bets": 500, "clv_points": 0.6, "clv_ci": (0.1, 1.1),
             "brier": 0.22, "calibration_slope": 1.0, "calibration_intercept": 0.0,
             "line_mae": 9.0, "baseline_mae": 10.0,
             "roi_ci": (0.01, 0.09), "t_stat": 2.6, "luck_adjusted_sign_match": True,
             "deflated_sharpe": 0.97, "n_trials": 9,
             "point_in_time_verified": True, "holdout_degradation": 0.1,
             "min_stability": 0.95, "survives_costs": True, "injury_blind_share": 0.2}
        res = G.evaluate(m)
        self.assertTrue(all(r.result == G.PASS for r in res), [r.as_dict() for r in res])
        self.assertEqual(G.tier_for(res), "promoted")

    def test_fail_is_not_blocked(self):
        m = {"settled_bets": 50, "brier": 0.30, "calibration_slope": 0.4,
             "calibration_intercept": 0.3, "line_mae": 12.0, "baseline_mae": 10.0}
        res = G.evaluate(m)
        self.assertIn(G.FAIL, [r.result for r in res])
        self.assertEqual(G.tier_for(res), "rejected")

    def test_point_in_time_contamination_is_at_risk(self):
        res = {r.gate_id: r for r in G.evaluate({"point_in_time_verified": False})}
        self.assertEqual(res["G-07"].result, G.AT_RISK)
        self.assertEqual(G.tier_for(list(res.values())), "research",
                         "AT-RISK must not be promotable, but is not a hard rejection")


if __name__ == "__main__":
    unittest.main()
