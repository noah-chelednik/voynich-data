# tests/regressions/3f9c87ec/test_reach_2.py
import pytest

from tests.test_ci_checks import _literal_count_hits


@pytest.mark.parametrize("operator", ["==", ">="])
def test_literal_population_count_reaches_a_named_size(operator):
    prefix = "rows = load(OUTPUT)\n"
    direct = prefix + f"assert len(rows) {operator} 3\n"
    named = prefix + f"size = len(rows)\nassert size {operator} 3\n"

    assert _literal_count_hits("tests/probe.py", direct), direct
    assert _literal_count_hits("tests/probe.py", named), named
