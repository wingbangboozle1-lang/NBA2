"""Tests for the SG-37 per-club season-table loader (nba2/v2/clubs.py).

The snapshot is injected (never written into data/raw by a test) so the rules are
checkable both when no capture exists and when one does:

* no snapshot  -> coverage 0/30, every published accessor empty, nothing invented;
* a snapshot   -> top-8 by minutes, shares sum to 1, every row keeps its official
                  source URL, and clubs without rows stay absent (never zero-filled);
* refresh gate -> 30 clubs required, out-of-range minutes refused, missing source refused.
"""

from __future__ import annotations

import unittest
from unittest import mock

from nba2.v2 import clubs, refresh as RF


def _row(player: str, tri: str, mpg: float, ppg: float, team_id: int = 1610612743) -> dict:
    return {"player": player, "player_id": str(abs(hash(player)) % 10**7), "team_abbrev": tri,
            "team_id": team_id, "age": 25, "gp": 10, "team_w": 5, "team_l": 5,
            "mpg": mpg, "ppg": ppg,
            "source_url": f"https://www.nba.com/stats/players/traditional?TeamID={team_id}"}


class TestNoSnapshot(unittest.TestCase):
    def setUp(self):
        self.p = mock.patch.object(clubs, "_doc", return_value=None)
        self.p.start()
        self.addCleanup(self.p.stop)

    def test_coverage_is_zero_and_nothing_is_invented(self):
        meta = clubs.snapshot_meta()
        self.assertEqual(meta["coverage_clubs"], 0)
        self.assertIn("never estimated", meta["note"])
        self.assertEqual(clubs.club_rows("ATL"), [])
        self.assertEqual(clubs.top8_blocks(), {})
        self.assertEqual(clubs.top8_shares(), {})


class TestWithSnapshot(unittest.TestCase):
    def setUp(self):
        rows = []
        # 10 players for DEN, minutes strictly decreasing
        for i in range(10):
            rows.append(_row(f"Den Player {i}", "DEN", 36.0 - 3 * i, 20.0 - i))
        # 9 players for BOS
        for i in range(9):
            rows.append(_row(f"Bos Player {i}", "BOS", 30.0 - 2 * i, 18.0))
        doc = {"schema": clubs.SCHEMA, "as_of": "2026-11-15",
               "retrieved_at_utc": "2026-11-15T12:00:00Z",
               "retrieval_method": "test", "source_url": clubs.SOURCE_API, "rows": rows}
        self.p = mock.patch.object(clubs, "_doc", return_value=doc)
        self.p.start()
        self.addCleanup(self.p.stop)

    def test_top8_is_by_minutes_and_stable(self):
        blocks = clubs.top8_blocks()
        self.assertEqual(set(blocks), {"DEN", "BOS"})
        den = blocks["DEN"]
        self.assertEqual(len(den), 8)
        mpgs = [float(r["mpg"]) for r in den]
        self.assertEqual(mpgs, sorted(mpgs, reverse=True))
        self.assertEqual(den[0]["player"], "Den Player 0")

    def test_shares_sum_to_one(self):
        for tri, rows in clubs.top8_shares().items():
            self.assertAlmostEqual(sum(r["min_share"] for r in rows), 1.0, places=3,
                                   msg=f"{tri}: top-8 shares must sum to 1")

    def test_every_row_keeps_its_official_source(self):
        for tri, rows in clubs.top8_blocks().items():
            for r in rows:
                self.assertTrue(r["source_url"].startswith("https://www.nba.com/stats/players/"),
                                f"{tri}/{r['player']}: row lost its official source")

    def test_absent_club_stays_absent(self):
        self.assertEqual(clubs.club_rows("LAL"), [])
        self.assertNotIn("LAL", clubs.coverage())

    def test_meta_reports_snapshot_provenance(self):
        meta = clubs.snapshot_meta()
        self.assertEqual(meta["coverage_clubs"], 2)
        self.assertEqual(meta["as_of"], "2026-11-15")


class TestRefreshGate(unittest.TestCase):
    def _good(self):
        rows = []
        for tri in ("ATL", "BOS", "BKN", "CHA", "CHI", "CLE", "DAL", "DEN", "DET", "GSW",
                    "HOU", "IND", "LAC", "LAL", "MEM", "MIA", "MIL", "MIN", "NOP", "NYK",
                    "OKC", "ORL", "PHI", "PHX", "POR", "SAC", "SAS", "TOR", "UTA", "WAS"):
            for i in range(8):
                rows.append(_row(f"{tri} Player {i}", tri, 30.0 - i, 15.0, team_id=1610612740))
        return {"rows": rows}

    def test_full_capture_passes(self):
        g = RF.gate_players(self._good())
        self.assertTrue(g["ok"], g["detail"])

    def test_missing_club_fails_closed(self):
        d = self._good()
        d["rows"] = [r for r in d["rows"] if r["team_abbrev"] != "UTA"]
        g = RF.gate_players(d)
        self.assertFalse(g["ok"])
        self.assertIn("UTA", g["detail"])

    def test_out_of_range_minutes_fails(self):
        d = self._good()
        d["rows"][0]["mpg"] = 55.0
        self.assertFalse(RF.gate_players(d)["ok"])

    def test_row_without_source_fails(self):
        d = self._good()
        d["rows"][3]["source_url"] = ""
        g = RF.gate_players(d)
        self.assertFalse(g["ok"])
        self.assertIn("without source", g["detail"])


if __name__ == "__main__":
    unittest.main()
