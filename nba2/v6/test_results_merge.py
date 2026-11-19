"""Regression tests for the finals reader in nba2.v6.results_coverage.

Why these exist (session arena/af5df7a7-nba2, 2026-11-19): the nightly publish job died
on hard gate G-V6-8 — "every game row points at an official nba.com document" — for
games 0022600231–0022600240, even though the official URLs were sitting in committed
capture files. Two reader defects hid them:

  1. the cross-file merge was first-file-wins, so a sparse ``data/raw/finals_2026-11-1x.json``
     row shadowed the URL-carrying ``capture_*/results_*.json`` row for the same game;
  2. the row reader did not know the aliases the committed feeds use (``source``,
     ``final_source_url``, ``away_team``/``home_team``).

The gate itself is untouched — it keeps demanding a real nba.com host. These tests pin
that the reader surfaces the provenance that is actually committed, and that a game with
no committed URL still fails the gate (the fail-closed direction must not move).
"""

from __future__ import annotations

import unittest

from nba2.v6 import check as V6C
from nba2.v6 import results_coverage as RC


class TestFinalsReader(unittest.TestCase):
    def test_committed_url_is_surfaced_not_shadowed_by_a_sparse_row(self):
        """0022600231's first source is the sparse finals_2026-11-14.json row."""
        fin = RC.finals_committed()
        rec = fin["0022600231"]
        self.assertEqual(rec["source_url"],
                         "https://www.nba.com/game/den-vs-nop-0022600231")
        self.assertEqual(rec["gamebook_url"],
                         "https://statsdmz.nba.com/pdfs/20261114/20261114_DENNOP_book.pdf")
        self.assertEqual((rec["away"], rec["home"]), ("DEN", "NOP"))

    def test_alias_keys_are_read_like_pipeline_settle_reads_them(self):
        """finals_2026-11-1x.json rows key the link ``final_source_url``/``source``."""
        fin = RC.finals_committed()
        rec = fin["0022600236"]          # IND @ PHI, 2026-11-15
        self.assertTrue(rec["source_url"].startswith("https://www.nba.com/game/"))
        self.assertEqual((rec["away"], rec["home"]), ("IND", "PHI"))
        self.assertTrue(rec["away_quarters"] and rec["home_quarters"])

    def test_every_committed_game_row_points_at_an_official_document(self):
        doc = RC.build()
        gate = V6C.gate_coverage_sources(doc["games"])
        self.assertTrue(gate["ok"], gate["failures"])

    def test_a_game_without_any_committed_url_still_fails_the_gate(self):
        """The fail-closed direction is pinned: a blank provenance row is a failure."""
        rows = [{"game_id": "0029999999", "matchup": "X @ Y",
                 "source_url": None, "gamebook_url": None}]
        gate = V6C.gate_coverage_sources(rows)
        self.assertFalse(gate["ok"])
        self.assertIn("0029999999: no official URL at all", gate["failures"])

    def test_non_nba_host_is_still_a_failure(self):
        rows = [{"game_id": "0029999998", "matchup": "X @ Y",
                 "source_url": "https://example.com/game", "gamebook_url": None}]
        gate = V6C.gate_coverage_sources(rows)
        self.assertFalse(gate["ok"])

    def test_score_conflict_between_files_is_flagged_not_averaged(self):
        fin = RC.finals_committed()
        for rec in fin.values():
            for c in rec.get("conflicts", []):
                self.assertIn("away_pts", c)
                self.assertIn("home_pts", c)

    def test_matchup_is_never_the_string_none_at_none(self):
        doc = RC.build()
        for g in doc["games"]:
            self.assertIsNotNone(g["matchup"])
            self.assertNotIn("None", g["matchup"])


if __name__ == "__main__":
    unittest.main()
