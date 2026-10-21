# tests/regressions/b09d5b4b/test_reach_10.py
from tests.test_ci_checks import _literal_count_hits


def test_count_guard_reaches_zl_source_path():
    assert _literal_count_hits(
        "tests/probe.py",
        "rows = load(ZL)\nassert len(rows) == 9\n",
    )
    source = (
        "def test_count(zl_source_path):\n"
        "    pages = load(zl_source_path)\n"
        "    assert len(pages) == 9\n"
    )
    assert _literal_count_hits("tests/probe.py", source)
