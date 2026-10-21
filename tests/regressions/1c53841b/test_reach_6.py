# tests/regressions/1c53841b/test_reach_6.py
from pathlib import Path

import pytest

from tests import test_ci_checks as checks


@pytest.mark.parametrize("marker", ["skip", "xfail"])
def test_ci_predicate_rejects_disabled_tests(monkeypatch, marker):
    checks.test_no_literal_counts()
    target = checks.ROOT / "tests" / "test_comparison.py"
    original = Path.read_text

    def read_with_disabled_test(self, *args, **kwargs):
        text = original(self, *args, **kwargs)
        if self == target:
            text += (
                "\nimport pytest\n"
                f"@pytest.mark.{marker}(reason='reach probe')\n"
                "def test_reach_disabled_probe():\n"
                "    assert True\n"
            )
        return text

    monkeypatch.setattr(Path, "read_text", read_with_disabled_test)
    with pytest.raises(AssertionError):
        checks.test_no_literal_counts()
