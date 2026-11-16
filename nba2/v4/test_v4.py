"""Tests for the v4 player-level surface.

The tests are the gates' second half: the gates in :mod:`nba2.v4.gamelog` measure
the capture, and these assert that the measurement itself is wired to the data —
that a moved digit, a dropped row, or a silently blank column fails here.
"""

from __future__ import annotations

import json
import re
import tempfile
import unittest.mock
import zlib
import unittest
from pathlib import Path

from . import official as O
from . import gamelog as GL
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
        names = {r["player"] for r in O.injury_rows()}
        for p in GL.players():
            self.assertIn(p["player"], names, p["player"])

    def test_capture_failures_publish_no_rows(self):
        for f in O.gamelogs()["capture_failures"]:
            self.assertNotIn(f["player"], [p["player"] for p in GL.players()])





# --------------------------------------------------------------------------- fixtures
# The fixtures below are structural: they reproduce the shape of the official tables
# (column order, /game/<id>/ and /player/<id>/ links) with invented numbers, so the
# parsers can be tested offline. They are NOT official data and nothing publishes them.

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
        got = O.designated_players("2026-11-16", ["GSW"])
        self.assertTrue(got["GSW"], "the join from club name to tricode returned nothing")
        self.assertTrue(all(r["status"] in ("Out", "Doubtful", "Questionable") for r in got["GSW"]))
        self.assertFalse(any(r["reason"].startswith("G League") for r in got["GSW"]))

    def test_slate_clubs_returns_tricodes(self):
        for club in O.slate_clubs("2026-11-16"):
            self.assertEqual(club, club.upper())
            self.assertLessEqual(len(club), 3)
