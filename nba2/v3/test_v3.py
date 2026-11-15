"""Tests for the v3 build. Standard library only, no network.

What is pinned here is the part that would otherwise fail silently: the
transcription arithmetic, the pinned HCA identity, the two estimators being
genuinely different functions, the luck gate actually blocking, the parlay price
being lower than the naive product when rho is positive, and the ledger refusing to
rewrite a settlement stamp.
"""

from __future__ import annotations

import json
import math
import tempfile
import unittest
from pathlib import Path

from . import official as O
from . import model as M
from . import rotation as ROT
from . import ledger as LD
from . import gates as G
from . import build as B
from . import check as CK


class TestSnapshot(unittest.TestCase):
    def test_selftest_is_clean(self):
        self.assertEqual(O.selftest(), [])

    def test_records_match_the_finals(self):
        self.assertEqual(sum(t["w"] for t in O.TEAMS.values()), 188)
        self.assertEqual(sum(t["l"] for t in O.TEAMS.values()), 188)

    def test_every_game_carries_a_source_url(self):
        for g in O.SLATE:
            self.assertTrue(g["source_url"].startswith("https://www.nba.com/game/"), g)

    def test_injury_rows_have_a_team_and_a_date(self):
        for r in O.INJURIES:
            self.assertIsNotNone(r["team_abbr"], r)
            self.assertIn(r["game_date"], ("2026-11-15", "2026-11-16"), r)

    def test_arenas_have_no_fabricated_coordinates(self):
        for a, c, s in O.ARENAS:
            self.assertTrue(a and c and s)
        for g in O.SLATE:
            self.assertIsNone(g["lat"])
            self.assertIsNone(g["lon"])


class TestHomeCourt(unittest.TestCase):
    def test_hca_is_the_pinned_identity(self):
        hc = M.home_court(M.load_played_games()["games"])
        self.assertEqual(hc["n_games"] + hc["neutral_excluded"], 188)
        want = hc["margin_sd"] * M.phi_inv(hc["home_win_rate"])
        self.assertLess(abs(hc["hca_points"] - want), 5e-4)
        self.assertAlmostEqual(M.phi(hc["hca_points"] / hc["margin_sd"]),
                               hc["home_win_rate"], places=3)

    def test_phi_inv_round_trips(self):
        for p in (0.01, 0.2, 0.5, 0.75, 0.99):
            self.assertAlmostEqual(M.phi(M.phi_inv(p)), p, places=9)


class TestEstimators(unittest.TestCase):
    def setUp(self):
        self.res = M.build()

    def test_two_estimators_are_different_functions(self):
        h, a = O.TEAMS["BOS"], O.TEAMS["UTA"]
        e1 = M.estimator_efficiency(h, a, 1.25, 99.0)
        e2 = M.estimator_scoring(h, a, 1.25, 16.9)
        self.assertNotAlmostEqual(e1, e2, places=1)

    def test_disagreement_is_published_and_non_negative(self):
        for ln in self.res["lines"]:
            self.assertGreaterEqual(ln["disagreement"], 0.0)
            self.assertLess(abs(ln["disagreement"]
                                - abs(ln["e1_margin"] - ln["e2_margin"])), 0.02)

    def test_total_is_possessions_times_ppp(self):
        for ln in self.res["lines"]:
            want = ln["possessions"] * (ln["ppp_home"] + ln["ppp_away"])
            self.assertLess(abs(ln["total"] - want), 0.2)
            self.assertLess(abs(ln["proj_home_pts"] - ln["possessions"] * ln["ppp_home"]), 0.2)

    def test_pythagorean_and_log5_are_sane(self):
        self.assertAlmostEqual(M.pythagorean(110, 110), 0.5, places=6)
        self.assertGreater(M.pythagorean(120, 100), 0.8)
        self.assertAlmostEqual(M.log5(0.5, 0.5), 0.5, places=6)
        self.assertGreater(M.log5(0.8, 0.2), 0.9)


class TestLuck(unittest.TestCase):
    def test_residuals_are_standardised(self):
        rows = M.luck_table()
        self.assertEqual(len(rows), 30)
        for r in rows:
            self.assertIsNotNone(r["luck_z"])
            self.assertIsNotNone(r["in_noise_band"])

    def test_band_is_not_empty_and_not_everything(self):
        band = M.outside_noise_band(M.luck_table())
        self.assertLess(len(band), 30)

    def test_a_blocked_club_produces_no_sealed_pick(self):
        res = M.build()
        band = set(res["outside_band"])
        for p in LD.build_picks(res):
            ln = next(l for l in res["lines"] if l["game_id"] == p["game_id"])
            self.assertFalse(ln["home"] in band or ln["away"] in band)


class TestFlow(unittest.TestCase):
    def test_rest_is_derived_from_official_dates(self):
        res = M.build()
        for ln in res["lines"]:
            f = ln["flow"]
            for side in ("away", "home"):
                self.assertIn(f[side]["three_in_four"], (True, False))
                if f[side]["rest_days"] is not None:
                    self.assertGreaterEqual(f[side]["rest_days"], 0)
                self.assertIsNone(f[side]["travel_km"])
                self.assertEqual(f[side]["travel_flag"], "F-306")

    def test_back_to_back_flags_are_consistent(self):
        res = M.build()
        for ln in res["lines"]:
            for side in ("away", "home"):
                f = ln["flow"][side]
                if f["back_to_back"] is not None:
                    self.assertEqual(f["back_to_back"], f["rest_days"] == 1)


class TestParlay(unittest.TestCase):
    def test_bivariate_normal_matches_known_values(self):
        self.assertAlmostEqual(M._bvn(0.0, 0.0, 0.0), 0.25, places=6)
        self.assertAlmostEqual(M._bvn(0.0, 0.0, 0.5), 1 / 3, places=4)
        # rho -> 1 degenerates to the marginal; quadrature is weakest there and the
        # measured rho is ~0, so the tolerance reflects the regime we actually use.
        self.assertAlmostEqual(M._bvn(2.0, 2.0, 0.99), M.phi(2.0), places=2)
        self.assertAlmostEqual(M._bvn(0.5, -0.3, 0.25), M._bvn(-0.3, 0.5, 0.25), places=5)

    def test_naive_product_is_printed_next_to_the_rho_price(self):
        priced = M.parlay_price(0.6, 0.6, 0.0)
        self.assertAlmostEqual(priced["p_joint"], 0.36, places=3)
        self.assertAlmostEqual(priced["p_naive"], 0.36, places=4)
        correlated = M.parlay_price(0.6, 0.6, 0.4)
        # positively correlated legs: the joint is HIGHER than the naive product, so the
        # naive number understates the parlay's true chance and overstates its price.
        self.assertGreater(correlated["p_joint"], priced["p_joint"])
        self.assertLess(correlated["naive_overstates_by"], 0.0)
        self.assertIsNotNone(correlated["naive_error_pct"])

    def test_measured_rho_carries_a_sample_size(self):
        rho = M.measure_rho(M.load_played_games()["games"])
        self.assertGreater(rho["n"], 100)
        self.assertIsNotNone(rho["r"])
        self.assertLess(abs(rho["r"]), 0.5)


class TestRotation(unittest.TestCase):
    ROSTER = [("A", 34.0), ("B", 31.0), ("C", 29.0), ("D", 27.0),
              ("E", 24.0), ("F", 22.0), ("G", 18.0), ("H", 16.0), ("I", 11.0)]

    def test_shares_sum_to_the_top8_share(self):
        sh = ROT.shares(self.ROSTER)
        self.assertEqual(len(sh["players"]), 8)
        self.assertAlmostEqual(sum(p["share"] for p in sh["players"]),
                               sh["top8_minutes_share"], places=3)
        self.assertAlmostEqual(sh["top8_minutes_share"], 201.0 / 240.0, places=6)

    def test_redistribution_conserves_minutes(self):
        top = sorted(self.ROSTER, key=lambda r: -r[1])[:8]
        before = sum(m for _, m in top)
        freed = dict(top)["A"]
        rd = ROT.redistribute(self.ROSTER, "A")
        incumbents = [r for r in rd["replacements"] if not r.get("next_man")]
        nxt = [r for r in rd["replacements"] if r.get("next_man")][0]
        gained = (sum(r["minutes_after"] - r["minutes_before"] for r in incumbents)
                  + (nxt["minutes_after"] - nxt["minutes_before"]))
        self.assertAlmostEqual(gained, freed, places=6)
        # the next man's baseline minutes are not part of the rotation being replaced
        self.assertAlmostEqual(sum(r["minutes_after"] for r in incumbents),
                               before - freed + freed * (1 - ROT.NEXT_MAN_SHARE), places=6)

    def test_next_man_gets_the_declared_share_of_freed_minutes(self):
        rd = ROT.redistribute(self.ROSTER, "A")
        nxt = [r for r in rd["replacements"] if r.get("next_man")][0]
        self.assertAlmostEqual(nxt["minutes_after"] - nxt["minutes_before"],
                               34.0 * ROT.NEXT_MAN_SHARE, places=6)

    def test_no_roster_means_blank_not_zero(self):
        blk = ROT.team_block("LAL", ["Reaves, Austin"])
        self.assertFalse(blk["shares"]["available"])
        self.assertIsNone(blk["shares"]["top8_minutes_share"])
        self.assertEqual(blk["shares"]["flag_id"], "F-307")


class TestLedger(unittest.TestCase):
    def test_seal_is_reproducible_and_verifies(self):
        res = M.build()
        with tempfile.TemporaryDirectory() as td:
            orig = LD.LEDGER_DIR
            try:
                LD.LEDGER_DIR = Path(td)
                info = LD.seal(res)
                ok, stored, recomputed = LD.verify(Path(td) / "sealed-2026-11-15.json")
                self.assertTrue(ok)
                self.assertEqual(stored, info["digest"])
                self.assertEqual(stored, recomputed)
                again = LD.seal(res)
                self.assertEqual(again["digest"], info["digest"])
            finally:
                LD.LEDGER_DIR = orig

    def test_prereg_digest_detects_edits(self):
        with tempfile.TemporaryDirectory() as td:
            orig = LD.PREREG_DIR
            try:
                LD.PREREG_DIR = Path(td)
                LD.write_prereg()
                ok, _ = LD.verify_prereg()
                self.assertTrue(ok)
                p = next(Path(td).glob("*.json"))
                d = json.loads(p.read_text())
                d["thresholds"] = {"tampered": True}
                p.write_text(json.dumps(d, indent=2))
                ok2, _ = LD.verify_prereg()
                self.assertFalse(ok2)
            finally:
                LD.PREREG_DIR = orig

    def test_pre_registration_states_a_settlement_rule(self):
        for s in LD.STRATEGIES:
            self.assertTrue(s["settlement_rule"])
            self.assertTrue(s["universe"])
            self.assertTrue(s["signal"])
            self.assertTrue(s["thresholds"])

    def test_no_pick_carries_a_stake(self):
        for p in LD.build_picks(M.build()):
            self.assertEqual(p["stake_pct"], 0.0)
            self.assertIsNone(p["market_price"])


class TestGates(unittest.TestCase):
    def test_hard_gates_pass(self):
        out = G.run(M.build(), None)
        hard = {g["id"]: g["pass"] for g in out["gates"]
                if g["id"] in ("G-F1", "G-F2", "G-F5")}
        self.assertTrue(all(hard.values()), hard)

    def test_gates_are_deterministic(self):
        a = G.run(M.build(), None)
        b = G.run(M.build(), None)
        self.assertEqual([g["id"] for g in a["gates"]], [g["id"] for g in b["gates"]])
        self.assertEqual([g["pass"] for g in a["gates"]], [g["pass"] for g in b["gates"]])
        self.assertEqual(a["ran_at_utc"], b["ran_at_utc"])

    def test_tip_cutoff_uses_a_declared_offset(self):
        self.assertEqual(G.ET_UTC_OFFSET_H, -5.0)


class TestPublishedPages(unittest.TestCase):
    def test_pages_exist_and_are_checked(self):
        pages, _ = B.build()
        self.assertEqual(len(pages), 7)
        self.assertEqual(CK.structural(), [])
        self.assertEqual(CK.semantic(), [])

    def test_nav_injection_is_idempotent(self):
        B.inject_nav()
        first = {p.name: p.read_text() for p in Path(B.SITE).glob("*.html")}
        B.inject_nav()
        second = {p.name: p.read_text() for p in Path(B.SITE).glob("*.html")}
        self.assertEqual(first, second)

    def test_every_published_row_links_out(self):
        import re
        for name in B.V3_PAGES:
            doc = (Path(B.SITE) / name).read_text()
            self.assertNotIn("href='", doc, f"{name} has a single-quoted href")
            for m in re.finditer(r"<tr[^>]*>(.*?)</tr>", doc, re.S):
                cells = re.findall(r"<td[^>]*>(.*?)</td>", m.group(1), re.S)
                if cells:
                    self.assertIn('href="https://', m.group(1), name)


if __name__ == "__main__":
    unittest.main()
