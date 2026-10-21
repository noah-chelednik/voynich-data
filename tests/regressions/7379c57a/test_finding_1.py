# tests/regressions/7379c57a/test_finding_1.py
"""Claim 4 (round 3 fix) says every argument "ends with exactly the damages its control tests and claims none
elsewhere". Its predicate, `test_each_why_names_the_damages_its_control_tests`, finds a claimed damage in the prose
before "Fails on:" only by the keywords lost/kept/left in/control/fails/fused and their forms. One of the five damage
names the suite itself defines (DAMAGE_NAMES), "paragraph text only", holds none of them, so the prose can claim that
damage freely: here fg-characters (control: loci-lost only) is made to say that paragraph text only fails it."""
import copy

from tests import test_reference_checks as checks

CLAIM = " Paragraph text only moves the count beyond the tolerance."


def test_a_why_claiming_paragraph_text_only_outside_its_control_is_refused(monkeypatch):
    assert "paragraph text only" in checks.DAMAGE_NAMES
    registry = copy.deepcopy(checks.REGISTRY)
    for r in registry["references"]:
        if r["id"] == "fg-characters":
            assert "paragraphs-only" not in r["control"]
            argument, listed = r["why"].split("Fails on:")
            r["why"] = argument.rstrip() + CLAIM + " Fails on:" + listed
    monkeypatch.setattr(checks, "REGISTRY", registry)
    monkeypatch.setattr(checks, "REFERENCES", {r["id"]: r for r in registry["references"]})
    try:
        checks.test_each_why_names_the_damages_its_control_tests()
    except AssertionError:
        return
    raise AssertionError(
        "fg-characters' argument claims paragraph text only fails it, a damage its control does not test, and the "
        "clause-4 predicate accepts it: 'paragraph text only' holds none of the predicate's keywords"
    )
