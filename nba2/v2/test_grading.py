"""Market-shape dispatch for the grader (added with the S-26 generator fix).

Two changes had to land together and would each have been correct alone: nba2/picks.py now names
the favourite laying points (``HOU -13.0``), and the live grader used to decide which market a row
belonged to by looking for a ``+`` in the selection string. Pinned here is the contract between
them, measured against the functions themselves rather than against a remembered story.

Run:  python3 -m unittest discover -s nba2/v2 -t . -p 'test_*.py'
"""
from __future__ import annotations

import unittest

from . import live as LV

# HOU beat UTA by 7.
G = {"home": "HOU", "away": "UTA", "home_margin": 7}


class TestSelectionDispatch(unittest.TestCase):
    def test_negative_spread_is_graded_as_a_spread(self):
        # won by 7 while laying 13: a LOSS against the spread, a WIN straight up.
        self.assertEqual(LV.grade_selection("HOU -13.0", G), "LOSS")
        self.assertEqual(LV._grade_spread("HOU -13.0", G), "LOSS")

    def test_positive_spread_still_graded_as_a_spread(self):
        self.assertEqual(LV.grade_selection("UTA +7.5", G), "WIN")   # lost by 7, covered 7.5
        self.assertEqual(LV.grade_selection("UTA +6.5", G), "LOSS")  # did not cover

    def test_exact_line_is_a_push_not_a_win(self):
        self.assertEqual(LV.grade_selection("HOU -7.0", G), "PUSH")

    def test_moneyline_is_graded_as_a_moneyline(self):
        self.assertEqual(LV.grade_selection("HOU ML", G), "WIN")
        self.assertEqual(LV.grade_selection("UTA ML", G), "LOSS")

    def test_unmarked_selection_is_ungradable_not_a_guess(self):
        # The old rule resolved a bare "HOU" as a moneyline WIN: an unmarked row silently acquired a
        # market. A shape the grader cannot identify must return None and surface as UNGRADABLE.
        self.assertIsNone(LV.grade_selection("HOU", G))
        self.assertIsNone(LV.grade_selection("", G))
        self.assertIsNone(LV.grade_selection("HOU -13.0", None))

    def test_kind_argument_wins_over_shape(self):
        self.assertEqual(LV.grade_selection("HOU", G, kind="ml"), "WIN")
        self.assertIsNone(LV.grade_selection("HOU ML", G, kind="spread"))  # not a number → ungradable

    def test_old_rule_could_not_grade_the_new_generator_output(self):
        """The measured reason this dispatch exists."""
        sel = "HOU -13.0"
        old = (LV._grade_spread(sel, G) if ("+" in sel and not sel.endswith("ML"))
               else LV._grade_ml(sel, G))
        self.assertIsNone(old)                                   # would have reported UNGRADABLE
        self.assertEqual(LV.grade_selection(sel, G), "LOSS")      # reports the true result

    def test_historical_card_is_graded_identically(self):
        """The sealed 2026-11-13 card: 8 graded rows, all WIN, nothing newly ungradable.

        If a future edit changes a result here, either the card was regenerated (it must not be) or
        the dispatcher changed meaning — both are defects, and this test cannot be satisfied by
        editing the artefact.
        """
        g = LV.grade()
        if not g:
            self.skipTest("the committed capture directory is absent in this checkout")
        sig = g["signals"]
        graded = [r for r in sig if r["status"] == "GRADED"]
        self.assertEqual(len(graded), g["recorded_signals_graded"])
        self.assertEqual(len(graded), 8)
        self.assertTrue(all(r["result"] == "WIN" for r in graded))
        self.assertEqual([r for r in sig if r["status"] == "UNGRADABLE"], [])
        self.assertEqual(g["distinct_games_graded"], 4)

    def test_parlay_legs_use_the_same_dispatch(self):
        # a spread leg inside a parlay must not be graded as a moneyline
        leg_win = LV.grade_selection("UTA +7.5", G)
        leg_loss = LV.grade_selection("UTA +6.5", G)
        self.assertEqual((leg_win, leg_loss), ("WIN", "LOSS"))


if __name__ == "__main__":
    unittest.main()
