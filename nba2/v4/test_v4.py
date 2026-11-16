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
from . import injury_parse as PA
from . import injury_renderings as RR
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
    """The settlement contract after the 2026-11-16 rewrite: all seals, distinct games."""

    @classmethod
    def setUpClass(cls):
        cls.doc = S.settle()
        cls.ledgers = {l["ledger"]: l for l in cls.doc["ledgers"]}

    def test_every_sealed_ledger_is_graded_on_one_surface(self):
        files = {l["ledger"] for l in self.doc["ledgers"]}
        self.assertEqual(files, {"data/raw/ledger/sealed-2026-11-13.json",
                                 "data/raw/ledger/sealed-2026-11-14.json",
                                 "data/v3/ledger/sealed-2026-11-15.json"},
                         "a seal that is not on this surface is a seal nobody can read")

    def test_every_seal_is_verified_before_grading(self):
        self.assertTrue(self.doc["settlement"]["seal_verified_all"])
        for l in self.doc["ledgers"]:
            self.assertTrue(l["seal_verified"], l["ledger"])
            self.assertEqual(l["seal_sha256"], l["seal_sha256"].lower())

    def test_graded_plus_ungraded_equals_each_seal(self):
        for l in self.doc["ledgers"]:
            self.assertEqual(l["n_graded"] + l["n_ungraded"], l["n_sealed"], l["ledger"])
        s = self.doc["settlement"]
        self.assertEqual(s["n_graded"] + s["n_ungraded"], s["n_sealed"])

    def test_overlapping_gradings_are_not_double_counted(self):
        s = self.doc["settlement"]
        distinct = {g["game_id"] for l in self.doc["ledgers"] for g in l["graded"]}
        self.assertEqual(s["n_distinct_games_graded"], len(distinct))
        self.assertLessEqual(s["n_distinct_games_graded"], s["n_graded"])
        self.assertEqual(s["n_duplicate_gradings"], s["n_graded"] - len(distinct))
        # the headline rate must be the distinct-game rate, never the summed one
        hits = {g["game_id"]: g for l in self.doc["ledgers"] for g in l["graded"]}
        expected = round(sum(1 for g in hits.values() if g["winner_correct"]) / len(hits), 4)
        self.assertEqual(s["distinct_winner_hit_rate"], expected)

    def test_only_games_with_a_verified_final_are_graded(self):
        verified = {f["game_id"] for f in self.doc["finals_used"]}
        for l in self.doc["ledgers"]:
            for g in l["graded"]:
                self.assertIn(g["game_id"], verified)
            for u in l["ungraded"]:
                self.assertNotIn(u["game_id"], verified,
                                 "a game with a verified final must not be left ungraded")

    def test_ungraded_is_not_a_loss(self):
        for l in self.doc["ledgers"]:
            for u in l["ungraded"]:
                self.assertTrue(u["reason"])
                self.assertNotIn("official_margin", u)

    def test_a_quarter_row_that_does_not_sum_to_the_final_is_withheld(self):
        for f in self.doc["finals_used"]:
            for side in ("away_q", "home_q"):
                q = f[side]
                if q:
                    self.assertEqual(sum(q), f["away_pts"] if side == "away_q" else f["home_pts"],
                                     f"{f['game_id']} {side} does not sum to the final")

    def test_stamp_is_deterministic_and_not_wall_clock(self):
        a = S.settle()["settlement"]["settled_at_utc"]
        b = S.settle()["settlement"]["settled_at_utc"]
        self.assertEqual(a, b)
        self.assertTrue(a.endswith("T23:59:59Z"))

    def test_settlement_hash_verifies_and_seals_survive(self):
        v = S.verify_settlement()
        self.assertTrue(v["ok"])
        self.assertTrue(v["seal_still_verified"])
        self.assertTrue(v["all_seals_ok"])

    def test_luck_is_reported_as_a_tail_probability_not_a_hit_rate(self):
        s = self.doc["settlement"]
        self.assertIsNotNone(s["p_at_least_observed_hits"])
        self.assertGreater(s["p_at_least_observed_hits"], 0.0)
        self.assertLessEqual(s["p_at_least_observed_hits"], 1.0)
        # the Poisson-binomial tail must dominate the all-correct product by construction
        self.assertGreaterEqual(s["p_at_least_observed_hits"], s["p_observed_distinct_run"])
        self.assertIn("luck", json.dumps(s).lower())

    def test_log_loss_baseline_is_the_coin_flip(self):
        s = self.doc["settlement"]
        self.assertAlmostEqual(s["distinct_log_loss_coin"], math.log(2), places=4)

    def test_tail_probability_helper(self):
        self.assertEqual(S.p_at_least(0, [0.5, 0.5]), 1.0)
        self.assertAlmostEqual(S.p_at_least(2, [0.5, 0.5]), 0.25, places=9)
        self.assertAlmostEqual(S.p_at_least(1, [1.0, 1.0]), 1.0, places=9)
        self.assertAlmostEqual(S.p_at_least(2, [0.9, 0.9]), 0.81, places=9)


class TestInjuryParse(unittest.TestCase):
    """The parser is the thing that failed silently before, so it is tested directly."""

    TABLE = ("| Game Date | Game Time | Matchup | Team | Player Name | Current Status | Reason |\n"
             "| --- | --- | --- | --- | --- | --- | --- |\n")

    def _p(self, body: str) -> dict:
        return PA.parse_render("**Injury Report: 11/16/26 07:00 AM**\n\n" + self.TABLE + body)

    def test_full_row(self):
        d = self._p("| 11/16/2026 | 07:00 (ET) | CHI@CLE | Chicago Bulls | Smith, Jalen | "
                    "Questionable | Injury/Illness - Left Finger Sprain |\n")
        r = d["rows"][0]
        self.assertEqual((r["date"], r["time_et"], r["matchup"], r["team"], r["player"],
                          r["status"], r["reason"]),
                         ("2026-11-16", "07:00", "CHI@CLE", "Chicago Bulls",
                          "Smith, Jalen", "Questionable",
                          "Injury/Illness - Left Finger Sprain"))
        self.assertEqual(d["unread"], [])

    def test_a_status_is_read_even_when_the_left_cells_are_dropped(self):
        d = self._p("|  |  |  | Pippen Jr., Scotty | Out | Injury/Illness - Lumbar Disc Herniation |\n")
        r = d["rows"][0]
        self.assertEqual((r["player"], r["status"], r["reason"]),
                         ("Pippen Jr., Scotty", "Out",
                          "Injury/Illness - Lumbar Disc Herniation"))
        self.assertEqual(d["unread"], [])

    def test_the_gsw_shape_never_assumes_the_middle_cell_is_a_status(self):
        # 'Out' survives here; the player/reason pair must still be attributed correctly.
        d = self._p("|  | 08:00 (ET) | GSW@NOP | Golden State Warriors | Curry, Stephen | Out |\n")
        r = d["rows"][0]
        self.assertEqual((r["team"], r["player"], r["status"], r["reason"]),
                         ("Golden State Warriors", "Curry, Stephen", "Out", None))
        # and when the status column is genuinely gone, the status stays blank
        d = self._p("|  | 08:00 (ET) | GSW@NOP | Golden State Warriors | Butler III, Jimmy | "
                    "Injury/Illness - Right ACL Repair / Surgery |\n")
        r = d["rows"][0]
        self.assertEqual(r["player"], "Butler III, Jimmy")
        self.assertIsNone(r["status"], "a status must never be inferred from a reason")
        self.assertEqual(r["reason"], "Injury/Illness - Right ACL Repair / Surgery")
        self.assertIn("F-V4-06", r["note"])

    def test_a_placeholder_is_a_club_not_a_player(self):
        d = self._p("|  |  |  | Washington Wizards |  |  | NOT YET SUBMITTED |\n")
        r = d["rows"][0]
        self.assertTrue(r["placeholder"])
        self.assertEqual(r["team"], "Washington Wizards")
        self.assertIsNone(r["player"])

    def test_a_non_status_word_is_not_accepted_as_a_status(self):
        d = self._p("|  |  |  | Team X | Some, Player | Maybe | Injury/Illness - Knee |\n")
        r = d["rows"][0]
        self.assertIsNone(r["status"])
        self.assertNotIn("Maybe", json.dumps(r["status"]))

    def test_every_stored_release_parses_with_no_unread_rows(self):
        for rel in RR.RENDERS:
            d = PA.parse_render(rel["text"])
            self.assertEqual(d["unread"], [], f"{rel['stamp_et']} has unread rows")
            self.assertEqual(d["counts"]["rows"], len(d["rows"]))

    def test_the_stored_rendering_matches_its_own_header(self):
        self.assertEqual(RR.selftest(), [])

    def test_the_diff_detects_the_two_real_status_changes(self):
        rels = ID.parsed()
        d = ID.diff(rels[0], rels[1])
        changes = {(c["key"][2], c["key"][3]): (c["from"], c["to"])
                   for c in d["status_changes"]}
        self.assertEqual(changes.get(("Miami Heat", "Larsson, Pelle")),
                         ("Questionable", "Doubtful"))
        self.assertEqual(changes.get(("Memphis Grizzlies", "Stewart, Isaiah")),
                         ("Questionable", "Out"))

    def test_the_cross_session_check_finds_the_dropped_statuses(self):
        cs = ID.cross_session_check()
        self.assertTrue(cs["available"])
        rows = {(c["key"][2], c["key"][3]): (c["from"], c["to"])
                for c in cs["diff"]["status_changes"]}
        self.assertEqual(rows.get(("Cleveland Cavaliers", "Tyson, Jaylon")),
                         ("Questionable", "Doubtful"),
                         "the earlier transcription recorded Questionable; the PDF prints Doubtful")
        for player in ("Curry, Stephen", "Moody, Moses", "Porzingis, Kristaps",
                       "Santos, Gui", "Williams, Brandon"):
            self.assertIn(("Golden State Warriors", player), rows,
                          f"the earlier transcription lost {player}'s status")


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
        newest = RR.newest()
        self.assertIn(newest["stamp_et"], doc, "the revision time must be printed")
        self.assertIn(newest["retrieved_utc"], doc, "the retrieval time must be printed")
        self.assertIn(newest["index_checked_utc"], doc, "the index check must be printed")

    def test_the_settlement_stamp_is_visible(self):
        doc = (SITE / "settle.html").read_text()
        self.assertIn("Settlement stamp", doc)
        self.assertIn("ALL SEALS VERIFIED", doc)
        # the distinct-game correction must be on the page, not just in the JSON
        self.assertIn("gradings are repeats", doc)

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
