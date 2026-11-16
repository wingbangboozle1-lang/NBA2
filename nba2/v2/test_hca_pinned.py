"""Home-court advantage is pinned to the measured home-win rate, and says so.

Brief item 11: "Pin home-court advantage to the measured home-win rate instead of
fitting it freely." Gap-map item IR-4 found the published label still said
"fitted". These tests keep the value and the wording in step.

Run:  python -m unittest discover -s nba2/v2 -t . -p 'test_hca_pinned.py'
"""

from __future__ import annotations

import unittest
from pathlib import Path

from . import model as M

ROOT = Path(__file__).resolve().parents[2]

# Every published v2 surface that mentions home-court. None may call it "fitted".
PUBLISHED_SURFACES = [
    ROOT / "site" / "index.html",
    ROOT / "site" / "lines.html",
    ROOT / "site" / "methodology.html",
]


class HomeCourtIsPinned(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, cls.cal = M.build_teams()

    def test_h_equals_sigma_times_2p_minus_1(self):
        # Pinning rule (model.py::_fit_constrained): h = sigma * (2p - 1), p = measured
        # league home-win rate. The only free parameter is sigma.
        expected = self.cal.margin_sd * (2.0 * self.cal.home_win_rate - 1.0)
        self.assertAlmostEqual(self.cal.hca, expected, delta=0.01)

    def test_published_implied_value_matches_fit(self):
        # The implied value the model publishes is the same number, to its 2 dp rounding.
        self.assertAlmostEqual(self.cal.hca, self.cal.impl_hca_from_win_rate, delta=0.01)

    def test_no_published_surface_calls_home_court_fitted(self):
        for path in PUBLISHED_SURFACES:
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("home-court (fitted", text, path.name)
            self.assertNotIn("a fitted home-court term", text, path.name)

    def test_builder_label_says_pinned(self):
        src = (ROOT / "nba2" / "v2" / "build.py").read_text(encoding="utf-8")
        self.assertIn("home-court (pinned to measured home-win rate, pts)", src)


if __name__ == "__main__":
    unittest.main()
