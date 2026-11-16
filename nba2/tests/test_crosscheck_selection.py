"""Regression tests for slate-snapshot selection in tools/crosscheck_site.py.

The defect this pins (found when the F-050 crosscheck gate first ran in CI,
session arena/d09f8d1e-nba2): the checker took `snapshot_candidates("slate")[0]`
as "the newest slate", but the committed candidates TIE on their internal stamp
(`slate_2026-11-14_to_11-17.json` and `slate_2026-11-14_to_11-17_v2.json` both
read `as_of 2026-11-14`), so `[0]` fell through to filesystem glob order. On the
Actions runner that returned the dict-shaped 27-row `_v2` file and the checker
died with `KeyError: 4` at CC-SNAP-02 (`x[idx["game_id"]]` on a dict row).
Locally the glob order happened to put the list-shaped 36-row file first, which
is why every local run had been green.

`slate_snapshot(site)` anchors selection to the published artefact (record count
+ shape) instead of a timestamp or a filesystem, normalises dict rows through the
declared column order, and returns None when nothing matches.
"""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load_crosscheck():
    spec = importlib.util.spec_from_file_location(
        "nba2_crosscheck_site", ROOT / "tools" / "crosscheck_site.py"
    )
    mod = importlib.util.module_from_spec(spec)
    # Register before exec: the module uses @dataclass, and dataclasses resolves
    # annotations through sys.modules[cls.__module__] (None → AttributeError).
    import sys
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


CC = _load_crosscheck()


def _site_with_slate_rows(n: int) -> dict:
    return {"sections": {"slate": {"rows": [{} for _ in range(n)]}}}


class TestCommittedArtifacts(unittest.TestCase):
    def test_selection_matches_the_published_slate_table(self):
        site = json.loads((ROOT / "data" / "site.json").read_text())
        sel = CC.slate_snapshot(site)
        self.assertIsNotNone(sel, "a published slate table must have a matching snapshot")
        path, doc = sel
        self.assertEqual(path.name, "slate_2026-11-14_to_11-17.json",
                         "the published 36-row table comes from the 36-row capture, "
                         "not the 27-row v2 pick-window file")
        self.assertEqual(len(doc["records"]), len(site["sections"]["slate"]["rows"]))
        self.assertTrue(all(isinstance(x, list) for x in doc["records"]),
                        "selection must return list-shaped rows for positional indexing")
        self.assertIn("game_id", doc["columns"])

    def test_the_naive_first_candidate_is_the_wrong_file(self):
        """Documents why `[0]` cannot be trusted: with a defined tie-break the
        FIRST candidate among the tied-stamp 11/14 pair is the dict-shaped v2
        file — the one that crashed CI. (The integration brought newer slate
        snapshots, so the pair is selected by stamp rather than assumed at [0].)"""
        cands = CC.snapshot_candidates("slate")
        self.assertGreaterEqual(len(cands), 2)
        tied_11_14 = [p for p in cands if "2026-11-14" in p.name]
        self.assertGreaterEqual(len(tied_11_14), 2, "the tied 11/14 pair must still exist")
        self.assertTrue(tied_11_14[0].name.endswith("_v2.json"),
                        f"expected the v2 file first under the name tie-break, got {tied_11_14[0].name}")
        site = json.loads((ROOT / "data" / "site.json").read_text())
        sel = CC.slate_snapshot(site)
        self.assertIsNotNone(sel)
        self.assertNotIn(sel[0], tied_11_14[:1], "selection must not just take [0] of the tied pair")


class TestSelectionRules(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.raw = Path(self._tmp.name)
        self._old_raw = CC.RAW
        CC.RAW = self.raw

    def tearDown(self):
        CC.RAW = self._old_raw
        self._tmp.cleanup()

    def _write(self, name: str, doc: dict) -> None:
        (self.raw / name).write_text(json.dumps(doc))

    def test_count_match_beats_glob_order_and_dict_shape(self):
        cols = ["game_id", "date"]
        # wrong-shaped candidate with the TIED stamp, named so the tie-break
        # puts it first (reverse name order) — the CI crash configuration
        self._write("slate_2026-11-14_to_11-17_v2.json", {
            "as_of": "2026-11-14", "columns": cols,
            "records": [{"game_id": "0022600001", "date": "2026-11-14"}],
        })
        self._write("slate_2026-11-14_to_11-17.json", {
            "as_of": "2026-11-14", "columns": cols,
            "records": [["0022600001", "2026-11-14"], ["0022600002", "2026-11-15"],
                        ["0022600003", "2026-11-16"]],
        })
        site = _site_with_slate_rows(3)
        sel = CC.slate_snapshot(site)
        self.assertIsNotNone(sel)
        self.assertEqual(sel[0].name, "slate_2026-11-14_to_11-17.json")
        self.assertTrue(all(isinstance(x, list) for x in sel[1]["records"]))

    def test_matching_candidate_with_dict_rows_is_normalised_to_lists(self):
        cols = ["game_id", "date"]
        self._write("slate_2026-11-15_to_11-18.json", {
            "as_of": "2026-11-15", "columns": cols,
            "records": [{"game_id": "0022600001", "date": "2026-11-15"},
                        {"game_id": "0022600002", "date": "2026-11-16"}],
        })
        sel = CC.slate_snapshot(_site_with_slate_rows(2))
        self.assertIsNotNone(sel)
        recs = sel[1]["records"]
        self.assertTrue(all(isinstance(x, list) for x in recs))
        self.assertEqual(recs[0], ["0022600001", "2026-11-15"])

    def test_no_matching_candidate_returns_none_not_a_guess(self):
        cols = ["game_id", "date"]
        self._write("slate_2026-11-14_to_11-17.json", {
            "as_of": "2026-11-14", "columns": cols,
            "records": [["0022600001", "2026-11-14"]],
        })
        self.assertIsNone(CC.slate_snapshot(_site_with_slate_rows(7)),
                          "an unmatched published table must be reported, never guessed")

    def test_candidate_order_is_deterministic_on_tied_stamps(self):
        cols = ["game_id"]
        for name in ("slate_2026-11-14_to_11-17.json", "slate_2026-11-14_to_11-17_v2.json"):
            self._write(name, {"as_of": "2026-11-14", "columns": cols, "records": []})
        a = [p.name for p in CC.snapshot_candidates("slate")]
        b = [p.name for p in CC.snapshot_candidates("slate")]
        self.assertEqual(a, b, "candidate order must not depend on the filesystem")
        self.assertEqual(a, sorted(a, reverse=True), "ties break by name, descending")


if __name__ == "__main__":
    unittest.main()
