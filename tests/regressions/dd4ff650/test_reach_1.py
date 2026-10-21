# tests/regressions/dd4ff650/test_reach_1.py
import re

import pytest

from tests import test_stability as checks


@pytest.mark.parametrize("part", ("MAJOR", "MINOR", "PATCH"))
def test_version_part_requires_a_definition(monkeypatch, part):
    checks.test_the_version_parts_are_defined()
    changed = re.sub(
        rf"^\| {part} \|.*$",
        f"| {part} | | |",
        checks.STABILITY,
        flags=re.M,
    )
    assert changed != checks.STABILITY
    monkeypatch.setattr(checks, "STABILITY", changed)

    with pytest.raises(AssertionError):
        checks.test_the_version_parts_are_defined()
