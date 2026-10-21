# tests/regressions/7ea91938/test_reach_3.py
"""Claim 5 (the document states every published value as the registry has it): the comparison is between the document
and a lossy rendering (floats to three decimals), so a registry value the document does not state passes."""
import copy

import pytest

from tests import test_reference_checks as checks


def test_a_registry_value_the_document_does_not_state_is_refused(monkeypatch):
    registry = copy.deepcopy(checks.REGISTRY)
    for r in registry["references"]:
        if r["id"] == "zl-h1":
            r["value"] = 3.8624  # the document says 3.862
    monkeypatch.setattr(checks, "REGISTRY", registry)
    monkeypatch.setattr(checks, "REFERENCES", {r["id"]: r for r in registry["references"]})
    text = (checks.ROOT / "docs" / "reference_checks.md").read_text(encoding="utf-8")
    assert "3.8624" not in text
    with pytest.raises(AssertionError):
        checks.test_the_document_states_the_registry()
