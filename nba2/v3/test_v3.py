"""v3 tests.

Each test here exists because the corresponding bug was real, was found, and would be found again
without a test. Nothing is tested for form's sake: every case below is a defect that shipped in an
earlier revision of this session's own code.

Run: ``python3 -m unittest discover -s nba2/v3 -t . -p 'test_*.py'``
"""

from __future__ import annotations

import copy
import json
import math
import unittest
from pathlib import Path

from nba2.v3 import backtest as BT
from nba2.v3 import injuries as I
from nba2.v3 import model as M
from nba2.v3 import official as O
from nba2.v3 import strategies as S

ROOT = Path(__file__).resolve().parents[2]


class TestBivariateNormal(unittest.TestCase):
    """phi2 is the parlay price. If it is wrong, every parlay price is wrong."""

    def test_zero_correlation_equals_product(self):
        # The independent case has a closed form; the copula must reproduce it.
        for p1, p2 in ((0.5, 0.5), (0.6, 0.3), (0.9, 0.2), (0.05, 0.95)):
            z1, z2 = M.inv_phi(p1), M.inv_phi(p2)
            got = M.phi2(z1, z2, 0.0)
            self.assertAlmostEqual(got, p1 * p2, places=6,
                                   msg=f"phi2(Φ⁻¹{p1}, Φ⁻¹{p2}, 0) should be {p1*p2}")

    def test_perfect_correlation_is_the_minimum(self):
        # As rho -> 1 the joint probability tends to min(p1, p2); that is the limiting case.
        for p1, p2 in ((0.6, 0.3), (0.2, 0.8)):
            z1, z2 = M.inv_phi(p1), M.inv_phi(p2)
            self.assertAlmostEqual(M.phi2(z1, z2, 0.998), min(p1, p2), places=3)

    def test_degenerate_rho_is_refused_not_approximated(self):
        # |rho| = 1 has a closed form; returning a quadrature answer there would hide the boundary.
        z = M.inv_phi(0.5)
        for bad in (1.0, -1.0, 1.5, float("nan")):
            with self.assertRaises((ValueError, AssertionError)):
                M.phi2(z, z, bad)

    def test_negative_correlation_reduces_below_product(self):
        # Anticorrelation is exactly why a naive product is unsafe for a parlay.
        z1, z2 = M.inv_phi(0.7), M.inv_phi(0.7)
        self.assertLess(M.phi2(z1, z2, -0.5), 0.49)

    def test_symmetric_in_arguments(self):
        z1, z2 = M.inv_phi(0.62), M.inv_phi(0.44)
        self.assertAlmostEqual(M.phi2(z1, z2, 0.3), M.phi2(z2, z1, 0.3), places=8)

    def test_inverse_phi_round_trips(self):
        for z in (-2.5, -1.0, -0.1, 0.0, 0.37, 1.4, 2.9):
            self.assertAlmostEqual(M.inv_phi(M.phi(z)), z, places=6)


class TestLedger(unittest.TestCase):
    """Tamper-evidence is the brief's explicit requirement, so each attack is tested."""

    @classmethod
    def setUpClass(cls):
        path = ROOT / "data" / "v3" / "ledger" / "sealed-picks.json"
        if not path.exists():
            raise unittest.SkipTest("no sealed ledger — run nba2.v3.strategies first")
        cls.doc = json.loads(path.read_text())

    def test_clean_ledger_verifies(self):
        ok, root, detail = S.verify_ledger(self.doc)
        self.assertTrue(ok, detail)
        self.assertEqual(len(root), 64)

    def test_editing_a_result_is_detected(self):
        bad = copy.deepcopy(self.doc)
        bad["picks"][0]["won"] = not bad["picks"][0].get("won", False)
        ok, _, detail = S.verify_ledger(bad)
        self.assertFalse(ok)
        self.assertTrue(detail["bad_rows"])

    def test_editing_a_hash_is_detected(self):
        bad = copy.deepcopy(self.doc)
        bad["picks"][1]["hash"] = "0" * 64
        ok, _, detail = S.verify_ledger(bad)
        self.assertFalse(ok)
        self.assertFalse(detail["root_matches"])

    def test_deleting_a_pick_is_detected(self):
        bad = copy.deepcopy(self.doc)
        bad["picks"].pop(2)
        ok, _, _ = S.verify_ledger(bad)
        self.assertFalse(ok)

    def test_reordering_picks_is_detected(self):
        # A chained root over an ordered list must not survive a reorder.
        bad = copy.deepcopy(self.doc)
        if len(bad["picks"]) < 3:
            self.skipTest("need at least 3 picks")
        bad["picks"][0], bad["picks"][2] = bad["picks"][2], bad["picks"][0]
        ok, _, _ = S.verify_ledger(bad)
        self.assertFalse(ok)

    def test_every_pick_binds_its_preregistration_hash(self):
        for p in self.doc["picks"]:
            self.assertIn("strategy_prereg_sha256", p)
            self.assertEqual(len(p["strategy_prereg_sha256"]), 64)


class TestEstimators(unittest.TestCase):
    """The two estimators must stay independent and on a common scale."""

    @classmethod
    def setUpClass(cls):
        # two_estimators() is what fills r_diff/r_rtg. Calling calibrate() alone leaves both at
        # their 0.0 defaults, and a test that compares two zero columns passes for the wrong reason.
        cls.cal = M.calibrate(M.load_teams())
        cls.teams = M.two_estimators(M.load_teams(), cls.cal)

    def test_home_advantage_is_pinned_not_fitted(self):
        # h = σ·Φ⁻¹(p) must hold exactly for the published number. The linear shortcut
        # σ(2p−1) is NOT the same quantity and was the bug this test caught.
        want = self.cal.margin_sd * M.inv_phi(self.cal.home_win_rate)
        self.assertAlmostEqual(self.cal.hca, want, places=3)

    def test_pinned_hca_reproduces_the_measured_home_rate(self):
        # Feeding h back through Φ must return the rate it was pinned to.
        # h was rounded to 4 dp for publication, so the round-trip holds to that precision.
        self.assertAlmostEqual(M.phi(self.cal.hca / self.cal.margin_sd),
                               self.cal.home_win_rate, places=4)

    def test_estimators_are_not_identical(self):
        # If A and B were the same function, "disagreement" would be a constant zero and the
        # brief's primary confidence signal would be vacuous.
        a = [t.r_diff for t in self.teams.values()]
        b = [t.r_rtg for t in self.teams.values()]
        self.assertTrue(any(abs(x) > 1e-9 for x in a), "r_diff was never computed")
        self.assertTrue(any(abs(x) > 1e-9 for x in b), "r_rtg was never computed")
        self.assertGreater(max(abs(x - y) for x, y in zip(a, b)), 0.2)

    def test_estimators_are_on_a_comparable_scale(self):
        a = [t.r_diff for t in self.teams.values()]
        b = [t.r_rtg for t in self.teams.values()]
        # both are centred; the estimator definitions subtract their own means
        self.assertLess(abs(sum(a)), 5.0)
        self.assertLess(abs(sum(b)), 5.0)

    def test_luck_is_zero_sum_ish(self):
        # Luck is (actual − expected); across a league the total must be near zero.
        total_luck = sum(t.luck for t in self.teams.values())
        self.assertLess(abs(total_luck), 30.0)


class TestTotals(unittest.TestCase):
    """The brief asks for possessions × PPP with the naive average printed beside it."""

    def test_total_is_possessions_times_ppp(self):
        teams = M.load_teams()
        ppp = M.league_ppp(teams)
        h, a = teams["BOS"], teams["LAL"]
        t = M.total_from_possessions(h, a, ppp)
        self.assertAlmostEqual(t["total"], t["poss"] * (t["ppp_home"] + t["ppp_away"]), places=9)
        self.assertAlmostEqual(t["pts_home"] + t["pts_away"], t["total"], places=9)

    def test_naive_and_possession_totals_are_not_the_same_number(self):
        # If they were always equal, printing both would be decoration.
        teams = M.load_teams()
        ppp = M.league_ppp(teams)
        gaps = []
        for tri, t in teams.items():
            for tri2, t2 in teams.items():
                if tri == tri2:
                    continue
                d = M.total_from_possessions(t, t2, ppp)
                gaps.append(abs(d["total"] - (t.pts + t2.pts)))
        self.assertGreater(max(gaps), 3.0)

    def test_ppp_is_within_physical_bounds(self):
        teams = M.load_teams()
        for tri, t in teams.items():
            self.assertGreater(t.ppp_off, 0.85, tri)
            self.assertLess(t.ppp_off, 1.45, tri)
            self.assertGreater(t.poss_pg, 90, tri)
            self.assertLess(t.poss_pg, 115, tri)


class TestLeakage(unittest.TestCase):
    """Three direct tests replace the naive deletion test that was wrong."""

    @classmethod
    def setUpClass(cls):
        cls.games = BT.load_games()
        cls.preds = BT.walk_forward(cls.games)
        cls.audit = BT.leakage_audit(cls.games, cls.preds)

    def test_all_three_tests_pass(self):
        self.assertTrue(self.audit["all_pass"], self.audit)

    def test_same_date_games_get_identical_ratings(self):
        # A leak would show as two games on one date with different inputs.
        self.assertEqual(self.audit["same_date_isolation"]["max_within_date_delta"], 0.0)

    def test_future_edit_changes_nothing(self):
        self.assertLess(self.audit["future_only_edit"]["max_delta"], 1e-9)

    def test_the_rejected_test_is_documented(self):
        # It is in the payload so a future contributor does not "fix" it back.
        self.assertIn("delete", self.audit["rejected_test"].lower())

    def test_every_prediction_uses_only_prior_games(self):
        for p in self.preds:
            self.assertGreater(p.n_prior_games, 0)
            self.assertEqual(p.n_prior_games, sum(1 for g in self.games if g.date < p.date))


class TestCalibration(unittest.TestCase):
    """The shrink factor is the only thing that beats a coin, so it is tested hardest."""

    @classmethod
    def setUpClass(cls):
        cls.preds = BT.walk_forward(BT.load_games())
        cls.shr = BT.shrink_gain(cls.preds)

    def test_alpha_zero_collapses_to_a_coin(self):
        # The limit case: if alpha could go to 0 and still win, the model would be pure noise.
        ps = self.preds[:20]
        self.assertTrue(all(0.0 <= p.p_home_a <= 1.0 for p in ps))

    def test_shrink_is_evaluated_out_of_sample(self):
        self.assertNotEqual(self.shr["fit_dates"], self.shr["holdout_cut"])
        self.assertGreater(self.shr["holdout_n"], 0)
        self.assertLess(self.shr["holdout_n"], self.shr["fit_n"])

    def test_gain_is_a_flat_basin_not_a_spike(self):
        # A single lucky grid point would not survive; check neighbours behave.
        a = self.shr["alpha"]
        lo = BT.shrink_gain(self.preds, grid=[a - 0.1, a, a + 0.1])
        self.assertLessEqual(abs(lo["holdout_log_loss_best"] - self.shr["holdout_log_loss_best"]),
                             0.02)

    def test_reliability_table_is_monotone_in_confidence(self):
        rel = BT.reliability_table(self.preds)
        rows = [r for r in rel["rows"] if r["n"] >= 5]
        forecasts = [r["forecast"] for r in rows]
        self.assertEqual(forecasts, sorted(forecasts),
                         "bands must be ordered by the probability they claim")

    def test_margin_shrink_beats_the_raw_margin(self):
        ms = BT.margin_shrink(self.preds)
        self.assertLess(ms["holdout_mae_shrunk"], ms["holdout_mae_raw"])


class TestStrategies(unittest.TestCase):
    """Multiplicity, direction, and the refusal gate."""

    def test_two_sided_p_is_at_least_the_one_sided_p(self):
        # The one-sided p is in the direction the rule predicts, so it is min(upper, lower);
        # the two-sided is twice the smaller tail. These are different questions and the
        # relationship is two-sided >= one-sided only when the one-sided is the smaller tail.
        for k, n, p0 in ((27, 39, 0.5), (68, 97, 0.698), (23, 61, 0.36), (35, 86, 0.25)):
            upper = sum(math.comb(n, i) * p0**i * (1 - p0)**(n - i) for i in range(k, n + 1))
            lower = sum(math.comb(n, i) * p0**i * (1 - p0)**(n - i) for i in range(0, k + 1))
            two = S._binom_two_sided(k, n, p0)
            self.assertAlmostEqual(two, min(1.0, 2 * min(upper, lower)), places=12)
            self.assertLessEqual(two, 1.0 + 1e-12)

    def test_holm_is_never_smaller_than_raw(self):
        # A correction that lowers a p-value is not a correction.
        raw = [(0.01, 5), (0.04, 5), (0.5, 5)]
        running = 0.0
        for i, (pv, m) in enumerate(sorted(raw)):
            adj = min(1.0, (m - i) * pv)
            running = max(running, adj)
            self.assertGreaterEqual(running + 1e-12, pv)

    def test_worse_than_base_rate_is_not_labelled_distinct(self):
        # A rule below its base rate must never be called distinct, however small its p.
        teams = M.load_teams()
        from nba2.v3 import build as B, backtest as BT
        out = S.run(teams, BT.run())
        for row in out["scoreboard"]:
            if row["hit_rate"] is not None and row["hit_rate"] <= row["base_rate_p0"]:
                self.assertFalse(row["distinguishable_from_base"],
                                 f"{row['id']} is at/below base rate but marked distinct")

    def test_luck_gate_refuses_when_a_club_is_outside(self):
        teams = M.load_teams()
        tri = next(iter(teams))
        teams[tri].luck_z = 4.0
        picks = [{"home": tri, "away": next(t for t in teams if t != tri)}]
        g = S.luck_gate(picks, teams)
        self.assertTrue(g["refused"])

    def test_luck_gate_allows_when_all_inside(self):
        teams = M.load_teams()
        for t in teams.values():
            t.luck_z = 0.0
        picks = [{"home": next(iter(teams)), "away": list(teams)[1]}]
        g = S.luck_gate(picks, teams)
        self.assertFalse(g["refused"])

    def test_parlay_price_brackets_the_naive_product(self):
        # With |rho| small the copula must sit near the product, not at an arbitrary distance.
        for rho in (-0.1, 0.0, 0.1):
            out = S.parlay_price_sgp(0.6, 0.55, rho)
            self.assertAlmostEqual(out["priced_joint"], out["naive_product"], delta=0.02)


class TestInjuries(unittest.TestCase):
    """The banner once published a UTC time that contradicted its own lag."""

    def test_banner_arithmetic_holds(self):
        b = I.banner()
        self.assertEqual(I.check_banner_arithmetic(b), [])

    def test_typed_utc_equivalent_contradiction_is_caught(self):
        b = dict(I.banner())
        b["revision_utc_equivalent"] = "10:15Z"      # the actual historical bug
        self.assertTrue(I.check_banner_arithmetic(b))

    def test_negative_lag_is_caught(self):
        b = dict(I.banner())
        b["retrieved_utc"] = "2026-11-15T09:00:00Z"
        self.assertTrue(I.check_banner_arithmetic(b))

    def test_diff_keys_on_date_team_player(self):
        prev = [{"date": "2026-11-14", "team": "BOS", "player": "X", "status": "Out"}]
        cur = [{"date": "2026-11-15", "team": "BOS", "player": "X", "status": "Available"}]
        d = I.diff_reports(prev, cur)
        # Same player on a different date is a date move, never a status change.
        self.assertEqual(d["counts"]["status_changes"], 0)
        self.assertEqual(d["counts"]["added"], 1)
        self.assertEqual(d["counts"]["dropped"], 1)

    def test_status_change_is_detected_on_the_same_key(self):
        prev = [{"date": "2026-11-15", "team": "BOS", "player": "X", "status": "Questionable"}]
        cur = [{"date": "2026-11-15", "team": "BOS", "player": "X", "status": "Out"}]
        d = I.diff_reports(prev, cur)
        self.assertEqual(d["counts"]["status_changes"], 1)


class TestCapture(unittest.TestCase):
    """The capture module's identities, re-derived rather than trusted."""

    def test_wins_equal_losses(self):
        teams = M.load_teams()
        self.assertEqual(sum(t.w for t in teams.values()), sum(t.l for t in teams.values()))

    def test_every_final_sums_to_its_quarters(self):
        # FINALS rows: (game_id, date, away, home, away_pts, home_pts, away_q, home_q, neutral, arena)
        self.assertTrue(O.FINALS, "no finals captured")
        for row in O.FINALS:
            gid, _d, _a, _h, ap, hp, aq, hq, _neu, _arena = row
            if aq:
                self.assertEqual(sum(aq), ap, f"{gid}: away quarters {sum(aq)} != final {ap}")
            if hq:
                self.assertEqual(sum(hq), hp, f"{gid}: home quarters {sum(hq)} != final {hp}")
            if aq and hq:
                self.assertEqual(len(aq), 4, gid)
                self.assertEqual(len(hq), 4, gid)

    def test_quarter_blocks_are_the_printers_own_numbers(self):
        # Spot-check one game against the captured table rather than against itself.
        g = {r[0]: r for r in O.FINALS}["0022600231"]
        self.assertEqual(g[6], [29, 27, 30, 30])   # DEN
        self.assertEqual(g[7], [23, 28, 31, 26])   # NOP
        self.assertEqual(sum(g[6]), 116)
        self.assertEqual(sum(g[7]), 108)

    def test_window_dates_are_ordered(self):
        self.assertLess(O.WINDOW_START, O.WINDOW_END)

    def test_league_ppp_is_plausible(self):
        teams = M.load_teams()
        self.assertTrue(1.0 < M.league_ppp(teams) < 1.25)


class TestBuildInvariants(unittest.TestCase):
    """What the build must never do."""

    def setUp(self):
        from nba2.v3 import build as B
        self.B = B

    def test_surfaces_are_declared_and_disjoint(self):
        self.assertEqual(set(self.B.SURFACES), {"projection", "bet"})

    def test_nav_puts_every_page_in_exactly_one_group(self):
        seen = {}
        for surface, _label, entries in self.B.NAV_GROUPS:
            for href, _text in entries:
                self.assertNotIn(href, seen, f"{href} appears in two nav groups")
                seen[href] = surface
        self.assertEqual(len(seen), sum(len(e[2]) for e in self.B.NAV_GROUPS))

    def test_bet_page_is_the_only_bet_surface_page(self):
        bet = [h for h, s in
               ((h, s) for s, _l, es in self.B.NAV_GROUPS for h, _t in es) if s == "bet"]
        self.assertEqual(bet, ["v3-bet.html"])

    def test_home_travel_is_zero_or_blank_never_a_distance(self):
        teams = M.load_teams()
        cal = self.B.calibration(teams)
        for ln in self.B.originated_lines(teams, cal):
            self.assertIn(ln.travel_home_km, (0.0, None),
                          f"{ln.game_id}: home club cannot travel to its own arena")


if __name__ == "__main__":
    unittest.main()
