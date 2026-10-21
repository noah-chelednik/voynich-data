# tests/regressions/d8d7a6b0/test_reach_1.py
import pytest

from tests.test_ci_checks import _literal_count_hits


@pytest.mark.parametrize(
    "source",
    [
        (
            "def check():\n"
            "    assert len(rows) == 9\n"
            "rows = load(ZL)\n"
            "check()\n"
        ),
        (
            "def outer():\n"
            "    def inner():\n"
            "        assert len(rows) == 9\n"
            "    rows = load(ZL)\n"
            "    inner()\n"
            "outer()\n"
        ),
        (
            "def get_rows():\n"
            "    return rows\n"
            "rows = load(ZL)\n"
            "assert len(get_rows()) == 9\n"
        ),
    ],
)
def test_deferred_reads_follow_their_enclosing_assignments(source):
    control = "rows = load(ZL)\nassert len(rows) == 9\n"
    assert _literal_count_hits("tests/probe.py", control)
    assert _literal_count_hits("tests/probe.py", source), source
