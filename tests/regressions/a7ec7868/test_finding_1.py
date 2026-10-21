# tests/regressions/a7ec7868/test_finding_1.py
import pytest

from tests.test_ci_checks import _literal_count_hits


@pytest.mark.parametrize("operator", [">", ">=", "<", "<="])
def test_aliased_population_threshold_is_rejected(operator):
    direct = (
        "rows = load(OUTPUT)\n"
        f"assert len(rows) {operator} 9\n"
    )
    aliased = (
        "rows = load(OUTPUT)\n"
        "expected = 9\n"
        "required = expected\n"
        f"assert len(rows) {operator} required\n"
    )

    assert _literal_count_hits("tests/test_probe.py", direct), (
        "The direct threshold must activate the detector"
    )
    assert _literal_count_hits("tests/test_probe.py", aliased), (
        "A handwritten population threshold remains forbidden "
        "when its literal is reached through aliases"
    )
