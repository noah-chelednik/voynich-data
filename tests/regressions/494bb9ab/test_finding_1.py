# tests/regressions/494bb9ab/test_finding_1.py
import pytest

from tests.test_ci_checks import _literal_count_hits


@pytest.mark.parametrize(
    ("source", "expected_hit"),
    [
        (
            "rows = []\n"
            "rows = load(ZL)\n"
            "alias = rows\n"
            "def check():\n"
            "    assert len(alias) == 9\n"
            "check()\n",
            True,
        ),
        (
            "def outer():\n"
            "    rows = load(ZL)\n"
            "    def inner():\n"
            "        assert len(rows) == 9\n"
            "    inner()\n"
            "rows = []\n"
            "outer()\n",
            True,
        ),
        (
            "def outer(rows):\n"
            "    def inner():\n"
            "        assert len(rows) == 3\n"
            "    inner()\n"
            "rows = load(ZL)\n"
            "outer([1, 2, 3])\n",
            False,
        ),
    ],
)
def test_enclosing_bindings_preserve_scope_and_assignment_order(
    source, expected_hit
):
    control = "rows = load(ZL)\nassert len(rows) == 9\n"
    assert _literal_count_hits("tests/probe.py", control)
    assert bool(_literal_count_hits("tests/probe.py", source)) == expected_hit
