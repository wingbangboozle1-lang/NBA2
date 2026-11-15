"""Regression tests for tools/crosscheck_gate.sh (F-050).

The defect this pins: the nightly workflow's semantic-crosscheck gate grepped
`^\\[fail\\]` while tools/crosscheck_site.py prints `[FAIL]`, so the gate could
never match a real failure and a red crosscheck could never block a commit. The
gate also swallowed checker crashes (`|| true` with no completion check).

These tests feed the gate synthetic checker logs through `--from-log` and assert
which logs block and which pass — the "prove the gate can fail" evidence asked
for in D9-04. No network, no repository state is read besides the script itself.
"""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / "tools" / "crosscheck_gate.sh"

CLEAN = """\
[ ok ] CC-A-01     a passing check
[info] CC-B-02     an informational check
        observed: something worth reading
97 checks: 96 pass, 0 fail, 1 info, 0 n/a
"""

REAL_FAIL = """\
[ ok ] CC-A-01     a passing check
[FAIL] CC-BAD-99   a genuinely failing check
        observed: the evidence
97 checks: 96 pass, 1 fail, 0 info, 0 n/a
"""

FRESHNESS_ONLY_FAIL = """\
[FAIL] CC-FRESH-01    the snapshot is within one day of the run date
        observed: snapshot 2026-11-13, run date 2026-11-15
97 checks: 96 pass, 1 fail, 0 info, 0 n/a
"""

NO_SUMMARY = """\
[ ok ] CC-A-01     a passing check
Traceback (most recent call last):
  File "tools/crosscheck_site.py", line 1, in <module>
    import missing_module
"""

# The exact line the old `grep '^\[fail\]'` could not match (lowercase pattern,
# uppercase output). Kept verbatim as the regression's subject.
OLD_PATTERN = r"^\[fail\]"


def run_gate(log_text: str) -> subprocess.CompletedProcess:
    with tempfile.NamedTemporaryFile(
        "w", suffix=".txt", delete=False, dir=ROOT / "tools"
    ) as f:
        f.write(log_text)
        path = f.name
    try:
        return subprocess.run(
            ["sh", str(GATE), "--from-log", path],
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=60,
        )
    finally:
        Path(path).unlink(missing_ok=True)


class TestCrosscheckGate(unittest.TestCase):
    def test_clean_log_passes(self):
        r = run_gate(CLEAN)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("gate passed", r.stdout)

    def test_real_failure_blocks(self):
        """A [FAIL] line must block — the whole point of the gate."""
        r = run_gate(REAL_FAIL)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("CR-7", r.stdout)

    def test_old_lower_case_pattern_could_never_match_the_real_output(self):
        """Documents the F-050 defect itself: the old pattern misses [FAIL]."""
        import re

        self.assertIsNone(re.search(OLD_PATTERN, "[FAIL] CC-BAD-99   x"))
        self.assertIsNotNone(re.search(r"^\[FAIL\]", "[FAIL] CC-BAD-99   x"))
        # and the fixed gate does block on that exact line
        self.assertEqual(run_gate(REAL_FAIL).returncode, 1)

    def test_freshness_only_failure_is_excluded_by_design(self):
        r = run_gate(FRESHNESS_ONLY_FAIL)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("CC-FRESH-01", r.stdout)

    def test_checker_crash_without_summary_blocks(self):
        """`|| true` used to swallow a crash; now a missing summary blocks."""
        r = run_gate(NO_SUMMARY)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("summary line", r.stdout)

    def test_info_lines_never_block(self):
        log = (
            "[ ok ] CC-A-01     pass\n"
            "[info] CC-B-02     info\n"
            "[ n/a] CC-C-03     n/a\n"
            "97 checks: 94 pass, 0 fail, 2 info, 1 n/a\n"
        )
        r = run_gate(log)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
