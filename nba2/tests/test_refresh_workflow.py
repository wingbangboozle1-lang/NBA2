"""Workflow wiring regressions for the official-final settlement build order.

These tests inspect only committed workflow text; they do not contact the NBA or GitHub.
The settle command is intentionally explicit in all rebuild paths so a stale official-finals
union fails closed before the settlement page or a generated site can be published.
"""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"


class TestRefreshWorkflowSettlementOrder(unittest.TestCase):
    @staticmethod
    def read(name: str) -> str:
        return (WORKFLOWS / name).read_text(encoding="utf-8")

    @staticmethod
    def position(text: str, needle: str) -> int:
        pos = text.find(needle)
        if pos < 0:
            raise AssertionError(f"workflow command not found: {needle}")
        return pos

    def test_nightly_settlement_runs_only_after_successful_finals_capture(self):
        workflow = self.read("refresh.yml")
        start = self.position(workflow, "      - name: Rebuild every tree from the committed capture")
        end = self.position(workflow, "      - name: Gate — provenance and freshness on every published tree")
        rebuild = workflow[start:end]

        self.assertIn("CAPTURE_FINALS: ${{ needs.capture.outputs.finals }}", rebuild)
        self.assertIn('if [ "${CAPTURE_FINALS:-}" = "success" ]; then', rebuild)
        self.assertIn("Official finals unavailable; preserve the committed settlement inputs.", rebuild)
        self.assertEqual(rebuild.count("python3 -m nba2.pipeline.settle"), 1)
        settle = self.position(rebuild, "python3 -m nba2.pipeline.settle")
        self.assertLess(settle, self.position(rebuild, "python3 -m nba2.pipeline.build_site_data"))
        self.assertLess(settle, self.position(rebuild, "python3 -m nba2.settlement_page"))

    def test_nightly_rebuild_commits_only_derived_settlement_outputs(self):
        workflow = self.read("refresh.yml")
        start = self.position(workflow, "      - name: Commit the rebuild")
        end = self.position(workflow, "      - name: Fail visibly if official settlement inputs were unavailable")
        commit = workflow[start:end]
        self.assertIn("data/settlement.json", commit)
        self.assertIn("data/raw/official_finals_union.json", commit)
        self.assertNotIn("data/raw/ledger", commit)
        self.assertNotIn("data/v3/ledger", commit)

    def test_pages_rebuilds_union_before_any_published_tree(self):
        workflow = self.read("pages.yml")
        settle = self.position(workflow, "python -m nba2.pipeline.settle")
        self.assertLess(settle, self.position(workflow, "python -m nba2.v2"))
        self.assertLess(settle, self.position(workflow, "python -m nba2.settlement_page"))

    def test_parity_rebuilds_union_before_data_and_settlement_pages(self):
        workflow = self.read("publish-parity.yml")
        settle = self.position(workflow, "python -m nba2.pipeline.settle")
        self.assertLess(settle, self.position(workflow, "python -m nba2.pipeline.build_site_data"))
        self.assertLess(settle, self.position(workflow, "python -m nba2.settlement_page"))


if __name__ == "__main__":
    unittest.main()
