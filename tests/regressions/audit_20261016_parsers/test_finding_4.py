# tests/regressions/audit_20261016_parsers/test_finding_4.py
import pytest

from parsers import PageVariables


@pytest.mark.parametrize("value", ["X", "Z"])
def test_letter_currier_hand_codes_survive(value):
    variables = PageVariables.from_header(f"<! $C={value}>")
    assert variables.cluster == value
