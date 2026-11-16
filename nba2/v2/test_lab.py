"""Tests for the strategy lab (session arena/ac5fab5c-nba2).

These guard the four claims that would be most damaging if they silently drifted:

* the walk-forward must not leak (a profitable backtest that saw the future is worthless),
* the bivariate-normal parlay price must respect the Fréchet bounds and its closed forms,
* the published history must rebuild the official standings exactly, and
* no strategy may be ranked or staked while its blocking gates fail.

Run:  python3 -m unittest discover -s nba2/v2 -t . -p 'test_*.py'
"""
from __future__ import annotations

import glob
import json
import unittest
from collections import Counter
from pathlib import Path

from . import official as O
from . import strategy_lab as SL

ROOT = Path(__file__).resolve().parents[2]


class TestHistoryCompleteness(unittest.TestCase):
    """The 188 official finals (183 in history + the 5 of 11/14 in the dated capture)
    must rebuild every standings record exactly."""

    @classmethod
    def setUpClass(cls):
        cls.games = SL.load_games()

    def test_every_game_id_is_unique(self):
        ids = [g["game_id"] for g in self.games]
        self.assertEqual(len(ids), len(set(ids)), "a duplicated game id would double-count")

    def test_history_is_188_games(self):
        # Named for the count it was written against; the invariant is the one that matters:
        # every final is unique by game id, wins balance losses, and the count is at least
        # the 188 the lab was calibrated on (the committed history only grows).
        ids = [g["game_id"] for g in self.games]
        self.assertEqual(len(ids), len(set(ids)), "duplicate game id in the history")
        self.assertGreaterEqual(len(self.games), 188)
        from nba2.v2 import official as O
        self.assertEqual(sum(v[0] for v in O.TEAMS.values()), len(self.games),
                         "official team table no longer matches the committed finals")

    def test_rebuilt_records_equal_official_standings(self):
        w, l = Counter(), Counter()
        for g in self.games:
            win, lose = ((g["home"], g["away"]) if g["home_pts"] > g["away_pts"]
                         else (g["away"], g["home"]))
            w[win] += 1
            l[lose] += 1
        for t, (ow, ol, *_rest) in O.TEAMS.items():
            self.assertEqual((ow, ol), (w[t], l[t]), f"{t}: standings {ow}-{ol} vs rebuilt {w[t]}-{l[t]}")

    def test_home_and_road_splits_also_match(self):
        hw, hl, rw, rl = Counter(), Counter(), Counter(), Counter()
        for g in self.games:
            if g.get("neutral_site"):
                continue
            if g["home_pts"] > g["away_pts"]:
                hw[g["home"]] += 1
                rl[g["away"]] += 1
            else:
                hl[g["home"]] += 1
                rw[g["away"]] += 1
        for t, (_w, _l, ohw, ohl, orw, orl, *_r) in O.TEAMS.items():
            self.assertEqual((ohw, ohl), (hw[t], hl[t]), f"{t} home split")
            self.assertEqual((orw, orl), (rw[t], rl[t]), f"{t} road split")

    def test_every_game_carries_an_official_source_url(self):
        for g in self.games:
            self.assertTrue(g.get("source_url", "").startswith("https://www.nba.com/game/"), g)


class TestNoLookAhead(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.games = SL.load_games()
        cls.preds = SL.walk_forward(cls.games)

    def test_no_prediction_sees_its_own_day_or_later(self):
        audit = SL.leakage_audit(self.preds, self.games)
        self.assertEqual(audit["n_violations"], 0, audit["offending_game_ids"])

    def test_predictions_cover_every_game_after_the_first_date(self):
        # Walk-forward coverage is a rule, not a constant. A prediction can only exist once
        # the model has something to fit on, so the invariant is: EVERY game in which both
        # clubs had already played at least one official final must carry a prediction. The
        # pre-season-opening games (a club's first appearance) legitimately have none. A
        # remembered constant such as 172 breaks the moment a night of results is appended,
        # which is precisely what the results feed is for.
        from collections import Counter
        played = Counter()
        first_appearance = []
        for g in sorted(self.games, key=lambda x: (x["date"], x["game_id"])):
            if played[g["away"]] == 0 or played[g["home"]] == 0:
                first_appearance.append(g["game_id"])
            played[g["away"]] += 1
            played[g["home"]] += 1
        have = {p.game_id for p in self.preds}
        missing = [g for g in self.games
                   if g["game_id"] not in have and g["game_id"] not in set(first_appearance)]
        self.assertEqual(missing, [],
                         f"{len(missing)} game(s) have no prediction although both clubs had "
                         f"already played: {[m['game_id'] for m in missing][:5]}")
        self.assertEqual(len(self.preds), len(self.games) - len(first_appearance),
                         f"{len(self.preds)} predictions for {len(self.games)} finals minus "
                         f"{len(first_appearance)} first-appearance game(s)")


class TestParlayMath(unittest.TestCase):
    def test_independence_returns_the_product(self):
        self.assertAlmostEqual(SL._bivariate_normal_upper(0.5, 0.5, 0.0), 0.25, places=4)
        self.assertAlmostEqual(SL._bivariate_normal_upper(0.6, 0.7, 0.0), 0.42, places=3)

    def test_perfect_positive_correlation_returns_the_minimum(self):
        self.assertAlmostEqual(SL._bivariate_normal_upper(0.6, 0.7, 0.999), 0.60, places=2)

    def test_perfect_negative_correlation_returns_the_frechet_lower_bound(self):
        # max(0, p1 + p2 - 1) = 0.30
        self.assertAlmostEqual(SL._bivariate_normal_upper(0.6, 0.7, -0.999), 0.30, places=2)

    def test_is_monotone_increasing_in_rho(self):
        vals = [SL._bivariate_normal_upper(0.6, 0.6, r) for r in (-0.5, -0.2, 0, 0.2, 0.5, 0.8)]
        self.assertEqual(vals, sorted(vals))

    def test_symmetric_in_the_legs(self):
        self.assertEqual(SL._bivariate_normal_upper(0.62, 0.71, 0.33),
                         SL._bivariate_normal_upper(0.71, 0.62, 0.33))

    def test_respects_frechet_bounds(self):
        for a in (0.15, 0.4, 0.75, 0.9):
            for b in (0.2, 0.5, 0.85):
                for r in (-0.9, -0.4, 0.0, 0.4, 0.9):
                    v = SL._bivariate_normal_upper(a, b, r)
                    self.assertGreaterEqual(v, max(0.0, a + b - 1) - 1e-3, (a, b, r, v))
                    self.assertLessEqual(v, min(a, b) + 1e-3, (a, b, r, v))


class TestLab(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rep = SL.run()

    def test_gate_g6_fails_because_there_is_no_price(self):
        g6 = next(g for g in self.rep["gates"] if g["id"] == "G6")
        self.assertEqual(g6["verdict"], "FAIL")

    def test_gate_g12_passes(self):
        g12 = next(g for g in self.rep["gates"] if g["id"] == "G12")
        self.assertEqual(g12["verdict"], "PASS")

    def test_no_strategy_is_reward_eligible_while_a_gate_blocks(self):
        for r in self.rep["leaderboard"]["ranked"]:
            self.assertFalse(r["eligible_for_reward"])
            self.assertIn("G6", r["blocked_by"])

    def test_player_prop_strategy_generates_no_bets(self):
        s7 = next(s for s in self.rep["strategies"] if s["sid"] == "S7")
        self.assertEqual(s7.get("n", 0), 0)

    def test_every_correlation_row_is_either_measured_or_explained_as_blocked(self):
        for row in self.rep["correlations"]:
            if row["status"] == "BLOCKED":
                self.assertTrue(row["note"], row["quantity"])
            else:
                self.assertIsNotNone(row["r"], row["quantity"])
                self.assertIsNotNone(row["ci95"], row["quantity"])

    def test_luck_report_flags_tiny_samples_even_when_p_is_significant(self):
        s4 = next(r for r in self.rep["luck"]["rows"] if r["sid"] == "S4")
        self.assertLess(s4["n"], 30)
        self.assertIn("SAMPLE TOO SMALL", s4["verdict"])

    def test_slate_window_is_three_days(self):
        from .official import WINDOW_START, WINDOW_END
        import datetime as dt
        self.assertEqual((dt.date.fromisoformat(WINDOW_END)
                          - dt.date.fromisoformat(WINDOW_START)).days, 3)
