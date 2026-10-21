# tests/regressions/7ccc8927/test_finding_1.py
import pytest

from tests.test_ci_checks import _literal_count_hits


@pytest.mark.parametrize(
    ("source", "expected_hit"),
    [
        (
            "rows: list = list(IVTFFParser().parse_file(ZL))\n"
            "assert len(rows) == 9\n",
            True,
        ),
        (
            "rows = list(IVTFFParser().parse_file(ZL)); "
            "assert len(rows) == 9\n",
            True,
        ),
        (
            "rows = list(IVTFFParser().parse_file(ZL))\n"
            "expected_count: int = 9\n"
            "assert len(rows) == expected_count\n",
            True,
        ),
        (
            "rows = list(IVTFFParser().parse_file(ZL))\n"
            "rows = [1, 2, 3]\n"
            "assert len(rows) == 3\n",
            False,
        ),
    ],
)
def test_population_count_tracking_respects_assignments(source, expected_hit):
    control = (
        "rows = list(IVTFFParser().parse_file(ZL))\n"
        "assert len(rows) == 9\n"
    )
    assert _literal_count_hits("tests/probe.py", control)
    hits = _literal_count_hits("tests/probe.py", source)
    assert bool(hits) == expected_hit, (source, hits)
