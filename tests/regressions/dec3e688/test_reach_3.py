# tests/regressions/dec3e688/test_reach_3.py
"""Reach dec3e688 gap 3 (claim 4): `_AssertionsAsComparisons` reads an assertion call only when its two operands are
positional (`len(node.args) >= 2`). The same listed calls with an operand passed by keyword, which unittest and
`math.isclose` accept, pass the guard with the very counts of audit 20261021-tests F2."""
from tests import test_ci_checks as checks

SNIPPETS = [
    "rows = load(OUTPUT)\nself.assertEqual(len(rows), second=4072)\n",
    "self.assertGreaterEqual(first=report.total_lines, second=4000)\n",
    "rows = load(OUTPUT)\nassert math.isclose(a=len(rows), b=4072)\n",
]


def test_keyword_assertion_counts_are_caught():
    missed = [s for s in SNIPPETS if not checks._literal_count_hits("tests/probe.py", s)]
    assert not missed, missed
