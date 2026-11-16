"""Settlement reads the union of official finals and refuses unverified or conflicting scores.

Each failure path is exercised, because a rule that cannot fail is decoration.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from nba2 import config
from nba2.models import ledger as LD
from nba2.pipeline import settle as ST

OFFICIAL = "https://www.nba.com/game/den-vs-nop-0022600231"


def _rec(gid="0022600231", away=116, home=108, **kw):
    r = {"game_id": gid, "date": "2026-11-14", "away": "DEN", "home": "NOP",
         "away_pts": away, "home_pts": home, "source": OFFICIAL}
    r.update(kw)
    return r


def _write(dirp: Path, name: str, records: list[dict], key: str = "records") -> Path:
    p = dirp / name
    p.write_text(json.dumps({key: records}))
    return p


def _ledger(dirp: Path, game_ids: list[str]) -> Path:
    preds = [{"game_id": g, "date": "2026-11-14", "away": "DEN", "home": "NOP",
              "our_spread_home": 6.0, "our_total": 234.5, "p_home_win": 0.3,
              "margin_model": -6.0, "total_model": 234.5} for g in game_ids]
    p = dirp / "sealed-test.json"
    LD.seal(preds, p, note="test ledger")
    return p


class TestLoadOfficialFinals(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.d = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_union_reads_every_snapshot_not_just_one(self):
        a = _write(self.d, "finals_a.json", [_rec("1")])
        b = _write(self.d, "results_b.json", [_rec("2", 100, 99)])
        recs, rep = ST.load_official_finals([a, b])
        self.assertEqual([r["game_id"] for r in recs], ["1", "2"])
        self.assertEqual(rep["records"], 2)
        self.assertEqual(rep["rejected"], [])

    def test_games_key_shape_is_accepted(self):
        # finals_<date>.json snapshots use "games" and "source_url" instead of "records"/"source"
        g = {"game_id": "9", "away_pts": 1, "home_pts": 2, "source_url": OFFICIAL}
        p = _write(self.d, "finals_g.json", [g], key="games")
        recs, _ = ST.load_official_finals([p])
        self.assertEqual(recs[0]["source"], OFFICIAL)
        self.assertFalse(recs[0]["quarters_verified"])

    def test_conflicting_scores_refuse_settlement(self):
        a = _write(self.d, "finals_a.json", [_rec("1", 116, 108)])
        b = _write(self.d, "results_b.json", [_rec("1", 116, 109)])
        with self.assertRaises(ST.FinalsConflict):
            ST.load_official_finals([a, b])

    def test_identical_scores_from_two_sources_are_not_a_conflict(self):
        a = _write(self.d, "finals_a.json", [_rec("1")])
        b = _write(self.d, "results_b.json", [_rec("1")])
        recs, _ = ST.load_official_finals([a, b])
        self.assertEqual(len(recs), 1)

    def test_quarters_that_do_not_sum_are_rejected_not_corrected(self):
        bad = _rec("1", 116, 108, away_quarters=[29, 27, 30, 29], home_quarters=[23, 28, 31, 26])
        p = _write(self.d, "results_bad.json", [bad])
        recs, rep = ST.load_official_finals([p])
        self.assertEqual(recs, [])
        self.assertIn("do not sum", rep["rejected"][0]["reason"])

    def test_quarters_that_sum_are_verified(self):
        ok = _rec("1", 116, 108, away_quarters=[29, 27, 30, 30], home_quarters=[23, 28, 31, 26])
        recs, _ = ST.load_official_finals([_write(self.d, "results_ok.json", [ok])])
        self.assertTrue(recs[0]["quarters_verified"])

    def test_non_official_source_is_rejected(self):
        r = _rec("1", source="https://example.com/game/1")
        recs, rep = ST.load_official_finals([_write(self.d, "finals_x.json", [r])])
        self.assertEqual(recs, [])
        self.assertIn("official", rep["rejected"][0]["reason"])

    def test_non_final_status_is_rejected(self):
        r = _rec("1", status="in progress")
        recs, rep = ST.load_official_finals([_write(self.d, "finals_x.json", [r])])
        self.assertEqual(recs, [])
        self.assertIn("not final", rep["rejected"][0]["reason"])

    def test_non_integer_score_is_rejected(self):
        r = _rec("1", away=None)
        recs, rep = ST.load_official_finals([_write(self.d, "finals_x.json", [r])])
        self.assertEqual(recs, [])
        self.assertIn("two integers", rep["rejected"][0]["reason"])

    def test_bool_is_not_an_integer_score(self):
        r = _rec("1", home=True)
        recs, _ = ST.load_official_finals([_write(self.d, "finals_x.json", [r])])
        self.assertEqual(recs, [])


class TestSettleRecords(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.d = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_scores_only_games_with_a_verified_final_and_lists_the_rest(self):
        led = _ledger(self.d, ["1", "2"])
        recs, _ = ST.load_official_finals([_write(self.d, "finals_a.json", [_rec("1")])])
        s = LD.settle_records(led, recs)
        self.assertEqual(s.games_settled, 1)
        self.assertEqual(s.games_expected, 2)
        self.assertTrue(s.status.startswith("PARTIAL"))
        self.assertEqual(s.per_game[0]["source"], OFFICIAL)

    def test_no_verified_finals_is_pending_not_zero_scored(self):
        led = _ledger(self.d, ["1"])
        s = LD.settle_records(led, [])
        self.assertEqual(s.games_settled, 0)
        self.assertTrue(s.status.startswith("PENDING"))


class TestCommittedCaptures(unittest.TestCase):
    """Regression on the repository's own captures: the 2026-11-14 finals must be read."""

    def test_the_five_official_1114_finals_are_in_the_union(self):
        recs, rep = ST.load_official_finals()
        ids = {r["game_id"] for r in recs}
        for gid in ["0022600231", "0022600232", "0022600233", "0022600234", "0022600235"]:
            self.assertIn(gid, ids)
        self.assertEqual(rep["rejected"], [])
        q = {r["game_id"]: r for r in recs}["0022600231"]
        self.assertTrue(q["quarters_verified"])
        self.assertEqual((q["away_pts"], q["home_pts"]), (116, 108))

    def test_both_sealed_ledgers_still_verify(self):
        for p in ST.find_ledgers():
            ok, _, _ = LD.verify(p)
            self.assertTrue(ok, p.name)


if __name__ == "__main__":
    unittest.main()
