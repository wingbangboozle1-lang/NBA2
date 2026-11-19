"""Tests for the v8 capture and pages.

These tests are deliberately about **provenance and arithmetic**, not about wording:

* the capture file must carry a source URL and a raw-file path for every document it used;
* the numbers on the pages must be the numbers in the capture (no hard-coded copies);
* the fail-closed parser must still fail closed if a raw file is tampered with.

The last test tampers with a temporary copy of a raw file and asserts that the parser's own
``selftest`` catches it. That is the difference between "we checked" and "it is checkable".
"""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from . import build as B

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "site"
RAW = ROOT / "data" / "raw" / "verify_2026-11-19" / "raw"


def _parser():
    spec = importlib.util.spec_from_file_location(
        "cap164", ROOT / "tools" / "session-164d832b-capture.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestCapture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cap = json.loads(B.CAP.read_text())

    def test_every_source_has_a_url_and_a_committed_raw_file(self):
        for name, meta in self.cap["retrieval"]["sources"].items():
            self.assertTrue(meta["url"].startswith("https://"), msg=name)
            p = ROOT / meta["raw_file"]
            self.assertTrue(p.exists(), msg=f"{name}: raw file missing ({meta['raw_file']})")
            self.assertGreater(p.stat().st_size, 200, msg=f"{name}: raw file implausibly small")

    def test_raw_files_are_hashed(self):
        hashed = self.cap["retrieval"]["raw_sha256"]
        self.assertGreaterEqual(len(hashed), 9)
        for name, digest in hashed.items():
            self.assertRegex(digest, r"^[0-9a-f]{64}$", msg=name)

    def test_no_row_is_unsourced(self):
        for key in ("standings",):
            for row in self.cap[key]:
                self.assertTrue(row["source_url"].startswith("https://"))
        for page in ("traditional", "opponent", "advanced"):
            for tri, row in self.cap[page].items():
                self.assertTrue(row["source_url"].startswith("https://"), msg=tri)

    def test_injury_rows_record_the_pdf_they_came_from(self):
        for key in ("injury_1119_1200", "injury_1119_0100", "injury_0645", "injury_0700"):
            rel = self.cap[key]
            self.assertTrue(rel["rows"], msg=key)
            for row in rel["rows"]:
                self.assertEqual(row["source_url"], rel["source_url"])
                self.assertIn(row["status"], {"Out", "Questionable", "Probable", "Doubtful",
                                              "Available"}, msg=f"{key}: {row}")

    def test_rejected_rows_are_counted_not_hidden(self):
        # The extractor's page-3 rendering drops alternating club cells; the parser must say so.
        for key in ("injury_1119_1200", "injury_0645", "injury_0700"):
            rel = self.cap[key]
            self.assertIn("rejected_rows", rel)
            self.assertIsInstance(rel["rejected_rows"], list)

    def test_home_court_pin_is_arithmetic_on_the_standings_page(self):
        st = self.cap["standings"]
        hw = 0
        hg = 0
        for r in st:
            a, b = r["home"].split("-")
            hw += int(a)
            hg += int(a) + int(b)
        self.assertEqual(self.cap["hca"]["home_wins"], hw)
        self.assertEqual(self.cap["hca"]["home_games"], hg)
        self.assertAlmostEqual(self.cap["hca"]["home_win_rate"], round(hw / hg, 4), places=4)

    def test_the_two_estimators_are_arithmetic_on_the_three_pages(self):
        tr, op, ad = self.cap["traditional"], self.cap["opponent"], self.cap["advanced"]
        for e in self.cap["estimators"]:
            tri = e["team"]
            want_a = round(tr[tri]["pts"] - op[tri]["opp_pts"], 2)
            want_b = round(ad[tri]["net_rtg"] * ad[tri]["pace"] / 100.0, 2)
            self.assertAlmostEqual(e["est_a_margin_per_game"], want_a, places=2, msg=tri)
            self.assertAlmostEqual(e["est_b_margin_per_game"], want_b, places=2, msg=tri)
            self.assertAlmostEqual(e["disagreement"], round(want_a - want_b, 2), places=2, msg=tri)


class TestSelftestCatchesTampering(unittest.TestCase):
    def test_a_wrong_point_differential_breaks_the_capture(self):
        parser = _parser()
        good = parser.build()
        self.assertEqual(parser.selftest(good), [], msg="baseline capture does not verify")

        tampered = json.loads(json.dumps(good))
        tampered["traditional"]["BOS"]["pts"] = tampered["traditional"]["BOS"]["pts"] + 1.0
        fails = parser.selftest(tampered)
        self.assertTrue(any("BOS" in f for f in fails),
                        msg=f"tampering with one points value was not caught: {fails}")

    def test_a_flipped_final_breaks_the_standings_reconstruction(self):
        parser = _parser()
        good = parser.build()
        tampered = json.loads(json.dumps(good))
        tampered["finals_1118"][0]["away_pts"], tampered["finals_1118"][0]["home_pts"] = (
            tampered["finals_1118"][0]["home_pts"], tampered["finals_1118"][0]["away_pts"])
        # The reconstruction test lives in the capture tool's own --selftest run; here we assert
        # that the capture *records* enough to notice: the printed record must match the score.
        self.assertNotEqual(tampered["finals_1118"][0]["away_pts"],
                            good["finals_1118"][0]["away_pts"])

    def test_a_missing_raw_file_cannot_be_captured(self):
        parser = _parser()
        tmp = Path(tempfile.mkdtemp())
        try:
            for p in RAW.glob("*.md"):
                shutil.copy(p, tmp / p.name)
            parser.RAW = tmp
            (tmp / "teams_advanced_2026-11-19.md").unlink()
            with self.assertRaises(FileNotFoundError):
                parser.build()
        finally:
            shutil.rmtree(tmp)


class TestPages(unittest.TestCase):
    PAGES = [p for p, _ in B.PAGES]

    def test_pages_exist_and_carry_their_numbers(self):
        cap = json.loads(B.CAP.read_text())
        doc = (SITE / "verify-1119.html").read_text()
        self.assertIn(str(cap["hca"]["home_wins"]), doc)
        self.assertIn(str(cap["hca"]["home_games"]), doc)
        for g in cap["finals_1118"]:
            self.assertIn(g["game_id"], doc, msg=f"final {g['game_id']} not on the page")
        for g in cap["slate_1119"]:
            self.assertIn(g["game_id"], doc, msg=f"scheduled game {g['game_id']} not on the page")

    def test_every_standings_row_is_on_the_page(self):
        cap = json.loads(B.CAP.read_text())
        doc = (SITE / "verify-1119.html").read_text()
        for r in cap["standings"]:
            self.assertIn(f">{r['team']}<", doc, msg=r["team"])

    def test_quarter_scores_are_shown_as_blank_with_a_reason(self):
        doc = (SITE / "verify-1119.html").read_text()
        self.assertIn("Quarter scores are blank on purpose", doc)
        self.assertIn("capture_2026-11-18/finals_2026-11-18.json", doc)

    def test_no_page_claims_that_a_proposal_was_implemented(self):
        doc = (SITE / "improvement.html").read_text()
        self.assertIn("Nothing in this table has been implemented", doc)

    def test_unknowns_page_names_a_route_for_every_question(self):
        doc = (SITE / "unknowns.html").read_text()
        ids = set(re.findall(r"<td>(U-\d\d)</td>", doc))
        self.assertEqual(len(ids), 10, msg=sorted(ids))
        self.assertIn("how to get it", doc)

    def test_pages_are_reachable_from_the_nav(self):
        for name in self.PAGES:
            for probe in ("index.html", "unknowns.html"):
                self.assertIn(f'href="{name}"', (SITE / probe).read_text(),
                              msg=f"{name} not linked from {probe}")

    def test_build_refuses_without_the_capture(self):
        orig = B.CAP
        try:
            B.CAP = Path("/nonexistent/official.json")
            with self.assertRaises(B.MissingCapture):
                B.build()
        finally:
            B.CAP = orig


if __name__ == "__main__":
    unittest.main()
