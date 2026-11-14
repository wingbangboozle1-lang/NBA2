"""Tests for the live-verification module (session arena/ab8743d8-nba2).

These lock in the two claims that would be most damaging if they silently drifted:

* the staleness test must keep explaining EVERY stale row (an unexplained row means either the
  reconstruction is wrong or the transcription was), and
* the grading arithmetic must stay honest — 8 recorded wins must never be reported as 8 games,
  and the no-price policy must never quietly gain a PnL.

Run:  python3 -m unittest discover -s nba2/v2 -t . -p 'test_*.py'
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from . import live as LV

ROOT = Path(__file__).resolve().parents[2]


class TestStaleness(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.st = LV.staleness()

    def test_evidence_present(self):
        self.assertTrue(self.st, "audit/2026-11-14 captures must be committed with the site")
        self.assertEqual(self.st["published_rows"], 30)

    def test_every_stale_row_is_explained(self):
        # A single unexplained row would mean the published table is wrong for a reason the
        # nine 11/13 finals do not account for — i.e. a transcription defect, not ageing.
        self.assertEqual(self.st["n_unexplained"], 0,
                         f"unexplained stale rows: {[r for r in self.st['stale_rows'] if r['cause'] != 'PRE_FINALS']}")

    def test_stale_count_equals_row_difference(self):
        self.assertEqual(self.st["n_stale"], self.st["published_rows"] - self.st["match_live_standings"])

    def test_published_table_matches_live_standings(self):
        # Direction of the finding AFTER the 2026-11-14 refresh (session arena/ac5fab5c-nba2):
        # the committed table was re-transcribed from live nba.com/standings, so the staleness
        # this module was written to detect (a pre-finals snapshot) is resolved. The check is
        # kept, inverted: the table must now agree with live standings on every row.
        self.assertEqual(self.st["match_live_standings"], 30)
        self.assertEqual(self.st["n_stale"], 0)
        self.assertGreater(self.st["match_live_standings"], self.st["match_pre_final_state"])


class TestGrading(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gr = LV.grade()

    def test_nine_games_graded(self):
        self.assertEqual(self.gr["games_graded"], 9)

    def test_every_final_has_two_official_sources(self):
        for g in self.gr["games"]:
            self.assertTrue(g["source"].startswith("https://www.nba.com/game/"))
            self.assertTrue(g["source_second"].startswith("https://www.nba.com/games"))

    def test_recorded_wins_exceed_distinct_games(self):
        # The whole point of the disclosure: do not let this regress into "8-0".
        self.assertEqual(self.gr["recorded_signals_graded"], 8)
        self.assertEqual(self.gr["distinct_games_graded"], 4)
        self.assertGreater(self.gr["recorded_signals_graded"], self.gr["distinct_games_graded"])

    def test_no_pnl_anywhere(self):
        for row in self.gr["signals"]:
            self.assertNotIn("profit_units", row, "profit must not appear without a committed price")
        self.assertIn("not published", self.gr["pricing_note"])

    def test_no_strategy_is_ranked_on_four_games(self):
        for s in self.gr["strategies"]:
            if s["graded"]:
                self.assertFalse(s["sample_adequate"])
                self.assertEqual(s["verdict"], "insufficient evidence")

    def test_sign_test_reproduces_by_hand(self):
        # 4 wins from 4 at a fair coin is 1/16 = 0.0625.
        for s in self.gr["strategies"]:
            if s["graded"] == 4:
                self.assertAlmostEqual(s["sign_p"], 0.0625, places=4)
                self.assertFalse(s["beats_luck_5pct"])

    def test_side_accuracy_reported_with_baselines(self):
        sa = self.gr["side_accuracy"]
        self.assertEqual(sa["n"], 9)
        for k in ("model", "net_rating_baseline", "always_home"):
            self.assertIn(k, sa)
        self.assertLessEqual(sa["model"], sa["n"])

    def test_naive_total_baseline_is_honest(self):
        # The model's total MAE ties the flat-224 baseline; that tie must be visible, not hidden.
        lf = self.gr["line_forecast"]
        self.assertAlmostEqual(lf["total_mae"], lf["naive_total_mae"], places=3)


class TestDecisionQueue(unittest.TestCase):
    def test_queue_reads_shared_register(self):
        dq = LV.decision_queue()
        reg = json.loads((ROOT / "suggestions" / "SUGGESTIONS.json").read_text())["suggestions"]
        ids = {r["id"] for r in reg}
        for it in dq["items"]:
            self.assertIn(it["id"], ids)

    def test_nothing_is_auto_accepted(self):
        dq = LV.decision_queue()
        for it in dq["items"]:
            self.assertIn(it["status"], {"implemented this session", "awaiting owner decision"})

    def test_every_item_has_both_links(self):
        for it in LV.decision_queue()["items"]:
            self.assertTrue(it["source"].startswith("https://"))
            self.assertTrue(it["evidence"].startswith("https://"))


class TestNewQuestions(unittest.TestCase):
    def test_questions_are_from_the_shared_register(self):
        items = LV.new_questions()["items"]
        self.assertTrue(items)
        reg = json.loads((ROOT / "requirements" / "QUESTIONS.json").read_text())["questions"]
        ids = {q["id"] for q in reg}
        for q in items:
            self.assertIn(q["id"], ids)
            self.assertTrue(q["source"].startswith("https://"))


if __name__ == "__main__":
    unittest.main()
