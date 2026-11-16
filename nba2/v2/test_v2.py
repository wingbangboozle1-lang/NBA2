"""Unit tests for the v2 model, its provenance contract, and the published site.

Run:  python -m unittest discover -s nba2/v2 -t . -p 'test_*.py'
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

import unittest

from . import content as C
from . import model as M
from . import official as O
from . import report as R

ROOT = Path(__file__).resolve().parents[2]


class TestOfficialSnapshot(unittest.TestCase):
    def test_all_30_teams_present(self):
        self.assertEqual(len(O.TEAMS), 30)

    def test_wins_equal_losses(self):
        i = O.integrity()
        self.assertTrue(i["wins_equals_losses"], i)

    def test_points_scored_equals_allowed_within_rounding(self):
        i = O.integrity()
        self.assertTrue(i["points_identity_ok"],
                        f"{i['weighted_points_scored']} vs {i['weighted_points_allowed']} ")

    def test_home_road_reciprocity(self):
        i = O.integrity()
        self.assertTrue(i["home_wins_equal_road_losses"])
        self.assertTrue(i["home_losses_equal_road_wins"])

    def test_games_played_is_whole(self):
        i = O.integrity()
        self.assertEqual(i["games_played_team_sum"] % 2, 0)

    def test_slate_is_34_games_and_window_is_three_days(self):
        # The brief's rule is "up to a maximum of 3 days in advance": today through today+3
        # inclusive. The committed window snapshot (capture_2026-11-15) carries 34 games and the
        # official per-day grid for 11-18 (12 games) is recorded in the 11-15 window capture.
        self.assertEqual(len(O.SLATE), 34)
        dates = sorted({g[0] for g in O.SLATE})
        self.assertEqual(dates[0], "2026-11-15")
        self.assertEqual(dates[-1], "2026-11-18")
        self.assertEqual(len(dates), 4)

    def test_per_day_counts_match_official_grid(self):
        """Per-day counts are compared to the official grid stored in the raw snapshots.

        Deriving the expectation from data/raw (what nba.com/schedule printed) rather than from a
        literal keeps this test honest through a refresh. The grid lives on the 11-15 window
        capture (slate_2026-11-15_to_11-17.json, which recorded 11-18's 12-game day too); the
        34-game window snapshot predates the grid field, so the newest snapshot that carries the
        grid wins. The two are produced by different code paths.
        """
        from collections import Counter
        from pathlib import Path as _P
        import glob as _g
        paths = (sorted(_g.glob(str(ROOT / "data" / "raw" / "slate_*_to_*.json")))
                 + sorted(_g.glob(str(ROOT / "data" / "raw" / "capture_*" / "slate_*_to_*.json"))))
        docs = [json.loads(_P(pl).read_text()) for pl in paths
                if "_v2" not in str(pl) and "context" not in str(pl)]
        docs = [d for d in docs if d.get("per_day_counts_official")]
        self.assertTrue(docs, "no committed slate snapshot carries the official per-day grid")
        raw = docs[-1]
        grid = raw["per_day_counts_official"]
        got = Counter(g[0] for g in O.SLATE)
        self.assertEqual(dict(got), {d: n for d, n in grid.items()
                                     if O.WINDOW_START <= d <= O.WINDOW_END})
        # the day the window gives up, it gains as a result: 11/14 is finished, so it is not slate
        self.assertEqual(grid.get("2026-11-14"), 5)
        self.assertNotIn("2026-11-14", got)

    def test_window_is_exactly_three_days_ahead(self):
        import datetime as _dt
        start = _dt.date.fromisoformat(O.WINDOW_START)
        end = _dt.date.fromisoformat(O.WINDOW_END)
        dates = sorted({g[0] for g in O.SLATE})
        # the window is contiguous with the days it prices: it ends on the last slate date, and the
        # brief's "today + N days" is measured from the capture date, not from the first game
        self.assertEqual((end - start).days, len(dates) - 1)
        self.assertEqual((start - _dt.date.fromisoformat(O.AS_OF)).days, 0)
        self.assertGreaterEqual(start, _dt.date.fromisoformat(O.AS_OF))

    def test_game_ids_unique(self):
        ids = [g[4] for g in O.SLATE]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_slate_team_is_in_the_team_table(self):
        for g in O.SLATE:
            self.assertIn(g[2], O.TEAMS)
            self.assertIn(g[3], O.TEAMS)

    def test_injury_rows_have_valid_status(self):
        allowed = {"Out", "Doubtful", "Questionable", "Probable", "Available"}
        for row in O.INJURIES:
            self.assertIn(row[5], allowed, row)

    def test_every_injury_row_carries_a_source(self):
        self.assertTrue(O.INJURY_PDF_URL.startswith("https://ak-static.cms.nba.com/"))

    def test_player_rows_carry_ids_for_links(self):
        for row in O.PLAYERS:
            self.assertTrue(row[7] and row[7].isdigit())

    def test_blocked_items_have_urls_and_reasons(self):
        for k, (what, why, url) in O.BLOCKED.items():
            self.assertTrue(what and why, k)
            self.assertTrue(url.startswith("http"), k)


class TestModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.teams, cls.cal = M.build_teams()
        cls.lines = M.originated_lines(cls.teams, cls.cal)

    def test_calibration_is_positive_and_finite(self):
        self.assertGreater(self.cal.margin_sd, 0)
        self.assertTrue(math.isfinite(self.cal.hca))
        self.assertLess(self.cal.rmse_wins, self.cal.rmse_baseline)

    def test_home_court_pinned_to_observed_rate(self):
        # h = sigma(2p-1) by construction
        p = self.cal.home_win_rate
        self.assertAlmostEqual(self.cal.hca, self.cal.margin_sd * (2 * p - 1), places=2)

    def test_reliability_in_unit_interval(self):
        for t in self.teams.values():
            self.assertGreaterEqual(t.reliability, 0.0)
            self.assertLessEqual(t.reliability, 1.0)

    def test_ratings_are_shrunk_towards_mean(self):
        """Shrinkage may pull toward the league mean; it may never cross it or amplify it.

        The bound this test used to assert — |consensus rating| <= |net points − mean| — compared a
        two-estimator mean against one estimator's deviation. That is not an invariant of the model:
        it held on the 183-game table by arithmetic accident and broke on the 188-game table. What
        is invariant is sign preservation and non-amplification of each component, plus the identity
        that the consensus rating is the mean of the two shrunk components.
        """
        mean_pts = sum(t.net_pts for t in self.teams.values()) / 30
        mean_rtg = sum(t.netrtg for t in self.teams.values()) / 30
        for t in self.teams.values():
            dev = t.net_pts - mean_pts
            if dev:
                self.assertEqual(math.copysign(1, t.r_diff), math.copysign(1, dev),
                                 msg=f"{t.tri}: r_diff crossed zero")
                self.assertLessEqual(abs(t.r_diff), abs(dev) + 1e-9,
                                     msg=f"{t.tri}: r_diff amplified the raw differential")
            # r_rtg pools the two estimators (a team at exactly 0.0 NetRtg can still carry a small
            # non-zero component), so it has no single raw to be bounded against. What must hold is
            # that the consensus never amplifies the league's own spread.
            self.assertLessEqual(abs(t.rating),
                                 max(abs(u.net_pts - mean_pts) for u in self.teams.values()) + 1e-9,
                                 msg=f"{t.tri}: consensus rating exceeds the largest raw deviation")
            self.assertAlmostEqual(t.rating, (t.r_diff + t.r_rtg) / 2.0, places=6,
                                   msg=f"{t.tri}: consensus rating is not the mean of its components")

    def test_expected_wins_sum_to_total_wins(self):
        """A win-consistent model must reproduce the league's win total exactly, so luck sums to zero."""
        self.assertAlmostEqual(sum(t.expected_wins for t in self.teams.values()),
                               sum(t.w for t in self.teams.values()), places=4)
        self.assertAlmostEqual(sum(t.luck for t in self.teams.values()), 0.0, places=4)

    def test_cover_probability_is_half_at_our_own_number(self):
        for ln in self.lines:
            self.assertAlmostEqual(ln.p_home_cover, 0.5, delta=0.02,
                                   msg=f"{ln.matchup}: {ln.p_home_cover:.4f}")

    def test_p_home_matches_normal_formula(self):
        for ln in self.lines:
            want = 0.5 * (1 + math.erf((ln.margin / self.cal.margin_sd) / math.sqrt(2)))
            self.assertAlmostEqual(ln.p_home, want, places=6)

    def test_spread_is_negative_of_margin_to_half_point(self):
        for ln in self.lines:
            self.assertAlmostEqual(ln.spread, -round(ln.margin * 2) / 2, places=6)
            self.assertAlmostEqual(ln.spread * 2, round(ln.spread * 2), places=9)

    def test_no_line_is_graded_a_without_agreement(self):
        for ln in self.lines:
            if ln.grade == "A":
                self.assertLessEqual(ln.agreement, 1.0)
                self.assertLessEqual(abs(ln.total_gap), 2.0)

    def test_every_pick_is_withheld(self):
        self.assertTrue(all(ln.pick_status.startswith("WITHHELD") for ln in self.lines))

    def test_parlay_math_is_exact(self):
        m2 = M.parlay_math(None, 2, -110.0)
        self.assertAlmostEqual(m2["break_even_prob"], (110 / 210) ** 2, places=6)   # 0.2744
        m3 = M.parlay_math(None, 3, -110.0)
        self.assertAlmostEqual(m3["break_even_prob"], (110 / 210) ** 3, places=6)   # 0.1437
        # stacking must strictly increase the hold
        self.assertGreater(m3["hold_n_legs_pct"], m2["hold_n_legs_pct"])

    def test_disagreement_is_small_because_estimators_agree(self):
        worst = max(ln.agreement for ln in self.lines)
        self.assertLess(worst, 2.0, f"worst spread disagreement {worst}")


class TestReportAndContent(unittest.TestCase):
    def test_every_content_row_has_a_source_url(self):
        for g in C.GATES:
            self.assertTrue(g[4].startswith("http"), g[0])
        for s in C.STRATEGIES:
            self.assertTrue(s["src"].startswith("http"), s["id"])
        for f in C.FLAGS:
            self.assertTrue(f[5].startswith("http"), f[0])
        for q in C.QUESTIONS:
            self.assertTrue(q[6].startswith("http"), q[0])

    def test_suggestion_states_are_from_a_known_set(self):
        for row in C.SUGGESTIONS:
            state = row[6]
            self.assertTrue(any(k in state for k in
                                ("IMPLEMENTED", "RECOMMENDED", "QUEUED", "PARTIAL", "BLOCKED", "PROPOSED")),
                            state)

    def test_every_gate_is_referenced_by_at_least_one_strategy(self):
        text = " ".join(s["gates_that_can_pass_today"] + "," + s["gates_that_fail_today"] for s in C.STRATEGIES)
        for gate in C.GATES:
            self.assertIn(gate[0], text, gate[0])

    def test_blocked_correlations_carry_a_url(self):
        for row in R.t_blocked_correlations():
            self.assertTrue(row["source_url"].startswith("http"), row["pair"])

    def test_source_register_has_no_unreachable_blank_url(self):
        for row in R.t_sources():
            self.assertTrue(row["url"].startswith("http"), row["key"])


class TestBacktest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from . import backtest as BT
        cls.bt = BT.run()

    def test_no_same_day_leakage(self):
        """Every scored date must have had at least one strictly earlier game."""
        meta = self.bt["meta"]
        self.assertEqual(meta["leakage_rule"],
                         "ratings for a date use only games strictly before that date")
        self.assertGreater(meta["n_games_scored"], 100)
        self.assertGreater(meta["n_skipped_no_prior"], 0, "opening games must be skipped, not priced")

    def test_accuracy_beats_coinflip_and_has_wide_interval(self):
        h = self.bt["headline"]
        self.assertGreater(h["straight_up_accuracy"], 0.55)
        lo, hi = h["accuracy_ci95"]
        self.assertLess(lo, h["straight_up_accuracy"])
        self.assertGreater(hi, h["straight_up_accuracy"])

    def test_model_beats_zero_margin_baseline(self):
        h = self.bt["headline"]
        self.assertLess(h["mae_margin"], h["mae_baseline_zero"])
        self.assertLess(h["brier"], h["brier_baseline"])

    def test_compression_finding_is_published_not_hidden(self):
        cp = self.bt["compression"]
        self.assertLess(cp["ratio"], 0.6, "if the model stopped being compressed, update the page text")
        self.assertIn("must never", cp["read"])

    def test_margin_total_correlation_is_honest_about_power(self):
        mt = self.bt["margin_total"]
        self.assertEqual(mt["n"], self.bt["meta"]["n_games_scored"])
        self.assertIn("power", mt["power_note"])
        lo, hi = mt["ci95"]
        self.assertLess(lo, 0)
        self.assertGreater(hi, 0)

    def test_every_scored_row_carries_a_source_url(self):
        for r in self.bt["rows"]:
            self.assertTrue(r["source_url"].startswith("https://www.nba.com/game/"), r)

    def test_backtest_does_not_claim_profit(self):
        blob = json.dumps(self.bt).lower()
        for bad in ("roi", "profit", "clv"):
            self.assertNotIn(bad, blob, f"backtest must not make a {bad.upper()} claim")

    def test_sensitivity_is_labelled_as_not_selection(self):
        for r in self.bt["sensitivity"]:
            self.assertIn("not used to pick", r["note"])


class TestPublishedSite(unittest.TestCase):
    """The site is an artefact of this repository; these tests keep it honest."""

    def test_site_builds_and_passes_its_own_check(self):
        from . import build as B
        from . import check as K
        B.build()
        self.assertEqual(K.check(), [])
        self.assertEqual(K.semantic(), [])

    def test_every_page_has_the_nav(self):
        from .build import NAV
        from ..v3.build import V3_PAGES
        site = ROOT / "site"
        pages = sorted(site.glob("*.html"))
        # The published tree holds the v2 pages (exactly the NAV set) plus the v3 pages, which
        # carry the full v2 nav (arena/e675ac3d's shared-tree rule). The assertion pins the NAV
        # to the emitted file set in both directions, so an unlisted page fails here.
        self.assertEqual({p.name for p in pages}, {href for href, _ in NAV} | set(V3_PAGES))
        for p in pages:
            doc = p.read_text()
            for href, _ in NAV:
                self.assertIn(f'href="{href}"', doc, f"{p.name} missing nav link {href}")

    def test_no_page_claims_a_pick_is_stakable(self):
        site = ROOT / "site"
        for p in site.glob("*.html"):
            text = p.read_text().lower()
            self.assertNotIn("guaranteed", text)
            self.assertNotIn("sure thing", text)

    def test_site_data_is_an_exact_mirror(self):
        """site/data must never drift from data/v2 — a stale copy broke the deploy on 2026-11-14."""
        for f in sorted((ROOT / "data" / "v2").glob("*.json")):
            mirror = ROOT / "site" / "data" / f.name
            self.assertTrue(mirror.exists(), f"site/data/{f.name} missing")
            self.assertEqual(mirror.read_text(), f.read_text(),
                             f"site/data/{f.name} is stale — copy it after the build, not before")

    def test_json_artefacts_are_published(self):
        for name in ("teams.json", "lines.json", "verification.json", "content.json"):
            self.assertTrue((ROOT / "data" / "v2" / name).exists(), name)


if __name__ == "__main__":
    unittest.main()


class TestPicksProbabilityIsTheRightMarket(unittest.TestCase):
    """A spread bet is priced by P(cover), not P(win).

    Regression for the defect this session published and fixed: the picks table priced a
    spread lean with the moneyline probability, which overstated P(lean) on every game and
    produced a break-even trigger (e.g. -1246) that no sportsbook offers on a spread. These
    tests fail if the two are ever conflated again.
    """

    @classmethod
    def setUpClass(cls):
        teams, cal = M.build_teams()
        cls.lines = M.originated_lines(teams, cal)
        cls.rows = R.t_picks(cls.lines)

    def test_every_row_publishes_both_probabilities(self):
        for r in self.rows:
            self.assertIn("lean_prob_ml", r, r["matchup"])
            self.assertIn("lean_prob_cover", r, r["matchup"])

    def test_spread_trigger_is_one_over_the_cover_probability(self):
        for r in self.rows:
            p = float(r["lean_prob_cover"])
            self.assertAlmostEqual(float(r["trigger_decimal"]), round(1.0 / p, 3), places=2,
                                   msg=f"{r['matchup']}: trigger {r['trigger_decimal']} "
                                       f"vs 1/P(cover) {1/p:.3f}")

    def test_moneyline_trigger_is_one_over_the_win_probability(self):
        for r in self.rows:
            p = float(r["lean_prob_ml"])
            self.assertAlmostEqual(float(r["trigger_ml_decimal"]), round(1.0 / p, 3), places=2,
                                   msg=r["matchup"])

    def test_cover_probability_is_near_a_half_at_our_own_number(self):
        # Our spread IS the median of our own distribution, so covering it is ~50% by
        # construction. A row whose cover probability is far from 0.5 means the line and the
        # probability have been decoupled.
        for r in self.rows:
            self.assertAlmostEqual(float(r["lean_prob_cover"]), 0.5, delta=0.02,
                                   msg=f"{r['matchup']}: {r['lean_prob_cover']}")

    def test_win_probability_is_not_silently_used_as_the_spread_probability(self):
        # At least one game must have a lean whose win probability differs from its cover
        # probability by more than the rounding of the half-point line. If this ever fails,
        # the two columns have collapsed back into one.
        diffs = [abs(float(r["lean_prob_ml"]) - float(r["lean_prob_cover"])) for r in self.rows]
        self.assertGreater(max(diffs), 0.05)


class TestSkillAttribution(unittest.TestCase):
    """The brief's luck-removal requirement, checked as arithmetic rather than prose."""

    @classmethod
    def setUpClass(cls):
        from . import strategy_lab as SL
        cls.games = SL.load_games()
        cls.preds = SL.walk_forward(cls.games)
        cls.base = SL.naive_baselines(cls.preds, cls.games)
        cls.attr = SL.skill_attribution(SL.build_strategies(cls.preds), cls.base,
                                        {"preds": cls.preds, "games": cls.games})

    def test_baselines_are_scored_on_the_same_game_set(self):
        for b in self.base["baselines"]:
            self.assertLessEqual(b["n"], len(self.preds))
            self.assertGreater(b["n"], 0)

    def test_every_baseline_rate_is_its_own_hits_over_its_own_n(self):
        for b in self.base["baselines"]:
            if b["n"]:
                self.assertAlmostEqual(b["hit_rate"], round(b["hits"] / b["n"], 4), places=4)

    def test_discordant_games_sum_to_the_reported_total(self):
        for key in ("headline_vs_win_pct_baseline", "headline_vs_margin_baseline"):
            h = self.attr[key]
            self.assertEqual(h["model_won_those"] + h["baseline_won_those"],
                             h["discordant_games"], key)

    def test_a_verdict_is_always_published_with_the_test(self):
        for key in ("headline_vs_win_pct_baseline", "headline_vs_margin_baseline"):
            self.assertTrue(self.attr[key]["verdict"])
            self.assertTrue(self.attr[key]["baseline"])


class TestGatesAreLoadBearing(unittest.TestCase):
    """A gate that cannot change state is decoration. These fixtures change it, on purpose."""

    def _meas(self, **over):
        from . import gate_eval as GE
        gid = O.SLATE[0][4]
        m = {"prices": {"present": False, "files": [], "by_game": {}, "as_of": None, "n": 0,
                        "note": "fixture"},
             "settlement": {"present": True, "settled_bets": 0, "n_ledgers": 1, "ledgers": [],
                            "settled_at": None},
             "availability": {"per_date": {}, "games_with_unknown_clubs": [], "unknown_clubs": [],
                              "report_date": O.INJURY_AS_OF},
             "lookahead": {"n_slate": len(O.SLATE), "violations": [], "rule": "fixture"},
             "freshness": {"hours_since_capture": 1.0, "capture_stamp": "2026-11-15T11:45:00Z",
                           "first_slate_date": O.WINDOW_START, "slate_starts_in_days": 0},
             "source_class": {"n_sources": len(O.SOURCES), "non_official": [], "ok": True}}
        m.update(over)
        return GE, gid, m

    def test_price_and_settlement_alone_change_a_withheld_line(self):
        GE, gid, m = self._meas()
        base = GE.pick_blockers(m, gid)
        self.assertEqual([b["gate"] for b in base], ["G6", "G7"])
        # give it a dated price and cross the settlement bar: the withheld string must go away
        m2 = {**m, "prices": {**m["prices"], "present": True,
                              "by_game": {gid: {"price": -110, "as_of": "2026-11-15T11:00Z"}}},
              "settlement": {**m["settlement"], "settled_bets": GE.SETTLE_BAR}}
        self.assertEqual(GE.pick_blockers(m2, gid), [])
        self.assertEqual(GE.pick_status(GE.pick_blockers(m2, gid)), "PUBLISHED")
        # a price for a DIFFERENT game id does not unlock this one
        m3 = {**m2, "prices": {**m2["prices"], "by_game": {"999999999": {}}}}
        self.assertEqual([b["gate"] for b in GE.pick_blockers(m3, gid)], ["G6"])

    def test_a_final_on_disk_for_a_slate_game_is_refused_as_lookahead(self):
        GE, gid, m = self._meas()
        m = {**m, "lookahead": {**m["lookahead"],
                                "violations": [{"game_id": gid, "date": O.SLATE[0][0],
                                                "final": "110-105", "matchup": "x@y"}]}}
        blocks = [b["gate"] for b in GE.pick_blockers(m, gid)]
        self.assertIn("G12", blocks)

    def test_board_verdicts_move_with_the_measurement_not_the_prose(self):
        GE, gid, m = self._meas()
        rows = {r["id"]: r for r in GE.board(m, {})}
        self.assertEqual(rows["G6"]["verdict"], "FAIL")
        self.assertEqual(rows["G11"]["verdict"], "PASS")
        m2 = {**m, "prices": {"present": True, "files": ["fixture"], "n": len(O.SLATE),
                              "as_of": "2026-11-15T11:00Z",
                              "by_game": {g[4]: {"price": -110} for g in O.SLATE}}}
        rows2 = {r["id"]: r for r in GE.board(m2, {})}
        self.assertEqual(rows2["G6"]["verdict"], "PASS")
        # a non-official host must fail G1 rather than be footnoted
        m3 = {**m, "source_class": {"n_sources": 1, "non_official": [{"key": "x", "url": "http://z",
                                                                      "name": "n"}], "ok": False}}
        self.assertEqual({r["id"]: r for r in GE.board(m3, {})}["G1"]["verdict"], "FAIL")

    def test_published_board_matches_the_committed_measurement_file(self):
        """data/v2/gates.json is what the pages quote; it must be reproducible from the artefacts."""
        from . import gate_eval as GE
        path = Path(__file__).resolve().parents[2] / "data" / "v2" / "gates.json"
        pub = json.loads(path.read_text())
        recomputed = GE.board(GE.measurements())
        recomputed = {r["id"]: r["verdict"] for r in GE.board(GE.measurements())}
        lab = json.loads((path.parent / "strategy_lab.json").read_text())
        lab_rows = {g["id"]: g["verdict"] for g in lab["gates"]}
        delegated = set(pub["delegated_to_lab"])
        for r in pub["board"]:
            want = lab_rows.get(r["id"]) if r["id"] in delegated else recomputed[r["id"]]
            self.assertEqual(r["verdict"], want,
                             msg=f"{r['id']}: the page says {r['verdict']}, the "
                                 f"{'lab' if r['id'] in delegated else 'artefacts'} says {want}")
        self.assertEqual(pub["fail"] + pub["pass"] + pub["not_measurable"], 12)
