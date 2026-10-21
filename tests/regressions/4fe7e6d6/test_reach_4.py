# tests/regressions/4fe7e6d6/test_reach_4.py
"""Clause 2: an argument claiming a damage its control does not test is refused, worded with or without the old verbs.
DAMAGE_WORDS gives the damage word-division-lost the words `word division`, written with `\\b` at both ends and no
plural or hyphen form, while the other damages' words take their plurals (`readings?`, `paragraphs?`, `spaces?`). So an
argument that claims the damage as "word divisions" (or "word-division") is accepted where "word division" is refused."""
import copy

import pytest

from tests import test_reference_checks as checks


def _with_claim(monkeypatch, claim):
    registry = copy.deepcopy(checks.REGISTRY)
    target = next(r for r in registry["references"] if "word-division-lost" not in r["control"])
    argument, listed = target["why"].split("Fails on:")
    target["why"] = argument.rstrip() + claim + " Fails on:" + listed
    monkeypatch.setattr(checks, "REGISTRY", registry)
    monkeypatch.setattr(checks, "REFERENCES", {r["id"]: r for r in registry["references"]})


def test_a_claim_of_word_divisions_outside_the_control_is_refused(monkeypatch):
    checks.test_each_why_names_the_damages_its_control_tests()  # passes as committed
    with monkeypatch.context() as m:
        _with_claim(m, " Merging a word division moves the count beyond the tolerance.")
        with pytest.raises(AssertionError):  # control: the singular is refused
            checks.test_each_why_names_the_damages_its_control_tests()
    _with_claim(monkeypatch, " Merging word divisions moves the count beyond the tolerance.")
    with pytest.raises(AssertionError):
        checks.test_each_why_names_the_damages_its_control_tests()
