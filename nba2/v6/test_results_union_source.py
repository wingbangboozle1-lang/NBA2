"""Regression: the scheduled rebuild must pass G-V6-8 on the committed union.

WHY THIS FILE EXISTS (measured, 2026-11-19)
-------------------------------------------
The scheduled refresh failed on the *publish* leg ten times in a row. Reproduced from the
committed capture commit `a5380e1`, the failure was:

    python3 -m nba2.v6  ->  HARD GATE FAILURE  G-V6-8
        ! 0022600231: no official URL at all      (and 0022600232-240)

Those rows are not missing a URL. `data/raw/official_finals_union.json` - written by
`nba2.pipeline.settle`, which the refresh runs immediately before the render - carries the
official game page for every one of them under the key `source`. Two defects in the reader
hid it:

  1. `_records_of` merged rows with `if val is not None or ...` nested inside another
     null-check, so the LAST row's explicit null overwrote a non-null from an earlier row in
     the same file;
  2. the URL extractor's `source` fallback required `startswith("https://")` at extraction
     time but ran after (1) had already nulled the value in one path, and did not accept the
     `final_source_url` key the older feeds use.

Both directions are pinned here: the URL must be surfaced when the file carries it, and a row
that genuinely has no official URL must still FAIL the gate. That second test is the reason
the gate is worth anything - a fix that made G-V6-8 pass unconditionally would be worse than
the bug.
"""

from __future__ import annotations

import json
import unittest

from nba2.v6 import results_coverage as RC


class TestOfficialUrlExtraction(unittest.TestCase):
    def test_source_key_is_accepted_when_it_is_an_official_game_page(self):
        row = {"source": "https://www.nba.com/game/den-vs-nop-0022600231"}
        self.assertEqual(RC._official_url(row, "source_url", "source"),
                         "https://www.nba.com/game/den-vs-nop-0022600231")

    def test_final_source_url_key_is_accepted(self):
        row = {"final_source_url": "https://www.nba.com/game/lal-vs-uta-0022600252"}
        self.assertEqual(RC._official_url(row, "source_url", "final_source_url"),
                         "https://www.nba.com/game/lal-vs-uta-0022600252")

    def test_a_prose_label_is_never_promoted_to_a_link(self):
        for bad in ("nba.com/schedule", "derived from the box score", "", None, 17,
                    "https://example.com/game/1"):
            self.assertIsNone(RC._official_url({"source": bad}, "source"), bad)

    def test_a_non_nba_host_is_refused_even_over_https(self):
        self.assertIsNone(RC._official_url({"source": "https://example.org/x"}, "source"))

    def test_null_never_beats_a_value_across_merged_rows(self):
        """The exact shape of the union file: a rich row followed by a sparse null row."""
        doc = {"records": [
            {"game_id": "0022600231", "away_pts": 116, "home_pts": 108,
             "source": "https://www.nba.com/game/den-vs-nop-0022600231"},
            {"game_id": "0022600231", "away_pts": 116, "home_pts": 108,
             "source": None, "source_url": None},
        ]}
        row = RC._records_of(doc)[0]
        self.assertEqual(row["source"], "https://www.nba.com/game/den-vs-nop-0022600231")
        self.assertEqual(RC._official_url(row, "source", "source_url"),
                         "https://www.nba.com/game/den-vs-nop-0022600231")


class TestCommittedUnionCarriesItsUrls(unittest.TestCase):
    def test_every_final_in_the_committed_union_has_an_official_url(self):
        doc = json.loads((RC.DATA / "raw" / "official_finals_union.json").read_text())
        rows = doc.get("records") or []
        self.assertGreater(len(rows), 0, "the union file is empty - the builder did not run")
        missing = [r["game_id"] for r in rows
                   if not RC._official_url(r, "source_url", "source", "official_source",
                                           "final_source_url")]
        self.assertEqual(missing, [],
                         f"{len(missing)} union row(s) carry no explicit official URL: {missing}")

    def test_the_reader_surfaces_those_urls_for_the_render(self):
        finals = RC.finals_committed()
        self.assertGreater(len(finals), 0)
        missing = [gid for gid, r in finals.items() if not r.get("source_url")]
        self.assertEqual(missing, [],
                         f"finals_committed() dropped the URL for {len(missing)} game(s): {missing}")


if __name__ == "__main__":
    unittest.main()
