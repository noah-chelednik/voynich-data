# tests/regressions/14df5abd/test_finding_1.py
"""Claim 4 says "an argument names no damage its control does not test", with
`test_each_why_names_the_damages_its_control_tests` as its predicate. That test skips every `why` that does not carry
the marker "Fails on:" (four of the eleven at HEAD: zl-characters, zl-h1, zl-word-tokens, zl-word-types, two of which
argue their teeth from damages in prose). A `why` that claims, in prose, a damage its `control` does not name passes
the predicate as long as it omits the marker: here zl-word-types (control: markup-kept, word-division-lost) is made to
say that a tenth of the loci lost fails it, which is false (7666 types, within 8114 +/- 811.4)."""
import copy

from tests import test_reference_checks as checks

CLAIM = " A tenth of the loci lost moves the count beyond the tolerance (positive control)."


def test_a_why_claiming_a_damage_its_control_does_not_test_is_refused(monkeypatch):
    registry = copy.deepcopy(checks.REGISTRY)
    for r in registry["references"]:
        if r["id"] == "zl-word-types":
            assert "loci-lost" not in r["control"]
            r["why"] = r["why"] + CLAIM
    monkeypatch.setattr(checks, "REGISTRY", registry)
    monkeypatch.setattr(checks, "REFERENCES", {r["id"]: r for r in registry["references"]})
    try:
        checks.test_each_why_names_the_damages_its_control_tests()
    except AssertionError:
        return
    raise AssertionError(
        "zl-word-types' why claims a tenth of the loci lost fails it, a damage its control does not test, "
        "and the clause-4 predicate accepts it because the why carries no 'Fails on:' marker"
    )
