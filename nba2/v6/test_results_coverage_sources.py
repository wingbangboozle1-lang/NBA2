"""Regression tests for merging provenance across duplicate official game rows.

The same final may be captured in a score-only feed and a richer official gamebook
feed. Metadata is joined only by exact game ID and agreeing score/teams; no URL is inferred.
"""

from __future__ import annotations

import unittest

from nba2.v6.results_coverage import AS_OF_UTC, build, finals_committed


class TestResultProvenanceMerge(unittest.TestCase):
    def test_committed_duplicate_sources_fill_missing_document_urls(self):
        rows = finals_committed()
        missing = [gid for gid, row in rows.items()
                   if not (row.get("source_url") or row.get("gamebook_url"))]
        self.assertEqual(missing, [],
                         "a matching committed official source should provide the document URL")

    def test_coverage_gate_accepts_exact_official_documents(self):
        doc = build()
        for row in doc["games"]:
            urls = [url for url in (row.get("source_url"), row.get("gamebook_url")) if url]
            self.assertTrue(urls, msg=f"{row['game_id']} has no committed document URL")
            self.assertTrue(any("nba.com" in url for url in urls), msg=row["game_id"])

    def test_reported_as_of_matches_the_committed_capture_timestamp(self):
        self.assertEqual(build()["as_of_utc"], AS_OF_UTC)

    def test_urls_are_not_synthesized_for_unknown_game_ids(self):
        rows = finals_committed()
        self.assertNotIn("0000000000", rows)


if __name__ == "__main__":
    unittest.main()
