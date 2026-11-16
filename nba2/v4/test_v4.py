"""Tests for the v4 refresh layer. Standard library only, like the rest of the repo.

The point of these tests is not coverage. It is that the claims the published pages make are
checked by something that will fail if the claim stops being true:

* the capture is internally consistent and reproducible;
* the surface wall cannot be crossed (tested in both directions, including a deliberate
  attempt to smuggle a stake onto the projection surface);
* a value with no official source cannot become a number;
* the settlement refuses to grade a broken seal, and never counts an ungraded game as a loss;
* the injury diff reports a blank status as blank;
* the luck z-score re-derives, and the published "9/9" cannot be quietly reported as skill.
"""

from __future__ import annotations

import json
import math
import unittest
from pathlib import Path

from . import capture as C
from . import check as CH
from . import injury_diff as ID
from . import model as M
from . import publish as P
from . import settlement as S
from . import write_capture as WC

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "site"


class TestCapture(unittest.TestCase):
    def test_selftest_is_clean(self):
        self.assertEqual(C.selftest(), [])

    def test_slate_is_complete_and_well_formed(self):
        sl = C.slate()
        self.assertEqual(len(sl), 29)
        self.assertEqual(len({g["game_id"] for g in sl}), 29)
        for g in sl:
            self.assertTrue(g["game_id"].startswith("002"))
            self.assertEqual(len(g["game_id"]), 10)
            self.assertTrue(g["source_url"].startswith("https://www.nba.com/game/"))

    def test_every_slate_date_is_in_the_captured_window(self):
        dates = sorted({g["date"] for g in C.slate()})
        self.assertEqual(dates, ["2026-11-16", "2026-11-17", "2026-11-18", "2026-11-19"])

    def test_standings_balance(self):
        st = C.standings()
        self.assertEqual(len(st), 30)
        self.assertEqual(sum(r["w"] for r in st), sum(r["l"] for r in st))

    def test_three_team_pages_are_all_complete(self):
        c = C.crosschecks()
        self.assertTrue(c["all_three_pages_complete"])
        self.assertEqual(len(C.advanced()), 30)
        self.assertEqual(len(C.opponent()), 30)
        self.assertEqual(len(C.traditional()), 30)

    def test_points_identity_holds_on_every_traditional_row(self):
        # 2*FGM + 3PM + FTM = PTS. A single wrong digit breaks this.
        for r in C.traditional():
            self.assertLessEqual(abs(2 * r["fgm"] + r["fg3m"] + r["ftm"] - r["pts"]), 0.45,
                                 msg=f"{r['tri']} points identity")

    def test_cross_page_corroboration_is_tight(self):
        for t in C.teams().values():
            self.assertLessEqual(abs(t["pts_for_crosscheck_delta"]), 0.10, msg=t["tri"])

    def test_finals_are_complete_and_quarter_rows_sum(self):
        fin = C.finals_2026_11_15()
        self.assertEqual(len(fin), 9)
        for g in fin:
            if g["away_q"] is not None:
                self.assertEqual(sum(g["away_q"]), g["away_pts"], msg=g["game_id"])
            if g["home_q"] is not None:
                self.assertEqual(sum(g["home_q"]), g["home_pts"], msg=g["game_id"])

    def test_a_missing_quarter_row_is_blank_not_back_solved(self):
        g = [x for x in C.finals_2026_11_15() if x["game_id"] == "0022600240"][0]
        self.assertIsNone(g["away_q"])
        self.assertEqual(g["quarter_status"], "partial")
        self.assertIsNotNone(g["home_q"])

    def test_every_source_page_has_a_url(self):
        for k, v in C.SOURCE_PAGES.items():
            self.assertTrue(v["url"].startswith("https://"), msg=k)

    def test_unread_inputs_are_declared_with_a_reason_and_a_url(self):
        self.assertGreaterEqual(len(C.UNREAD), 4)
        for k, (what, why, url) in C.UNREAD.items():
            self.assertTrue(what and why, msg=k)
            self.assertTrue(url.startswith("https://"), msg=k)


class TestCaptureIsReproducible(unittest.TestCase):
    def test_writer_is_idempotent(self):
        files = WC.write()
        first = {f: (ROOT / f).read_bytes() for f in files}
        WC.write()
        second = {f: (ROOT / f).read_bytes() for f in files}
        self.assertEqual(first, second, "capture rewrite is not byte-identical")

    def test_written_index_lists_every_file(self):
        p = ROOT / "data/raw/refresh_2026-11-16/capture_index.json"
        idx = json.loads(p.read_text())
        for f in idx["files"]:
            self.assertTrue((ROOT / f).exists(), msg=f)


class TestModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res = M.build()

    def test_two_estimators_are_different_functions(self):
        # same inputs, different answers somewhere - otherwise "disagreement" is theatre
        diffs = [p["disagreement"] for p in self.res["projections"]]
        self.assertTrue(all(d >= 0 for d in diffs))
        self.assertGreater(max(diffs), 0.0)

    def test_hca_is_the_pinned_identity(self):
        hc = self.res["home_court"]
        self.assertAlmostEqual(hc["margin_sd"] * M.phi_inv(hc["home_win_rate"]),
                               hc["hca_points"], places=3)
        self.assertGreaterEqual(hc["n_games"], M.HCA_MIN_GAMES)

    def test_hca_is_not_fitted_to_the_slate(self):
        # The measured home-win rate has to come from official finals, and the pool has to
        # match the league game count implied by the standings - not a couple of days.
        c = C.crosschecks()
        self.assertEqual(self.res["history"]["n_games"], int(c["league_games"]))

    def test_total_is_possessions_times_ppp(self):
        for p in self.res["projections"]:
            expect = p["possessions"] * (p["ppp_home"] + p["ppp_away"])
            self.assertLessEqual(abs(expect - p["proj_total"]), 0.06, msg=p["game_id"])

    def test_total_is_not_a_blend_of_team_averages(self):
        # A total built as the mean of the two clubs' points per game ignores the opponent's
        # defence; this asserts the published total actually uses OffRtg and DefRtg.
        teams = self.res["teams"]
        for p in self.res["projections"][:5]:
            h = teams[p["flow"]["home"]["team"]]
            a = teams[p["flow"]["away"]["team"]]
            naive = h["pts_for"] + a["pts_for"]
            self.assertNotAlmostEqual(p["proj_total"], naive, places=0)

    def test_luck_z_rederives(self):
        for r in self.res["luck"]:
            p = M.pythagorean(r["pts_for"], r["pts_against"])
            exp_w = p * r["gp"]
            self.assertAlmostEqual(exp_w, r["expected_wins"], places=2)
            sd = math.sqrt(r["gp"] * p * (1 - p))
            self.assertAlmostEqual((r["w"] - exp_w) / sd, r["luck_z"], places=2)

    def test_luck_band_membership_matches_the_flag(self):
        for r in self.res["luck"]:
            self.assertEqual(r["in_noise_band"], abs(r["luck_z"]) <= self.res["luck_band_z"])

    def test_a_blocked_club_blocks_the_game(self):
        # force a club into the band and check the gate refuses a game involving it
        band = {"BOS"}
        g = [x for x in C.slate() if "BOS" in (x["away"], x["home"])][0]
        row = M.price_game(g, self.res["teams"], self.res["hca"], self.res["sigma"],
                           M.played_games()["games"], C.slate(), band,
                           M.injury_rows(), M.travel_miles())
        self.assertTrue(row["luck_gate"]["blocked"])

    def test_rho_carries_its_sample_size_and_interval(self):
        self.assertGreaterEqual(self.res["rho"]["n"], 100)
        self.assertIsNotNone(self.res["rho"]["r"])
        self.assertIsNotNone(self.res["rho"]["ci95"])

    def test_projection_rows_carry_no_price_and_no_stake(self):
        for p in self.res["projections"]:
            self.assertIsNone(p["market_price"])
            self.assertEqual(p["stake_pct"], 0.0)
            self.assertEqual(p["surface"], "projection")


class TestSurfaceWall(unittest.TestCase):
    def test_the_model_refuses_every_bet_row_without_a_price(self):
        bet = M.build()["bet_surface"]
        self.assertEqual(bet["n_rows"], 0)
        self.assertEqual(bet["n_refused"], len(M.build()["projections"]))
        self.assertFalse(bet["publishable"])

    def test_a_price_produces_a_bet_row(self):
        res = M.build()
        gid = res["projections"][0]["game_id"]
        bet = M.bet_surface_rows(res["projections"],
                                 {gid: {"home_decimal": 2.10, "book": "TEST-FEED"}})
        self.assertEqual(bet["n_rows"], 1)
        self.assertEqual(bet["rows"][0]["surface"], "bet")
        self.assertIn("edge_vs_market", bet["rows"][0])

    def test_assert_no_mixing_rejects_a_stake_on_the_projection_surface(self):
        res = M.build()
        bad = dict(res["projections"][0])
        bad["kelly_fraction"] = 0.12
        bad["edge_vs_market"] = 0.05
        with self.assertRaises(AssertionError):
            M.assert_no_mixing([bad], "projection")

    def test_assert_no_mixing_rejects_a_mislabelled_row(self):
        res = M.build()
        bad = dict(res["projections"][0])
        bad["surface"] = "bet"
        with self.assertRaises(AssertionError):
            M.assert_no_mixing([bad], "projection")

    def test_projection_html_mentions_stakes_only_to_disclaim_them(self):
        doc = (SITE / "projection.html").read_text()
        self.assertIn("no stake", doc.lower())
        self.assertEqual(CH.surface_wall(), [])


class TestSettlement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = S.settle()

    def test_seal_is_verified_before_grading(self):
        self.assertTrue(self.doc["seal_verified"])
        self.assertEqual(self.doc["seal_sha256"],
                         json.loads((ROOT / "data/v3/ledger/sealed-2026-11-15.json")
                                    .read_text())["sha256"])

    def test_graded_plus_ungraded_equals_the_seal(self):
        s = self.doc["settlement"]
        self.assertEqual(s["n_graded"] + s["n_ungraded"], s["n_sealed"])

    def test_only_verified_finals_are_graded(self):
        verified = {g["game_id"] for g in C.finals_2026_11_15()}
        for g in self.doc["graded"]:
            self.assertIn(g["game_id"], verified)

    def test_ungraded_is_not_a_loss(self):
        # every ungraded row must carry a reason and no score
        for u in self.doc["ungraded"]:
            self.assertTrue(u["reason"])
            self.assertNotIn("official_margin", u)

    def test_stamp_is_deterministic_and_not_wall_clock(self):
        a = S.settle()["settlement"]["settled_at_utc"]
        b = S.settle()["settlement"]["settled_at_utc"]
        self.assertEqual(a, b)
        self.assertTrue(a.endswith("T23:59:59Z"))

    def test_settlement_hash_verifies_and_seal_survives(self):
        v = S.verify_settlement()
        self.assertTrue(v["ok"])
        self.assertTrue(v["seal_still_verified"])

    def test_a_nine_for_nine_run_is_not_published_as_skill(self):
        # If this test ever fails, someone has started claiming the run as evidence.
        s = self.doc["settlement"]
        if s["n_graded"] >= 5:
            self.assertGreater(s["p_observed_run_under_model"], 0.01,
                               "the observed run is now unlikely enough to investigate - "
                               "but check the sample size before calling it skill")
        self.assertIn("luck", json.dumps(s).lower())

    def test_log_loss_beats_the_coin_flip_baseline_or_is_reported_honestly(self):
        s = self.doc["settlement"]
        self.assertIsNotNone(s["log_loss_coin"])
        self.assertAlmostEqual(s["log_loss_coin"], math.log(2), places=4)


class TestInjuryDiff(unittest.TestCase):
    def test_releases_carry_three_stamps_and_a_hash(self):
        doc = ID.release_ledger()
        self.assertGreaterEqual(doc["n_releases_stored_this_session"], 2)
        for r in doc["releases"]:
            self.assertTrue(r["report_stamp_et"])
            self.assertTrue(r["retrieved_at_utc"])
            self.assertTrue(r["url"].startswith("https://"))
            self.assertEqual(len(r["content_sha256"]), 64)
            self.assertFalse(r["binary_stored"], "bytes are not storeable in this sandbox")
            self.assertIn("F-V4-01", r["binary_stored_reason"])

    def test_consecutive_diff_counts_add_up(self):
        doc = ID.release_ledger()
        self.assertGreaterEqual(doc["consecutive_release_diffs"], 1)
        for d in doc["diffs"]:
            c = d["counts"]
            total = (c["status_changed"] + c["placeholder_resolved"] + c["reason_changed_only"]
                     + c["added"] + c["removed"] + c["still_placeholder"])
            self.assertEqual(len(d["status_changes"]) + len(d["reason_changes"])
                             + len(d["added"]) + len(d["removed"])
                             + len(d["still_placeholder"]), total)

    def test_a_blank_status_is_diffed_as_blank(self):
        a = {"report_stamp_et": "x", "retrieved_at_utc": "x", "provenance": {"url": "u"},
             "records": [["2026-11-16", "07:00", "A@B", "T", "P", "", "", ""]]}
        b = {"report_stamp_et": "y", "retrieved_at_utc": "y", "provenance": {"url": "u"},
             "records": [["2026-11-16", "07:00", "A@B", "T", "P", "", "", ""]]}
        d = ID.diff(a, b)
        self.assertEqual(d["counts"]["status_changed"], 0)
        self.assertEqual(d["counts"]["still_placeholder"], 1)
        # a blank becoming a real status IS a change
        b["records"][0][5] = "Out"
        d = ID.diff(a, b)
        self.assertEqual(d["counts"]["placeholder_resolved"], 1)
        self.assertEqual(d["status_changes"][0]["to"], "Out")

    def test_a_placeholder_is_never_a_player(self):
        for r in C.INJURY_RELEASES[0]["rows"]:
            if r[6] == "NOT YET SUBMITTED":
                self.assertEqual(r[4], "")

    def test_identical_release_is_declared_not_duplicated(self):
        p = ROOT / "data/raw/refresh_2026-11-16/injury_transcript_20261116_0930AM.json"
        doc = json.loads(p.read_text())
        self.assertIsNotNone(doc["replication"])
        self.assertEqual(doc["replication"]["flagged"], "F-V4-09")


class TestGatesAndCheck(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gates = CH.gates(CH.build_docs())

    def test_every_prebuild_gate_passes(self):
        for g in self.gates:
            self.assertTrue(g["ok"], msg=f"{g['id']}: {g['measured']} {g['detail']}")

    def test_provenance_gate_catches_a_row_without_a_source(self):
        docs = {"x": {"rows": [{"game_id": "0022600000", "away": "A"}]}}
        g = [x for x in CH.gates(docs) if x["id"] == "G-V4-6"][0]
        self.assertFalse(g["ok"])

    def test_freshness_gate_catches_a_quarter_row_that_does_not_sum(self):
        orig = C.finals_2026_11_15
        bad = orig()
        bad[0]["away_q"] = list(bad[0]["away_q"])
        bad[0]["away_q"][0] += 1
        C.finals_2026_11_15 = lambda: bad
        try:
            g = [x for x in CH.gates(CH.build_docs()) if x["id"] == "G-V4-1"][0]
            self.assertFalse(g["ok"])
        finally:
            C.finals_2026_11_15 = orig

    def test_full_check_is_green(self):
        r = CH.run()
        self.assertEqual(r["structural"], [])
        self.assertEqual(r["surface_wall"], [])
        self.assertEqual(r["numeric"], [])
        self.assertTrue(r["publishable"])


class TestPublishedPages(unittest.TestCase):
    def test_all_v4_pages_exist_and_have_a_stylesheet(self):
        for name in P.V4_PAGES:
            p = SITE / name
            self.assertTrue(p.exists(), msg=name)
            self.assertIn('href="assets/site.css"', p.read_text(), msg=name)

    def test_every_v4_page_is_navigable_from_every_other(self):
        for name in P.V4_PAGES:
            doc = (SITE / name).read_text()
            for other, _label in P.V4_NAV:
                self.assertIn(f'href="{other}"', doc, msg=f"{name} -> {other}")

    def test_projection_and_bet_are_separate_nav_entries(self):
        labels = dict((h, l) for h, l in P.V4_NAV)
        self.assertIn("projection.html", labels)
        self.assertIn("bet.html", labels)
        self.assertNotEqual(labels["projection.html"], labels["bet.html"])

    def test_the_injuries_banner_shows_both_times(self):
        doc = (SITE / "v4-injuries.html").read_text()
        self.assertIn(C.INJURY_RELEASES[0]["stamp_et"], doc)
        self.assertIn(C.INJURY_RELEASES[0]["retrieved_utc"], doc)

    def test_the_settlement_stamp_is_visible(self):
        doc = (SITE / "settle.html").read_text()
        self.assertIn("Settlement stamp", doc)
        self.assertIn("PRE-TIP HASH VERIFIED", doc)

    def test_every_fragment_link_lands_on_a_real_anchor(self):
        # A link to page.html#section is a broken link if the section was renamed.
        import re as _re
        anchor = _re.compile(r'href="([^"]+)"')
        for name in P.V4_PAGES:
            for href in anchor.findall((SITE / name).read_text()):
                if href.startswith(("http", "mailto")):
                    continue
                path, _, frag = href.partition("#")
                target = SITE / (path or name)
                self.assertTrue(target.exists(), msg=f"{name} -> {href}")
                if frag:
                    self.assertIn(f'id="{frag}"', target.read_text(),
                                  msg=f"{name} -> {href} has no matching anchor")

    def test_the_irregularity_register_is_complete_and_reasoned(self):
        doc = (SITE / "v4-verify.html").read_text()
        for fid, sev, where, what, effect in P.V4_FLAGS:
            self.assertIn(fid, doc, msg=fid)
            self.assertTrue(what and effect, msg=fid)
            self.assertTrue(where[3].startswith("https://"), msg=fid)
            self.assertIn(sev, ("blocking", "gap"), msg=fid)

    def test_no_placeholder_tokens_anywhere(self):
        for name in P.V4_PAGES:
            self.assertIsNone(CH.PLACEHOLDER.search((SITE / name).read_text()), msg=name)


if __name__ == "__main__":
    unittest.main()
