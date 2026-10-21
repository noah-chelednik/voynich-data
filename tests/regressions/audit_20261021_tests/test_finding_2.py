# tests/regressions/audit_20261021_tests/test_finding_2.py
"""AT 20261021 F2: the no-literal-count guard (G10, `test_no_literal_counts`) sees only `ast.Compare`, so the same
hard-coded count written as a unittest assertion or a `math.isclose` call passes it. The suite already holds a
`unittest.TestCase` (tests/test_runtime_no_skip.py), and pytest collects TestCase classes in every test tree."""

from tests import test_ci_checks as checks

SNIPPETS = [
    "import unittest\nclass T(unittest.TestCase):\n    def test_a(self):\n        self.assertEqual(len(rows), 4072)\n",
    "self.assertGreaterEqual(report.total_lines, 4000)\n",
    "import math\nassert math.isclose(len(rows), 4072)\n",
]


def test_unittest_and_isclose_counts_are_caught():
    missed = [s for s in SNIPPETS if not checks._literal_count_hits("tests/probe.py", s)]
    assert not missed, missed
