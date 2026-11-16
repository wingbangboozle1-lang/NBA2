"""Regression tests for nba2.v2.check's local-link and anchor resolution (CR-V4-1).

The defect this pins: the checker resolved `page.html#section` to a file literally
named "page.html#section", so every fragment link was reported broken and the v4
register had to fall back to file-level links (change request CR-V4-1 from session
arena/b3914335-nba2). The checker must strip the fragment when resolving and then
verify that the fragment exists as an id/name in the target page. Pure `#anchor`
links are verified against their own page; external links are skipped.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from . import check as CK


PAGE = """<!DOCTYPE html>
<html><body>
<a name="top"></a>
{links}
<table><tr><td>a</td><td><a href="https://www.nba.com/standings">src</a></td></tr></table>
</body></html>"""

TARGET = """<!DOCTYPE html>
<html><body><h2 id="section-two">Two</h2><a name="legacy-anchor"></a></body></html>"""


class TestLocalLinkResolution(unittest.TestCase):
    def _check(self, links: str, extra_pages: dict[str, str] | None = None) -> list[str]:
        with tempfile.TemporaryDirectory() as td:
            site = Path(td)
            (site / "index.html").write_text(PAGE.format(links=links))
            (site / "other.html").write_text(TARGET)
            for name, body in (extra_pages or {}).items():
                (site / name).write_text(body)
            orig = CK.SITE
            try:
                CK.SITE = site
                return CK.check()
            finally:
                CK.SITE = orig

    def test_fragment_link_resolves_to_the_file_and_the_anchor(self):
        self.assertEqual(self._check('<a href="other.html#section-two">ok</a>'), [])

    def test_name_anchor_is_accepted(self):
        self.assertEqual(self._check('<a href="other.html#legacy-anchor">ok</a>'), [])

    def test_missing_fragment_is_reported_as_a_broken_anchor(self):
        problems = self._check('<a href="other.html#no-such-id">bad</a>')
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("broken anchor", problems[0])
        self.assertIn("no-such-id", problems[0])

    def test_missing_file_is_reported_as_a_broken_local_link(self):
        problems = self._check('<a href="gone.html#anywhere">bad</a>')
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("broken local link", problems[0])

    def test_same_page_anchor_is_checked_against_its_own_page(self):
        self.assertEqual(self._check('<a href="#top">bad</a>'), [])
        problems = self._check('<a href="#definitely-missing">bad</a>')
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("broken anchor", problems[0])

    def test_query_strings_do_not_confuse_resolution(self):
        self.assertEqual(self._check('<a href="other.html?v=2#section-two">ok</a>'), [])

    def test_external_links_are_skipped(self):
        self.assertEqual(
            self._check('<a href="https://example.com/gone#x">ok</a>'
                        '<a href="mailto:a@b.c">ok</a>'), [])


if __name__ == "__main__":
    unittest.main()
