"""Tests for the v4 player-level surface.

The tests are the gates' second half: the gates in :mod:`nba2.v4.gamelog` measure
the capture, and these assert that the measurement itself is wired to the data —
that a moved digit, a dropped row, or a silently blank column fails here.
"""

from __future__ import annotations

import json
import re
import unittest.mock
import zlib
import unittest
from pathlib import Path

from . import official as O
from . import gamelog as GL
from . import injury as IN
from . import minutes as MN
from . import build as B
from . import capture as CAP

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

    def test_no_double_escaped_entities(self):
        # A URL cell that is escaped twice prints as "&amp;amp;" to the reader and, worse,
        # is a link that no longer matches the endpoint it claims to document.
        B.build()
        for name in B.V4_NAMES:
            doc = (SITE / name).read_text()
            for bad in ("&amp;amp;", "&amp;lt;", "&amp;quot;", "&amp;#"):
                self.assertNotIn(bad, doc, f"{name}: double-escaped entity {bad!r}")
            # hrefs keep exactly one level of escaping (& -> &amp;); a second level is the bug.
            for m in re.finditer(r'href="(https?://[^"]+)"', doc):
                self.assertNotIn("&amp;amp;", m.group(1), f"{name}: href {m.group(1)}")

    def test_nav_survives_the_whole_generator_chain(self):
        # v4 copies the navigation out of the published index.html. If a v2 run happens
        # after v3 has written its links, index.html is missing them and v4 would then
        # propagate the incomplete nav to every page. This is the tripwire: after a
        # v2 -> v3 -> v4 chain, every page must still link every v3 and v4 page.
        try:
            from nba2.v3 import build as V3
            v3_names = [n for n, _ in V3.V3_PAGES]
        except Exception:  # noqa: BLE001 - v3 not importable: assert the v4 half only
            v3_names = []
        B.build()
        required = set(v3_names) | set(B.V4_NAMES)
        for page in sorted(SITE.glob("*.html")):
            nav = re.search(r"<nav[^>]*>(.*?)</nav>", page.read_text(), re.S)
            if nav is None:
                continue
            links = set(re.findall(r'href="([^"]+\.html)"', nav.group(1)))
            missing = required - links
            self.assertFalse(missing, f"{page.name}: nav is missing {sorted(missing)}")


if __name__ == "__main__":
    unittest.main()


# --------------------------------------------------------------------------- capture code
# The fixtures below are structural: they reproduce the shape of the official tables
# (column order, /game/<id>/ and /player/<id>/ links) with invented numbers, so the
# parsers can be tested offline. They are NOT official data and nothing in this file
# publishes them.

LOG_FIXTURE = """<html><body>
<div>PPG 20.0 RPG 5.0 APG 4.0</div>
<table class="Crom_table"><thead><tr>
<th>Game Date</th><th>Match Up</th><th>W/L</th><th>MIN</th><th>PTS</th><th>REB</th><th>AST</th><th>+/-</th>
</tr></thead><tbody>
<tr><td>2026-11-11</td><td><a href="https://www.nba.com/game/0022600225/">GSW @ HOU</a></td>
<td>L</td><td>30:30</td><td>20</td><td>5</td><td>4</td><td>-9</td></tr>
<tr><td>2026-11-13</td><td><a href="https://www.nba.com/game/0022600238/">GSW vs. SAS</a></td>
<td>W</td><td>10:30</td><td>20</td><td>5</td><td>4</td><td>3</td></tr>
</tbody></table></body></html>"""

ROSTER_FIXTURE = """<html><body><table><thead><tr><th>Player</th><th>#</th><th>Pos</th></tr></thead>
<tbody>
<tr><td><a href="https://www.nba.com/player/201939/stephen-curry">Curry, Stephen</a></td><td>30</td><td>G</td></tr>
<tr><td><a href="https://www.nba.com/player/1630611/gui-santos">Santos, Gui</a></td><td>15</td><td>F</td></tr>
<tr><td>Head Coach</td><td></td><td></td></tr>
</tbody></table></body></html>"""


def _pdf(*pairs) -> bytes:
    body = " ".join(f"BT ({name}) Tj ({status}) Tj ET" for name, status in pairs)
    return (b"%PDF-1.4\nstream\n" + zlib.compress(body.encode("latin-1")) +
            b"\nendstream\n%%EOF")


class TestCaptureCode(unittest.TestCase):
    """nba2.v4.capture — the parsers the scheduled workflow will run unsupervised."""

    def test_parse_gamelog_reads_rows_and_header(self):
        got = CAP.parse_gamelog(LOG_FIXTURE)
        self.assertEqual(got["rows_declared"], 2)
        self.assertEqual(got["season_header"], {"ppg": 20.0, "rpg": 5.0, "apg": 4.0})
        self.assertEqual([g["game_id"] for g in got["games"]], ["0022600225", "0022600238"])
        self.assertEqual(got["games"][0]["opponent"], "HOU")
        self.assertEqual(got["games"][0]["home_away"], "away")
        self.assertEqual(got["games"][1]["home_away"], "home")
        self.assertEqual(got["games"][0]["minutes_dec"], 30.5)

    def test_parse_gamelog_refuses_an_empty_table(self):
        with self.assertRaises(CAP.CaptureError) as ctx:
            CAP.parse_gamelog("<table><tr><th>Match Up</th></tr></table>No data available")
        self.assertIn("No data available", str(ctx.exception))

    def test_parse_gamelog_refuses_a_row_without_a_game_id(self):
        page = LOG_FIXTURE.replace('<a href="https://www.nba.com/game/0022600238/">GSW vs. SAS</a>',
                                   "GSW vs. SAS")
        with self.assertRaises(CAP.CaptureError) as ctx:
            CAP.parse_gamelog(page)
        self.assertIn("no official game id", str(ctx.exception))

    def test_parse_gamelog_refuses_a_missing_season_header(self):
        with self.assertRaises(CAP.CaptureError) as ctx:
            CAP.parse_gamelog(LOG_FIXTURE.replace("PPG 20.0 ", ""))
        self.assertIn("PPG", str(ctx.exception))

    def test_find_table_reports_a_layout_change(self):
        with self.assertRaises(CAP.CaptureError):
            CAP.find_table("<table><tr><th>Something else</th></tr></table>", ["Match Up"])

    def test_parse_roster_takes_official_ids_only(self):
        got = CAP.parse_roster(ROSTER_FIXTURE)
        self.assertEqual([p["player_id"] for p in got], ["201939", "1630611"])
        self.assertEqual(got[0]["player"], "Curry, Stephen")
        self.assertEqual(got[0]["pos"], "G")

    def test_parse_roster_refuses_a_page_with_no_player_links(self):
        with self.assertRaises(CAP.CaptureError):
            CAP.parse_roster("<table><tr><td>Coach</td></tr></table>")

    def test_capture_player_gates_the_parse_before_returning(self):
        bad = LOG_FIXTURE.replace("<td>20</td>", "<td>21</td>", 1)
        with unittest.mock.patch.object(CAP, "http_get", lambda url: bad.encode()):
            with self.assertRaises(CAP.CaptureError) as ctx:
                CAP.capture_player("Fix, Ture", "GSW", "201939")
        self.assertIn("G-41-02", str(ctx.exception))

    def test_capture_player_accepts_a_consistent_parse(self):
        with unittest.mock.patch.object(CAP, "http_get", lambda url: LOG_FIXTURE.encode()):
            got = CAP.capture_player("Fix, Ture", "GSW", "201939")
        self.assertEqual(got["rows_captured"], 2)
        self.assertEqual(got["rows_declared"], 2)

    def test_pdf_pairs_reads_a_flate_stream(self):
        got = CAP.pdf_pairs(_pdf(("Curry, Stephen", "Out"), ("Santos, Gui", "Questionable")))
        self.assertIn(("Curry, Stephen", "Out"), got)
        self.assertIn(("Santos, Gui", "Questionable"), got)

    def test_pdf_pairs_returns_nothing_for_a_pdf_it_cannot_read(self):
        self.assertEqual(CAP.pdf_pairs(b"%PDF-1.4\nnothing here\n"), set())

    def test_designated_players_come_off_the_committed_release(self):
        # A guard on the join the nightly run depends on: the PDF prints club names,
        # the site and this module work in tricodes.
        got = CAP._designated("2026-11-16", ["GSW"])
        self.assertTrue(got["GSW"], "the join from club name to tricode returned nothing")
        self.assertTrue(all(r["status"] in ("Out", "Doubtful", "Questionable") for r in got["GSW"]))
        self.assertFalse(any(r["reason"].startswith("G League") for r in got["GSW"]))

    def test_slate_clubs_returns_tricodes(self):
        for club in CAP.slate_clubs("2026-11-16"):
            self.assertEqual(club, club.upper())
            self.assertLessEqual(len(club), 3)
