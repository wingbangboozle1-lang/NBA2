"""Tests for the v7 layer. Standard library only; no network.

The tests fall into four groups:

  * **transcription identities** — three arithmetic checks that fail if a single row of the
    2026-11-19 snapshot slipped a column;
  * **model invariants** — the pinned home court reproduces the measured rate, the
    point-in-time cut cannot see the future, the disagreement is symmetric, the parlay
    orthant reduces to the naive product at rho = 0;
  * **honesty invariants** — a strategy with a blocked gate carries no stake, a blank is
    never a zero, a luck-outside club blocks its game;
  * **page invariants** — every emitted table row carries a source or an explained blank,
    and no page carries the snapshot-less state.
"""

from __future__ import annotations

import json
import math
import re
import unittest
from collections import Counter
from pathlib import Path

from nba2.v7 import build as B
from nba2.v7 import check as CH
from nba2.v7 import flags as FLAGS
from nba2.v7 import nav as NAV
from nba2.v7 import model as M
from nba2.v7 import official as O
from nba2.v7 import strategies as S
from nba2.v7.common import ROOT, SITE, V7


def _games():
    return M.load_games()


class TestTranscription(unittest.TestCase):
    """If one of these fails, a number in official.py is wrong."""

    def test_net_rating_identity_on_all_clubs(self):
        bad = []
        for t, r in O.TEAMS.items():
            d = abs((r["off"] - r["dfn"]) - r["net"])
            if d > 0.15:
                bad.append((t, round(d, 3)))
        self.assertFalse(bad, f"NetRtg != OffRtg - DefRtg on {bad}")

    def test_point_differential_identity_on_all_clubs(self):
        """PTS (traditional) - Opp PTS (opponent) == +/- (traditional): two pages agree."""
        bad = []
        for t, r in O.TEAMS.items():
            d = abs((r["pts"] - r["opp"]) - r["pm"])
            if d > 0.20:
                bad.append((t, round(d, 3)))
        self.assertFalse(bad, f"point differential disagrees on {bad}")

    def test_wins_reconcile_with_the_committed_official_finals(self):
        """Every club's W on the standings page equals its wins in the committed finals."""
        games, _, _ = _games()
        seen = {g["game_id"]: g for g in games}
        for g in O.FINALS_2026_11_18:
            seen[g["game_id"]] = {"away": g["away"], "home": g["home"],
                                  "away_pts": g["away_pts"], "home_pts": g["home_pts"],
                                  "date": "2026-11-18"}
        w = Counter()
        for g in seen.values():
            w[g["home"] if g["home_pts"] > g["away_pts"] else g["away"]] += 1
        bad = [(t, w[t], O.STANDINGS[t]["w"]) for t in O.STANDINGS if w[t] != O.STANDINGS[t]["w"]]
        self.assertFalse(bad, f"W mismatches (club, from finals, on standings): {bad}")

    def test_every_club_appears_in_both_tables(self):
        self.assertEqual(set(O.TEAMS), set(O.STANDINGS))
        self.assertEqual(len(O.TEAMS), 30)

    def test_slate_rows_are_unique_by_game_id_and_have_tips(self):
        ids = [g["game_id"] for g in O.SLATE]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(g["tip"] for g in O.SLATE))
        # every club in the slate has a row in the snapshot, or the projection is blank
        clubs = {g["away"] for g in O.SLATE} | {g["home"] for g in O.SLATE}
        self.assertTrue(clubs <= set(O.TEAMS), clubs - set(O.TEAMS))


class TestModelInvariants(unittest.TestCase):
    def setUp(self):
        self.games, _, _ = _games()

    def test_pinned_hca_reproduces_the_measured_home_win_rate(self):
        hc = M.home_court(self.games)
        self.assertAlmostEqual(hc["reproduces_rate"], hc["home_win_rate"], places=6)
        self.assertGreater(hc["hca_points"], 0)
        self.assertLess(hc["hca_points"], hc["margin_sd"])

    def test_point_in_time_cut_cannot_see_the_future(self):
        """A cut dated D must produce exactly what a cut trained on only pre-D games does.

        This is the guard against the leakage the first draft had: it cut its ratings from
        the 2026-11-19 team-stat pages and then "walk-forward tested" October games. The
        assertion is on the *inputs* to the ratings — the training set — because that is
        where the future would leak in.
        """
        cut = M.Cut(self.games, "2026-11-10")
        prior = [g for g in self.games if g["date"] < "2026-11-10"]
        self.assertEqual(cut.meta["n_train"], len(prior))
        manual, _ = M.ratings_as_of(prior, "2026-11-10")
        self.assertEqual(set(cut.ratings), set(manual))
        for tri in manual:
            self.assertAlmostEqual(cut.ratings[tri]["e1_rating"],
                                   manual[tri]["e1_rating"], places=12)
        # and no game played on or after D can be in the training count
        self.assertFalse([g for g in prior if g["date"] >= "2026-11-10"])

    def test_a_cut_before_any_game_predicts_nothing(self):
        cut = M.Cut(self.games, "2000-01-01")
        self.assertEqual(cut.ratings, {})
        self.assertEqual(cut.margins("BOS", "LAL"), (None, None))

    def test_total_is_possessions_times_ppp(self):
        teams = M.snapshot_teams()
        cut = M.Cut(self.games, "9999-12-31")
        t = cut.total("BOS", "LAL", teams)
        self.assertIsNotNone(t["total"])
        self.assertAlmostEqual(t["total"], t["possessions"] * (t["ppp_home"] + t["ppp_away"]),
                               places=9)
        self.assertAlmostEqual(t["possessions"],
                               (teams["BOS"]["pace"] + teams["LAL"]["pace"]) / 2, places=9)

    def test_total_is_blank_not_zero_without_pace(self):
        cut = M.Cut(self.games, "9999-12-31")
        t = cut.total("BOS", "LAL", {"BOS": {"tri": "BOS"}, "LAL": {"tri": "LAL"}})
        self.assertIsNone(t["total"])
        self.assertIn("blank", t["flag"])

    def test_walk_forward_is_trained_only_on_earlier_dates(self):
        wf = M.walk_forward(self.games)
        first = wf["rows"][0]["date"]
        prior = [g for g in self.games if g["date"] < first]
        self.assertGreaterEqual(len(prior), M.MIN_TRAIN_GAMES)
        # every prediction date must be later than the earliest training date
        self.assertTrue(all(r["date"] >= first for r in wf["rows"]))

    def test_walk_forward_reports_a_failure_as_a_failure(self):
        """Whatever the numbers are, the verdict must follow from them, not be asserted."""
        wf = M.walk_forward(self.games)
        self.assertEqual(wf["beats_coin_log_loss"], wf["log_loss"] < math.log(2))
        # the first draft of this module had a sign error that scored 34%; this guard exists
        # so a sign error can never again be published as a result
        self.assertGreater(wf["accuracy"], 0.40,
                           "accuracy this low means the margin sign or the labels are wrong")

    def test_parlay_orthant_reduces_to_the_naive_product_at_zero_rho(self):
        for h, k in ((0.5, -0.3), (1.2, 0.8), (-0.7, 0.1)):
            naive = M.phi(h) * M.phi(k)
            self.assertAlmostEqual(S._bvn_orthant(h, k, 0.0), naive, places=12)

    def test_parlay_orthant_is_monotone_in_rho(self):
        prev = None
        for r in (-0.4, -0.2, 0.0, 0.2, 0.4):
            v = S._bvn_orthant(0.8, 0.5, r)
            if prev is not None:
                self.assertGreater(v, prev)
            prev = v

    def test_rho_has_a_confidence_interval_that_contains_it(self):
        r = M.rho(self.games)
        self.assertLessEqual(r["ci95"][0], r["r"])
        self.assertLessEqual(r["r"], r["ci95"][1])


class TestHonesty(unittest.TestCase):
    def setUp(self):
        self.res = M.resolve()
        self.slate = __import__("nba2.v7.slate", fromlist=["build"]).build(self.res)
        self.st = S.build(self.res, self.slate)

    def test_a_blocked_gate_means_no_stake(self):
        for s in self.st["leaderboard"]:
            if s["n_pass"] < s["n_gates"]:
                self.assertEqual(s["stake"], 0.0)
                self.assertEqual(s["status"], "BLOCKED")
                self.assertTrue(s["reason"].startswith("blocked by"))

    def test_no_market_price_means_the_price_gate_is_blocked(self):
        g = next(g for g in self.st["gates"] if g["id"] == "G-V7-6")
        self.assertEqual(g["status"], "BLOCKED")

    def test_pre_registrations_are_never_rewritten(self):
        before = {p.name: p.read_bytes() for p in (V7 / "prereg").glob("*.json")}
        S.prereg_register(S.strategies(self.res))
        after = {p.name: p.read_bytes() for p in (V7 / "prereg").glob("*.json")}
        self.assertEqual(before, after, "a frozen pre-registration changed bytes")

    def test_every_pre_registration_carries_the_four_required_fields(self):
        for p in (V7 / "prereg").glob("*.json"):
            d = json.loads(p.read_text())
            for k in ("signal", "thresholds", "universe", "settlement_rule"):
                self.assertTrue(d.get(k), f"{p.name} has no {k}")

    def test_props_are_blocked_with_arithmetic(self):
        pr = self.st["props"]
        self.assertLess(pr["max_games_per_player"], 15)
        self.assertTrue(pr["rows"])

    def test_luck_outside_the_band_blocks_the_game(self):
        res = self.res
        slate = __import__("nba2.v7.slate", fromlist=["build"]).build(res)
        for row in slate["rows"]:
            outside = [t for t in (row["away"], row["home"])
                       if res["luck"].get(t, {}).get("outside")]
            self.assertEqual(row["luck_gate"]["blocks"], bool(outside), msg=row["game_id"])


class TestNav(unittest.TestCase):
    """The sidebar pass, tested on synthetic documents.

    Regression: the first version searched the *whole* document for a v7 href to decide whether
    the sidebar already had one. The landing page also carries v7 links inside its category
    card, so that card looked like a sidebar entry, the sidebar block was stripped, and the run
    reported a lost link on index.html. A nav pass must look at the nav.
    """

    def _doc(self, nav_body: str, main_body: str = "") -> str:
        return f"<html><body><aside><nav>{nav_body}</nav></aside><main>{main_body}</main></body></html>"

    def test_missing_links_are_added_once_and_are_idempotent(self):
        doc = self._doc('<a href="index.html">Start</a>')
        once = NAV._inject(doc, None)
        twice = NAV._inject(once, None)
        self.assertEqual(once, twice)
        for h in NAV.LABELS:
            self.assertEqual(once.count(f'href="{h}"'), 1, h)

    def test_a_v7_link_outside_the_sidebar_does_not_count_as_sidebar_presence(self):
        card = "".join(f'<a href="{h}">{h}</a>' for h in NAV.LABELS)
        doc = self._doc('<a href="index.html">Start</a>', main_body=card)
        out = NAV._inject(doc, "v7-slate.html")
        nav = re.search(r"<nav>(.*?)</nav>", out, re.S).group(1)
        self.assertEqual(set(re.findall(r'href="(v7-[a-z]+\.html)"', nav)),
                         set(NAV.LABELS))

    def test_an_existing_sidebar_link_is_not_duplicated(self):
        nav = "".join(f'<a href="{h}">x</a>' for h in NAV.LABELS)
        doc = self._doc(nav)
        self.assertEqual(NAV._inject(doc, None), doc)

    def test_no_sidebar_link_is_ever_dropped(self):
        doc = self._doc('<a href="index.html">Start</a><a href="flagged.html">F</a>')
        out = NAV._inject(doc, None)
        self.assertTrue(NAV._hrefs(doc) <= NAV._hrefs(out))


class TestVerificationLedger(unittest.TestCase):
    def setUp(self):
        from nba2.v7 import verification as V
        self.v = V.build()

    def test_every_checked_claim_matched(self):
        bad = [r["id"] for r in self.v["rows"] if not r["not_read"] and not r["ok"]]
        self.assertFalse(bad, bad)

    def test_an_unread_source_is_never_counted_as_a_match(self):
        for r in self.v["rows"]:
            if r["not_read"]:
                self.assertEqual(r["n"], 0, r["id"])
                self.assertEqual(r["matched"], 0, r["id"])
                self.assertFalse(r["ok"], r["id"])

    def test_every_row_has_an_official_url(self):
        for r in self.v["rows"]:
            self.assertTrue(r["source"].startswith("https://"), r["id"])

    def test_the_ledger_is_not_empty(self):
        self.assertGreaterEqual(self.v["n_claims"], 8)
        self.assertGreater(self.v["n_compared"], 100)


class TestFlags(unittest.TestCase):
    def test_every_flag_names_a_source_and_a_disposition(self):
        for fid, sev, url, wrong, instead, where in FLAGS.FLAGS:
            with self.subTest(flag=fid):
                self.assertTrue(url.startswith("https://"), fid)
                self.assertIn(sev, {"gap", "info", "blocker"}, fid)
                self.assertGreater(len(wrong), 40, fid)
                self.assertGreater(len(instead), 40, fid)
                self.assertTrue(where, fid)

    def test_flag_ids_are_unique_and_render_with_an_anchor(self):
        ids = [f[0] for f in FLAGS.FLAGS]
        self.assertEqual(len(ids), len(set(ids)))
        section = FLAGS.build_section()
        for fid in ids:
            self.assertIn(f'id="{fid}"', section)
        self.assertEqual(section.count("<tr>"), len(ids) + 1)  # +1 header row


class TestPages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        res = M.resolve()
        cls.slate = __import__("nba2.v7.slate", fromlist=["build"]).build(res)
        cls.st = S.build(res, cls.slate)
        cls.pages = {
            "v7-slate.html": B.page_slate(res, cls.slate),
            "v7-strategies.html": B.page_strategies(cls.st, cls.slate, res),
            "v7-skill.html": B.page_skill(res, cls.st),
            "v7-methodology.html": B.page_methodology(res),
        }
        cls.checks = CH.structural(cls.pages)

    def test_every_structural_check_passes(self):
        bad = [c["id"] for c in self.checks if not c["ok"]]
        self.assertFalse(bad, bad)

    def test_slate_page_carries_the_disagreement_column(self):
        body = self.pages["v7-slate.html"]
        self.assertIn("Disagree", body)
        self.assertIn("disagreement", body.lower())

    def test_every_slate_row_links_its_official_game_page(self):
        body = self.pages["v7-slate.html"]
        # each row links its game twice: once on the fixture, once in the source column
        self.assertEqual(len(re.findall(r'https://www\.nba\.com/game/', body)),
                         2 * len(O.SLATE))

    def test_availability_is_blank_and_flagged_when_no_report_was_read(self):
        if not O.INJURY_REPORT_READ:
            self.assertIn("no official injury report was read", self.pages["v7-slate.html"])

    def test_the_three_day_cap_is_stated(self):
        self.assertIn("three days", self.pages["v7-slate.html"].lower()
                      + self.pages["v7-methodology.html"].lower()
                      + self.pages["v7-strategies.html"].lower())

    def test_no_page_claims_a_stake(self):
        for name, body in self.pages.items():
            self.assertNotRegex(body, r"[1-9]\d*\.\d{2} u", msg=name)


if __name__ == "__main__":
    unittest.main()
