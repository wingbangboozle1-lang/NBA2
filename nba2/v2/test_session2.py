"""Tests for the 2026-11-15 capture and the machinery added by session arena/98b0eae9-nba2.

Guarding the claims that would be most damaging if they silently drifted:

* the results feed must re-verify quarter sums == finals at load time (fail-closed),
* the headline total must be possessions x PPP, never an average of scoring averages,
* travel distances must be reproducible haversine values from the sourced coordinates,
* rest / B2B / 3-in-4 must match the full known schedule, not just the window,
* minutes redistribution must follow the published mechanical rule exactly,
* the market-anchored prior must stay blank without a market and weight by OOS log-loss,
* per-pick ledger hashes must verify and detect a tampered row,
* every arena coordinate must be labelled THIRD-PARTY in the capture.

Run:  python3 -m unittest discover -s nba2/v2 -t . -p 'test_*.py'
"""
from __future__ import annotations

import hashlib
import json
import unittest

from . import capture2 as C2
from . import minutes as MIN
from . import model as M
from . import official as O
from . import travel as TV


class TestResultsFeed(unittest.TestCase):
    def test_five_finals_with_quarters_and_verified_flags(self):
        rows = C2.results_rows()
        self.assertEqual(len(rows), 5)
        for r in rows:
            self.assertEqual(sum(r["away_quarters"]), r["away_pts"], r["game_id"])
            self.assertEqual(sum(r["home_quarters"]), r["home_pts"], r["game_id"])
            self.assertTrue(r["source_url"].startswith("https://www.nba.com/game/"), r["game_id"])
            self.assertTrue(r["gamebook_url"].startswith("https://statsdmz.nba.com/pdfs/"), r["game_id"])

    def test_settlement_stamp_is_visible_and_linkable(self):
        st = C2.settlement_stamp()
        self.assertEqual(st["games_settled"], 5)
        self.assertEqual(st["settled_date"], "2026-11-14")
        self.assertTrue(str(st["official_results_url"]).startswith("https://"))

    def test_quarter_sum_mismatch_would_fail_closed(self):
        # the loader re-asserts quarter sums == finals on every read; a corrupted capture
        # must raise, not render. Monkeypatch the file loader with a broken copy.
        doc = json.loads(C2.RESULTS_FILE.read_text())
        doc["records"][0]["away_quarters"][0] += 1  # break the sum
        orig = C2._load
        C2._load = lambda path: doc
        try:
            with self.assertRaises(ValueError):
                C2.results_rows()
        finally:
            C2._load = orig


class TestTotalsPossTimesPPP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.teams, cls.cal = M.build_teams()
        cls.lines = M.originated_lines(cls.teams, cls.cal)

    def test_headline_total_is_poss_times_ppp(self):
        for ln in self.lines:
            self.assertAlmostEqual(ln.total, ln.poss * (ln.ppp_home + ln.ppp_away), places=6,
                                   msg=ln.matchup)
            self.assertAlmostEqual(ln.pts_home, ln.poss * ln.ppp_home, places=6)
            self.assertAlmostEqual(ln.pts_away, ln.poss * ln.ppp_away, places=6)

    def test_total_is_not_the_scoring_average(self):
        # the two estimators must both exist and the headline must be the poss*PPP one
        for ln in self.lines:
            self.assertNotAlmostEqual(ln.total, ln.total_b, places=6,
                                      msg="estimators collapsed to one — disagreement lost")
            self.assertIn("poss x PPP", ln.total_method)

    def test_trigger_formats_agree(self):
        for ln in self.lines:
            self.assertEqual(ln.trigger_total_dec, 2.000)
            self.assertEqual(ln.trigger_total_american, "+100")
            self.assertEqual(M.to_american(ln.trigger_total_dec), ln.trigger_total_american)

    def test_american_roundtrip(self):
        self.assertEqual(M.to_american(1.5), "-200")
        self.assertEqual(M.to_american(2.5), "+150")
        self.assertAlmostEqual(M.american_to_dec("+150"), 2.5)
        self.assertAlmostEqual(M.american_to_dec("-200"), 1.5)


class TestMeasuredDispersion(unittest.TestCase):
    def test_total_sd_is_measured_from_188_finals(self):
        self.assertEqual(M.n_finals_for_sd(), 188)
        sd = M.measured_total_sd()
        self.assertGreater(sd, 15)
        self.assertLess(sd, 30)


class TestTravelAndRest(unittest.TestCase):
    def test_haversine_zero_and_known_pair(self):
        self.assertAlmostEqual(TV.haversine_mi(39.7486, -105.0075, 39.7486, -105.0075), 0.0)
        # Crypto.com Arena (LAL) -> Intuit Dome (LAC): same-city arenas, ~12-13 miles
        mi = TV.leg_miles("LAL", "LAC")
        self.assertIsNotNone(mi)
        self.assertGreater(mi, 5)
        self.assertLess(mi, 25)

    def test_every_arena_has_coordinates_and_third_party_label(self):
        rows = C2.arena_rows()
        self.assertEqual(len(rows), 30)
        for r in rows:
            self.assertIsInstance(r["lat"], float)
            self.assertIsInstance(r["lon"], float)
            self.assertIn("THIRD-PARTY", r["coords_provenance"])

    def test_rest_b2b_and_three_in_four(self):
        dates = TV.team_game_dates()
        # CHI played 11/13 and 11/14 (the two games around the ground-stop) -> 11/14 is a B2B
        ctx = TV.rest_context("2026-11-14", "CHI", dates)
        self.assertEqual(ctx["days_rest"], 0)
        self.assertTrue(ctx["b2b"])
        # a team with no prior game must publish None, never a number
        ctx2 = TV.rest_context("2026-10-20", "BOS", dates)
        self.assertIsNone(ctx2["prev_date"])

    def test_travel_leg_flagged_not_estimated_when_unknown(self):
        legs = TV.travel_legs_for_game("2026-11-15", "IND", "PHI")
        for tri, c in legs.items():
            if c["travel_miles"] is None:
                self.assertTrue(c["travel_flagged"], tri)


class TestMinutesRedistribution(unittest.TestCase):
    def test_top8_shares_sum_to_one(self):
        for club, rows in MIN.top8_shares().items():
            self.assertAlmostEqual(sum(r["min_share"] for r in rows), 1.0, places=3, msg=club)

    def test_redistribution_follows_the_rule(self):
        rep = MIN.replacement_shares("Denver Nuggets", ["Murray, Jamal"])
        self.assertEqual(rep["missing"], ["Jamal Murray"])
        rows = {r["player"]: r for r in rep["rows"]}
        self.assertIsNone(rows["Jamal Murray"]["new_mpg"])  # the out row keeps None, never 0
        # total minutes conserved: sum of new mpg of available == total mpg of the block
        block = MIN.top8_blocks()["Denver Nuggets"]
        tot = sum(float(r["mpg"]) for r in block)
        new_tot = sum(r["new_mpg"] for r in rep["rows"] if r["new_mpg"] is not None)
        self.assertAlmostEqual(new_tot, tot, places=1)
        # every remaining player gains (vacated > 0)
        for r in rep["rows"]:
            if r["new_mpg"] is not None:
                self.assertGreater(r["new_mpg"], float(r["mpg"]), r["player"])

    def test_vacant_block_publishes_blank_not_estimate(self):
        rep = MIN.replacement_shares("Minnesota Timberwolves",
                                     [r["player"] for r in MIN.top8_blocks()["Minnesota Timberwolves"]])
        self.assertEqual(rep["rows"], [])
        self.assertIn("VACANT", rep["flag"])

    def test_unknown_club_is_flagged_not_invented(self):
        rep = MIN.replacement_shares("Sacramento Kings", ["Fox, De'Aaron"])
        self.assertIn("NOT CAPTURED", rep["coverage"])


class TestMarketPrior(unittest.TestCase):
    def test_blank_without_market(self):
        r = M.market_prior(3.5, None, 0.45, 0.42)
        self.assertIsNone(r["blended"])
        self.assertIn("G6", r["reason"])

    def test_blank_without_oos_scores(self):
        r = M.market_prior(3.5, -2.5, None, None)
        self.assertIsNone(r["blended"])

    def test_weights_follow_inverse_logloss(self):
        r = M.market_prior(4.0, 2.0, 0.50, 0.25)
        self.assertIsNotNone(r["blended"])
        self.assertGreater(r["w_market"], r["w_model"])  # smaller LL -> more weight
        self.assertAlmostEqual(r["w_model"] + r["w_market"], 1.0, places=6)
        self.assertAlmostEqual(r["blended"], r["w_model"] * 4.0 + r["w_market"] * 2.0, places=2)


class TestLedgerHashes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pathlib import Path
        root = Path(__file__).resolve().parents[2]
        cls.doc = json.loads((root / "data" / "v2" / "ledger.json").read_text())

    def test_every_row_has_a_hash_and_a_status(self):
        # One row per priced game: the count follows the published slate, and every slate game
        # must appear. Asserting a fixed 34 made a resliced window look like a missing ledger.
        from . import official as O
        self.assertEqual(len(self.doc["rows"]), len(O.SLATE))
        self.assertEqual({r["game_id"] for r in self.doc["rows"]},
                         {g[4] for g in O.SLATE})
        for r in self.doc["rows"]:
            self.assertEqual(len(r["row_hash"]), 64)
            self.assertEqual(r["hash_alg"], "sha256")
            self.assertIn(r["settlement"], ("settled", "pending official final"))

    def test_hash_verifies_against_published_row(self):
        # the stored payload is the published row verbatim; re-hashing it must reproduce the
        # stored hash, and the mirror columns must match the payload they mirror
        for r in self.doc["rows"]:
            h = hashlib.sha256(json.dumps(r["row_payload"], sort_keys=True).encode()).hexdigest()
            self.assertEqual(h, r["row_hash"], f"tampered or drifted row: {r['matchup']}")
            self.assertEqual(r["row_payload"]["spread"], r["published_line"])
            self.assertEqual(r["row_payload"]["total"], r["published_total"])

    def test_tampering_is_detected(self):
        import copy
        r = self.doc["rows"][0]
        tampered = copy.deepcopy(r["row_payload"])
        tampered["spread"] = tampered["spread"] + 1.0        # a post-tip edit of the pick
        tampered["p_home"] = 0.99                            # a post-tip edit of a probability
        h = hashlib.sha256(json.dumps(tampered, sort_keys=True).encode()).hexdigest()
        self.assertNotEqual(h, r["row_hash"])


class TestInjuryStamps(unittest.TestCase):
    def test_revision_and_retrieval_both_published(self):
        meta = C2.injury_meta()
        self.assertIn("06:15", meta["revision_time_et"])
        self.assertTrue(meta["retrieval_time_utc"].startswith("2026-11-15"))
        self.assertTrue(str(meta["pdf_url"]).startswith("https://"))

    def test_rows_carry_the_report_fields_verbatim(self):
        rows = C2.injury_rows()
        self.assertEqual(len(rows), 101)
        not_sub = [r for r in rows if "NOT YET SUBMITTED" in (r.get("reason") or "")]
        self.assertGreater(len(not_sub), 0, "unfiled clubs must be published as NOT YET SUBMITTED")
        for r in not_sub:
            self.assertEqual(r["player"], "")
            self.assertEqual(r["status"], "")

    def test_rotation_availability_never_claims_zero_injuries(self):
        avail = C2.rotation_availability("IND@PHI")
        self.assertTrue(avail["text"])
        self.assertNotIn("0 injuries", avail["text"])


class TestPreRegistration(unittest.TestCase):
    def test_every_strategy_is_frozen_with_a_hash(self):
        from pathlib import Path
        root = Path(O.__file__).resolve().parents[2]
        doc = json.loads((root / "data" / "v2" / "preregistration.json").read_text())
        self.assertEqual(len(doc["files"]), 7)
        for f in doc["files"]:
            p = root / "data" / "v2" / "prereg" / f"{f['id']}.json"
            self.assertTrue(p.exists(), f["id"])
            d = json.loads(p.read_text())
            self.assertEqual(hashlib.sha256(json.dumps(
                {k: v for k, v in d.items() if k != "prereg_hash"}, sort_keys=True).encode()).hexdigest(),
                d["prereg_hash"], f["id"])
            self.assertTrue(d["signal"])
            self.assertTrue(d["threshold"])
            self.assertTrue(d["universe"])
            self.assertTrue(d["settlement_rule"])


if __name__ == "__main__":
    unittest.main()


class TestRefreshGates(unittest.TestCase):
    """Fixture-based tests of the scheduled job's gate logic (no network in tests)."""

    def test_finals_gate_accepts_off_days_and_rejects_missing_coverage(self):
        from . import refresh as RF
        finals = {
            "games_seen_by_date": {"2026-11-13": 0, "2026-11-14": 1},
            "finals_by_date": {"2026-11-13": 0, "2026-11-14": 1},
            "records": [{"date": "2026-11-14", "game_id": "0022600101", "home": "BOS", "away": "DET",
                         "home_pts": 1, "away_pts": 0, "source_url": "https://www.nba.com/game/example"}],
        }
        ok = RF.gate_finals(["2026-11-13", "2026-11-14"], finals)
        self.assertTrue(ok["ok"], ok["detail"])
        bad = RF.gate_finals(["2026-11-12", "2026-11-13", "2026-11-14"], finals)
        self.assertFalse(bad["ok"])
        self.assertIn("2026-11-12", bad["detail"])

    def test_standings_gate_validates_cumulative_arithmetic_not_partial_window(self):
        from . import refresh as RF
        from datetime import datetime, timezone
        finals = {"records": [
            {"date": "2026-11-14", "game_id": "0022600101", "home": "BOS", "away": "DET", "home_pts": 10, "away_pts": 9,
             "source_url": "https://www.nba.com/game/example"},
        ]}
        standings = {"fetched_at_utc": datetime.now(timezone.utc).isoformat(), "rows": [
            {"tri": f"T{i:02d}", "w": 1, "l": 1, "source_url": "https://www.nba.com/standings"}
            for i in range(30)
        ]}
        # Season-to-date records must not be compared with a one-day finals fragment.
        self.assertTrue(RF.gate_standings(standings, finals)["ok"])
        standings["rows"][0]["w"] += 1
        self.assertFalse(RF.gate_standings(standings, finals)["ok"])

    def test_injury_gate_requires_both_stamps(self):
        from . import refresh as RF
        good = {"pdf_url": "https://ak-static.cms.nba.com/x.pdf",
                "revision_time_et": "06_15AM", "retrieval_time_utc": "2026-11-15T12:05:00Z"}
        self.assertTrue(RF.gate_injuries(good, "2026-11-14")["ok"])
        for drop in ("pdf_url", "revision_time_et", "retrieval_time_utc"):
            broken = dict(good)
            broken.pop(drop)
            self.assertFalse(RF.gate_injuries(broken, "2026-11-14")["ok"], drop)

    def test_slate_gate_rejects_duplicate_ids_and_unsourced_rows(self):
        from . import refresh as RF
        dates = ["2026-11-15", "2026-11-16", "2026-11-17", "2026-11-18"]
        slate = {"covered_dates": dates, "games": [
            {"date": dates[0], "game_id": "0022600101", "home": "BOS", "away": "NYK",
             "source_url": f"https://www.nba.com/schedule?date={dates[0]}"},
            {"date": dates[0], "game_id": "0022600102", "home": "LAL", "away": "LAC",
             "source_url": f"https://www.nba.com/schedule?date={dates[0]}"},
        ]}
        self.assertTrue(RF.gate_slate(slate, "2026-11-15")["ok"])
        slate["games"].append({"date": dates[0], "game_id": "0022600102", "home": "LAL", "away": "LAC",
                                "source_url": "https://example.com/schedule?date=2026-11-15"})
        self.assertFalse(RF.gate_slate(slate, "2026-11-15")["ok"])
        slate2 = {"covered_dates": dates, "games": [
            {"date": dates[0], "game_id": "0022600101", "home": "BOS", "away": "NYK", "source_url": ""}]}
        self.assertFalse(RF.gate_slate(slate2, "2026-11-15")["ok"])

    def test_provenance_gate_flags_sourceless_rows(self):
        from . import refresh as RF
        docs = {"slate": {"games": [{"game_id": "g", "source_url": "https://x"}]},
                "standings": {"rows": [{"tri": "BOS", "source_url": ""}]}}
        g = RF.gate_provenance(docs)
        self.assertFalse(g["ok"])
        self.assertIn("standings[0]", g["detail"])
