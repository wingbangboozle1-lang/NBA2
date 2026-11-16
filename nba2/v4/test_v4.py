"""Tests for the v4 player-level surface.

The tests are the gates' second half: the gates in :mod:`nba2.v4.gamelog` measure
the capture, and these assert that the measurement itself is wired to the data —
that a moved digit, a dropped row, or a silently blank column fails here.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from . import official as O
from . import gamelog as GL
from . import injury as IN
from . import minutes as MN
from . import build as B

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "site"


class TestCapture(unittest.TestCase):
    def test_every_captured_player_gate_passes(self):
        fails = [g for g in GL.gates() if g["status"] != "PASS"]
        self.assertEqual(fails, [], f"failing gates: {fails}")

    def test_declared_row_counts_match_the_file(self):
        for p in GL.players():
            self.assertEqual(len(p["games"]), p["rows_declared"], p["player"])

    def test_means_equal_the_official_header(self):
        for b in GL.baselines():
            h = b["official_header"]
            self.assertAlmostEqual(b["ppg"], h["ppg"], places=1, msg=b["player"])
            self.assertAlmostEqual(b["rpg"], h["rpg"], places=1, msg=b["player"])
            self.assertAlmostEqual(b["apg"], h["apg"], places=1, msg=b["player"])

    def test_no_minutes_over_a_game(self):
        for r in GL.rows():
            self.assertLessEqual(r["minutes_dec"], 48.0, r)

    def test_every_row_carries_a_game_id_and_a_source(self):
        for r in GL.rows():
            self.assertTrue(re.fullmatch(r"\d{10}", r["game_id"]), r)
            self.assertTrue(r["source_url"].startswith("https://www.nba.com/"), r)

    def test_player_ids_come_from_the_official_roster(self):
        ids = O.roster_ids()
        for p in GL.players():
            self.assertEqual(ids.get(p["player"]), p["player_id"], p["player"])

    def test_every_captured_player_is_on_the_release(self):
        names = {r["player"] for r in IN.player_rows(True)}
        for p in GL.players():
            self.assertIn(p["player"], names, p["player"])

    def test_capture_failures_publish_no_rows(self):
        for f in O.gamelogs()["capture_failures"]:
            self.assertNotIn(f["player"], [p["player"] for p in GL.players()])


class TestInjuryDiff(unittest.TestCase):
    def test_both_files_are_addressed_by_their_own_timestamp(self):
        self.assertIn("06_15PM", O.injury(True)["provenance"]["url"])
        self.assertIn("06_15AM", O.injury(False)["provenance"]["url"])

    def test_diff_keys_are_club_player_pairs(self):
        d = IN.diff()
        for c in d["changes"]:
            self.assertTrue(c["team"] and c["player"])
            self.assertNotEqual(c["from_status"], c["to_status"])

    def test_diff_is_reproducible(self):
        self.assertEqual(IN.diff(), IN.diff())

    def test_every_release_row_has_a_source(self):
        for r in IN.records(True):
            self.assertTrue(r["source_url"].startswith("https://"), r)

    def test_not_submitted_rows_have_no_player(self):
        for r in IN.not_submitted(True):
            self.assertEqual(r["player"], "")


class TestMinutes(unittest.TestCase):
    def test_at_risk_sums_only_captured_players(self):
        for team in MN.CAPTURED_CLUBS:
            a = MN.at_risk(team)
            s = sum(r["mpg"] for r in a["rows"] if r["mpg"] is not None)
            self.assertAlmostEqual(s, a["vacated_mpg"], places=1)

    def test_absorption_candidates_exclude_designated_players(self):
        for team in MN.CAPTURED_CLUBS:
            outs = {r["player"] for r in MN.release_outs(team)}
            for c in MN.absorption_candidates(team):
                self.assertNotIn(c["player"], outs)

    def test_redistribution_leaves_the_receiving_side_blank(self):
        for team in MN.CAPTURED_CLUBS:
            r = MN.redistribution(team)
            for row in r["rows"]:
                self.assertIsNone(row["new_mpg"], row)
                self.assertIsNone(row["new_share"], row)


class TestPages(unittest.TestCase):
    def test_bodies_are_deterministic(self):
        self.assertEqual(B.body_player_logs(), B.body_player_logs())
        self.assertEqual(B.body_rotation_impact(), B.body_rotation_impact())
        self.assertEqual(B.body_injury_diff(), B.body_injury_diff())

    def test_every_row_in_every_body_links_out(self):
        for name, fn in B.BODIES.items():
            doc = fn()
            for m in re.finditer(r"<tr[^>]*>(.*?)</tr>", doc, re.S):
                if "<td" not in m.group(1):
                    continue  # header row
                self.assertIn('href="https://', m.group(1), f"{name}: {m.group(1)[:80]}")
            self.assertNotIn("href='", doc, name)

    def test_no_placeholder_tokens(self):
        for name, fn in B.BODIES.items():
            doc = fn()
            for token in ("TODO", "TBD", "lorem ipsum", "XXX", "{{", "}}"):
                self.assertNotIn(token, doc, f"{name} contains {token!r}")

    def test_build_is_idempotent(self):
        B.build()
        first = {p.name: p.read_text() for p in SITE.glob("*.html")}
        B.build()
        second = {p.name: p.read_text() for p in SITE.glob("*.html")}
        self.assertEqual(first, second)

    def test_v4_pages_carry_the_published_nav(self):
        B.build()
        index = (SITE / "index.html").read_text()
        v2_links = set(re.findall(r'<a href="([a-z0-9\-]+\.html)"', index))
        for name in B.V4_NAMES:
            doc = (SITE / name).read_text()
            links = set(re.findall(r'<a href="([a-z0-9\-]+\.html)"', doc))
            self.assertTrue(v2_links <= links, f"{name} is missing {sorted(v2_links - links)}")

    def test_nav_links_resolve(self):
        B.build()
        for name in B.V4_NAMES:
            doc = (SITE / name).read_text()
            for link in re.findall(r'href="([^"#:]+)"', doc):
                if link.startswith(("http://", "https://", "mailto:")):
                    continue
                self.assertTrue((SITE / link).exists(), f"{name}: broken link {link}")


if __name__ == "__main__":
    unittest.main()
