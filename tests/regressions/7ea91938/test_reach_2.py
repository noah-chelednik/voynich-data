# tests/regressions/7ea91938/test_reach_2.py
"""Claim 3 (each value has a quote holding the value as the page writes it): the check accepts any spelling that is a
substring of the quote, so a value more precise than the page (3.8624 for the page's 3.862) passes, and so does a value
that is only a fragment of a number in the quote (862 for 188,862)."""
import copy

import pytest

from tests import test_reference_checks as checks


def _registry_with(reference_id, value):
    registry = copy.deepcopy(checks.REGISTRY)
    for r in registry["references"]:
        if r["id"] == reference_id:
            r["value"] = value
    return registry


@pytest.mark.parametrize(("reference_id", "value"), [("zl-h1", 3.8624), ("zl-characters", 862)])
def test_a_value_the_quote_does_not_hold_is_refused(monkeypatch, reference_id, value):
    registry = _registry_with(reference_id, value)
    monkeypatch.setattr(checks, "REGISTRY", registry)
    monkeypatch.setattr(checks, "REFERENCES", {r["id"]: r for r in registry["references"]})
    quote = checks.REFERENCES[reference_id]["quote"]
    assert str(value) not in quote.split()  # the page does not write this value
    with pytest.raises(AssertionError):
        checks.test_the_registry_is_well_formed()
