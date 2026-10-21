# tests/regressions/cf1c8c6e/test_reach_8.py
import pytest

from tests.test_ci_checks import _literal_count_hits


@pytest.mark.parametrize(
    "expectation",
    [
        "assert len(rows) == 9\n",
        "expected_count = 9\nassert len(rows) == expected_count\n",
    ],
)
def test_literal_counts_of_source_populations_are_detected(expectation):
    source = "rows = list(IVTFFParser().parse_file(ZL))\n" + expectation
    assert _literal_count_hits("tests/probe.py", source), (
        "The unqualified no-literal-count claim misses this source population count:\n"
        + source
    )
