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
    """Every committed official final — the season history PLUS each dated capture (11/14,
    11/15, 11/16 and later) — must rebuild every standings record exactly.

    The count is derived, never hard-coded: it used to be pinned to 188 (history + the five
    11/14 finals), so the lab silently kept scoring an eleven-day-old season while the tree
    held 205 verified finals.
    """

    @classmethod
    def setUpClass(cls):
        cls.games = SL.load_games()

    def test_every_game_id_is_unique(self):
        ids = [g["game_id"] for g in self.games]
        self.assertEqual(len(ids), len(set(ids)), "a duplicated game id would double-count")

    def test_history_matches_the_committed_finals_count(self):
        """The lab must score every committed official final, not a remembered count.

        The count is derived by globbing the same folders the module globs, because the union
        ledger (``official_finals_union.json``) is only the recent window and counting it
        instead of the sources reports a phantom shortfall.
        """
        import glob as _glob
        decided = set()
        for pat in ("data/raw/history/games_*.json", "data/raw/results/results_*.json",
                    "data/raw/capture_*/results_*.json", "data/raw/refresh_*/results_*.json",
                    "data/raw/refresh_*/finals_*.json"):
            for f in _glob.glob(str(ROOT / pat)):
                doc = json.loads(Path(f).read_text())
                for r in (doc.get("records") or doc.get("games") or []):
                    if r.get("away_pts") is not None and r.get("home_pts") is not None \
                            and r.get("game_id"):
                        decided.add(r["game_id"])
        self.assertEqual(len(self.games), len(decided))
        self.assertGreaterEqual(len(self.games), 188,
                                "the lab must never score fewer finals than it did before")

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

    def test_predictions_cover_every_game_that_has_prior_data(self):
        # Walk-forward prices a date only from strictly earlier games, so the season's OPENING
        # date cannot be priced at all. Every game after it must be, and a fixture on a later
        # date whose clubs have both already played must never be silently skipped: asserting
        # a fixed 172 previously hid that each later finals file was not being scored.
        first = min(g["date"] for g in self.games)
        expected = sum(1 for g in self.games if g["date"] > first)
        priced = {p.game_id for p in self.preds}
        unpriced = [g for g in self.games
                    if g["date"] > first and g["game_id"] not in priced]
        # The only legitimate skips are the first games of clubs that had never appeared.
        first_seen = {}
        for g in sorted(self.games, key=lambda x: (x["date"], x["game_id"])):
            for club in (g["home"], g["away"]):
                first_seen.setdefault(club, g["date"])
        for g in unpriced:
            self.assertTrue(g["date"] == first_seen[g["home"]] or g["date"] == first_seen[g["away"]],
                            f"{g['game_id']} is priceable but was not priced")
        self.assertGreater(len(self.preds), 172)


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
