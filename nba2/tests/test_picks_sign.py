"""S-26 regression tests: strategy S2 must name the model's *favourite*, laying points.

Background (reproduced from source by session `arena/03a581a0-nba2`, 2026-11-14):

    nba2/model.py originate_line()
        margin   = (home_str + adj_home) - (away_str + adj_away) + HOME_ADV   # home's margin
        spread   = round(margin * 2) / 2                                      # == away's spread
        label    = f"{away_team} {spread:+.1f}"                               # away line, e.g. "POR -6.0"

    nba2/picks.py S2 (before the fix)
        if margin > 0:  sel = f"{home} {spread:+.1f}"        # home + away's number  -> dog side
        else:           sel = f"{away} {-spread:+.1f}"       # away with flipped sign -> dog side

Both branches therefore emitted the **underdog** side in all nine strong-margin games of the
committed slate (`POR +6.0` where the same file's label reads `POR -6.0`).  The strategy's own
comment says "Bet the model's favorite to cover", and `spread_edge` is published as
`abs(predicted_margin)` = "how far the favorite is expected to win by", so the favourite side
is the intended one.

These tests fail on the old expression and pass on `picks.spread_selection`.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load_picks_module():
    """`nba2/picks.py` does `from model import ...`, i.e. it expects `nba2/` on sys.path."""
    added = str(ROOT / "nba2")
    inserted = added not in sys.path
    if inserted:
        sys.path.insert(0, added)
    try:
        spec = importlib.util.spec_from_file_location("nba2_picks_under_test",
                                                      ROOT / "nba2" / "picks.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        if inserted:
            sys.path.remove(added)


picks = _load_picks_module()
spread_selection = picks.spread_selection


def _line(away, home, margin, home_prob):
    """Build the field set spread_selection reads, the way originate_line() fills it."""
    spread = round(margin * 2) / 2.0
    return {
        "away": away, "home": home,
        "predicted_margin": round(margin, 2),
        "originated_spread": spread,
        "originated_spread_label": f"{away} {spread:+.1f}",
        "home_win_prob": round(home_prob, 3),
        "away_win_prob": round(1 - home_prob, 3),
    }


class TestS2NamesTheFavourite(unittest.TestCase):
    def test_away_favourite_lays_points(self):
        # The exact line S-26 quotes: POR is the model's 6.07-point favourite.
        line = _line("POR", "SAC", -6.07, 0.329)
        sel, prob = spread_selection(line)
        self.assertEqual(sel, "POR -6.0")
        self.assertEqual(sel, line["originated_spread_label"],
                         "for an away favourite the selection must equal the file's own label")
        self.assertEqual(prob, line["away_win_prob"])

    def test_home_favourite_lays_points(self):
        line = _line("MIL", "ORL", 2.24, 0.566)
        sel, prob = spread_selection(line)
        self.assertEqual(sel, "ORL -2.0")
        # the mirrored away line is "MIL +2.0"; the selection must be its opposite side
        self.assertEqual(line["originated_spread_label"], "MIL +2.0")
        self.assertNotEqual(sel, "MIL +2.0")
        self.assertEqual(prob, line["home_win_prob"])

    def test_old_expression_is_reproduced_as_the_defect(self):
        """Pin the buggy expression so the defect cannot come back unnoticed."""
        line = _line("POR", "SAC", -6.07, 0.329)
        margin, spread = line["predicted_margin"], line["originated_spread"]
        old = (f"{line['home']} {spread:+.1f}" if margin > 0
               else f"{line['away']} {-spread:+.1f}")
        self.assertEqual(old, "POR +6.0")            # what the site used to publish
        self.assertNotEqual(old, spread_selection(line)[0])
        self.assertLess(float(spread_selection(line)[0].rsplit(" ", 1)[1]), 0.0,
                        "the fixed selection must LAY points, not take them")

    def test_every_strong_margin_selection_is_the_favourite_laying_points(self):
        slate = json.loads((ROOT / "nba2" / "data" / "picks.json").read_text())
        strong = [l for l in slate["lines"] if abs(l["predicted_margin"]) >= 4.0]
        self.assertEqual(len(strong), 9,
                         "the committed slate has exactly nine STRONG_MARGIN games")
        for line in strong:
            sel, _ = spread_selection(line)
            team, pts = sel.rsplit(" ", 1)
            pts = float(pts)
            favourite = line["home"] if line["predicted_margin"] > 0 else line["away"]
            self.assertEqual(team, favourite,
                             f"{line['away']}@{line['home']}: selection {sel} must name the "
                             f"model's favourite ({favourite})")
            self.assertLess(pts, 0.0,
                            f"{line['away']}@{line['home']}: {sel} must lay points")
            if team == line["away"]:
                self.assertEqual(sel, line["originated_spread_label"],
                                 "an away-favourite selection must reproduce the file's label")


class TestHistoricalForecastIsNotRestamped(unittest.TestCase):
    """`nba2/data/picks.json` is the repo's only out-of-sample forecast.

    S-26 proposes "regenerate picks.json".  That would restamp `generated_utc` with a
    post-hoc date and destroy the property the whole out-of-sample claim rests on, so the
    generator was fixed and the historical artefact was deliberately left byte-identical.
    This test makes that decision executable: if anyone regenerates the file, it fails.
    """

    def test_generated_utc_is_the_pre_tip_stamp(self):
        slate = json.loads((ROOT / "nba2" / "data" / "picks.json").read_text())
        self.assertEqual(slate["generated_utc"], "2026-11-13T22:30:00Z",
                         "the pre-tip stamp must never be restamped by a rebuild")

    def test_forecast_line_count_unchanged(self):
        slate = json.loads((ROOT / "nba2" / "data" / "picks.json").read_text())
        self.assertEqual(len(slate["lines"]), 23)


if __name__ == "__main__":
    unittest.main()
