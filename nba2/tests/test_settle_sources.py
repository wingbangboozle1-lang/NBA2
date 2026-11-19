"""Regression tests for the settlement source-discovery repair (session arena/fb1d73b2-nba2).

Why these tests exist. ``nba2/pipeline/settle.py`` used to discover official finals in
``data/raw/finals_*.json``, ``data/raw/capture_*/results_*.json``,
``data/raw/results/results_*.json`` and ``data/v2/results.json`` — but NOT the
``data/raw/capture_<date>/finals_<date>.json`` feed that ``nba2.v2.refresh --write`` writes on
every nightly run (schema ``nba2.results-feed.v2``). The union therefore froze at 31 games
while 50 rows of later official finals sat in the same tree, unread. Because
``nba2/settlement_page.py`` refuses to build when the committed union is not a fresh rebuild,
the nightly ``publish`` job failed at the rebuild step for three consecutive runs — a stale
*discovery* rule, not a stale fetch, was what kept the site from refreshing.

The same class of bug is guarded here three ways:

1. the capture-directory finals feed is discovered (and only that pattern — a stray
   ``capture_*/other.json`` must not become a finals source);
2. the two committed spellings of a period row (``*_quarters`` and ``*_q``) are both read, and
   a period row that does not reproduce the printed final still rejects its source;
3. the committed union on ``main`` equals a fresh rebuild — the exact invariant
   ``nba2.settlement_page`` enforces, so this repo cannot be merged into a state where the
   nightly rebuild step fails again.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from nba2.pipeline import settle as S


def _write(path: Path, doc: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc))
    return path


class SourceDiscovery(unittest.TestCase):
    def test_capture_directory_finals_feed_is_a_source(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            raw = root / "data" / "raw"
            rec = {"game_id": "0022600001", "date": "2026-11-19", "away": "BOS", "home": "NYK",
                   "away_pts": 100, "home_pts": 105, "away_q": [20, 30, 25, 25],
                   "home_q": [30, 25, 25, 25], "ot_periods": 0,
                   "source_url": "https://www.nba.com/game/bos-vs-nyk-0022600001"}
            _write(raw / "capture_2026-11-20" / "finals_2026-11-20.json",
                   {"schema": "nba2.results-feed.v2", "records": [rec]})
            # a neighbouring capture file must NOT be mistaken for a finals source
            _write(raw / "capture_2026-11-20" / "slate_2026-11-20.json",
                   {"schema": "nba2.slate.v2", "records": [rec]})
            old_raw, old_v2 = S.RAW, S.ROOT
            try:
                S.RAW, S.ROOT = raw, root
                found = [S._label(p) for p in S.finals_sources()]
            finally:
                S.RAW, S.ROOT = old_raw, old_v2
            self.assertIn("data/raw/capture_2026-11-20/finals_2026-11-20.json", found)
            self.assertNotIn("data/raw/capture_2026-11-20/slate_2026-11-20.json", found)

    def test_repo_actually_discovers_the_nightly_feed(self) -> None:
        """The real tree contains capture_*/finals_*.json; discovery must see every one of them."""
        on_disk = sorted(str(p.relative_to(S.ROOT))
                         for p in (S.RAW).glob("capture_*/finals_*.json"))
        found = sorted(S._label(p) for p in S.finals_sources())
        self.assertTrue(on_disk, "expected at least one nightly finals capture in the tree")
        for p in on_disk:
            self.assertIn(p, found)


class PeriodRowSchemas(unittest.TestCase):
    def _norm(self, rec: dict) -> tuple[list, list]:
        with tempfile.TemporaryDirectory() as td:
            path = _write(Path(td) / "finals_x.json", {"records": [rec]})
            return S.normalise_source(path)

    def test_q_alias_is_read_and_summed(self) -> None:
        cands, rej = self._norm({"game_id": "g1", "away_pts": 100, "home_pts": 105,
                                 "away_q": [20, 30, 25, 25], "home_q": [30, 25, 25, 25],
                                 "source_url": "https://www.nba.com/game/x"})
        self.assertEqual(len(cands), 1)
        self.assertEqual(rej, [])
        self.assertEqual(cands[0]["away_quarters"], [20, 30, 25, 25])
        self.assertEqual(cands[0]["home_quarters"], [30, 25, 25, 25])
        self.assertEqual(cands[0]["date"], None)

    def test_quarters_spelling_still_works(self) -> None:
        cands, rej = self._norm({"game_id": "g2", "away_pts": 100, "home_pts": 105,
                                 "away_quarters": [20, 30, 25, 25],
                                 "home_quarters": [30, 25, 25, 25]})
        self.assertEqual(len(cands), 1)
        self.assertEqual(rej, [])
        self.assertEqual(cands[0]["away_quarters"], [20, 30, 25, 25])

    def test_a_period_row_that_does_not_sum_rejects_the_source(self) -> None:
        """Fail-closed: a bad quarter row is refused, never silently dropped-but-trusted."""
        cands, rej = self._norm({"game_id": "g3", "away_pts": 100, "home_pts": 105,
                                 "away_q": [20, 30, 25, 10], "home_q": [30, 25, 25, 25]})
        self.assertEqual(cands, [])
        self.assertEqual(len(rej), 1)
        self.assertEqual(rej[0]["game_id"], "g3")
        self.assertIn("does not sum", rej[0]["reason"])

    def test_date_is_carried_through_the_union(self) -> None:
        """The results feed is 'one row per game: date, teams, final score, quarter scores'."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            a = _write(root / "a.json", {"records": [
                {"game_id": "g4", "date": "2026-11-19", "away_pts": 100, "home_pts": 105,
                 "away": "BOS", "home": "NYK", "source": "https://www.nba.com/game/1"}]})
            b = _write(root / "b.json", {"records": [
                {"game_id": "g4", "away_pts": 100, "home_pts": 105, "away": "BOS", "home": "NYK",
                 "away_q": [20, 30, 25, 25], "home_q": [30, 25, 25, 25],
                 "source_url": "https://www.nba.com/game/1"}]})
            doc = S.build_union([a, b])
            self.assertEqual(doc["conflicts"], [])
            self.assertEqual(len(doc["records"]), 1)
            r = doc["records"][0]
            self.assertEqual(r["date"], "2026-11-19")
            self.assertEqual(r["away_quarters"], [20, 30, 25, 25])

    def test_conflicting_scores_are_excluded_not_averaged(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            a = _write(root / "a.json", {"records": [
                {"game_id": "g5", "away_pts": 100, "home_pts": 105, "source": "https://x/1"}]})
            b = _write(root / "b.json", {"records": [
                {"game_id": "g5", "away_pts": 110, "home_pts": 105, "source": "https://x/2"}]})
            doc = S.build_union([a, b])
            self.assertEqual(doc["records"], [])
            self.assertEqual(len(doc["conflicts"]), 1)
            self.assertEqual(doc["conflicts"][0]["game_id"], "g5")


class PublishedUnionIsCurrent(unittest.TestCase):
    def test_union_on_disk_is_a_fresh_rebuild(self) -> None:
        """nba2.settlement_page refuses to build on a stale union — the nightly publish failed on
        exactly this. Keep the committed artefact and the pure function in lockstep."""
        disk = json.loads(S.UNION_PATH.read_text())
        fresh = S.build_union()
        self.assertEqual(disk.get("records"), fresh["records"])
        self.assertEqual(disk.get("conflicts"), fresh["conflicts"])
        self.assertEqual(disk.get("sources_read"), fresh["sources_read"])

    def test_union_covers_the_whole_played_window(self) -> None:
        """Every date the nightly finals capture printed must be represented in the union."""
        disk = json.loads(S.UNION_PATH.read_text())
        have = {r["date"] for r in disk["records"] if r.get("date")}
        for p in sorted((S.RAW / "capture_2026-11-18").glob("finals_*.json")):
            want = {r["date"] for r in json.loads(p.read_text())["records"] if r.get("date")}
            self.assertTrue(want, "capture file should carry dates")
            self.assertTrue(want <= have, f"dates in {p.name} missing from the union: {want - have}")

    def test_seals_verify_before_grading(self) -> None:
        from nba2.models import ledger as LD
        for p in S.find_ledgers():
            ok, stored, recomp = LD.verify(p)
            self.assertTrue(ok, f"{p.name}: seal digest {stored} != recomputed {recomp}")


if __name__ == "__main__":
    unittest.main()
