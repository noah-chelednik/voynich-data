# tests/regressions/audit_20261017_docs_r2/test_finding_1.py
import pytest

from tests.test_ci_checks import _literal_count_hits


@pytest.mark.parametrize(
    "source",
    [
        (
            "def outer():\n"
            "    rows = list(IVTFFParser().parse_file(ZL))\n"
            "    def inner():\n"
            "        assert len(rows) == 9\n"
            "    inner()\n"
        ),
        (
            "def get_rows():\n"
            "    return list(IVTFFParser().parse_file(ZL))\n"
            "rows = get_rows()\n"
            "assert len(rows) == 9\n"
        ),
    ],
)
def test_g10_reaches_source_populations_across_function_scopes(source):
    control = (
        "rows = list(IVTFFParser().parse_file(ZL))\n"
        "assert len(rows) == 9\n"
    )
    assert _literal_count_hits("tests/probe.py", control)
    assert _literal_count_hits("tests/probe.py", source)
