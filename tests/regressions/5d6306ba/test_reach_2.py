# tests/regressions/5d6306ba/test_reach_2.py
from tests.test_ci_checks import _literal_count_hits


def test_real_population_literal_is_rejected_through_aliases():
    direct = (
        "rows = load(OUTPUT)\n"
        "assert len(rows) == 9\n"
    )
    aliased = (
        "rows = load(OUTPUT)\n"
        "expected = 9\n"
        "required = expected\n"
        "assert len(rows) == required\n"
    )

    assert _literal_count_hits("tests/test_probe.py", direct)
    assert _literal_count_hits("tests/test_probe.py", aliased), (
        "A handwritten expected population remains forbidden through aliases"
    )
