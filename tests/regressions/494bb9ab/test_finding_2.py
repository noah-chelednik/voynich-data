# tests/regressions/494bb9ab/test_finding_2.py
from tests.test_ci_checks import _literal_count_hits


def test_function_provenance_respects_parameter_shadowing():
    control = (
        "def get_rows():\n"
        "    return load(ZL)\n"
        "assert len(get_rows()) == 9\n"
    )
    assert _literal_count_hits("tests/probe.py", control)

    source = (
        "def get_rows():\n"
        "    return load(ZL)\n"
        "def check(get_rows):\n"
        "    assert len(get_rows()) == 3\n"
        "check(lambda: [1, 2, 3])\n"
    )
    assert not _literal_count_hits("tests/probe.py", source)
