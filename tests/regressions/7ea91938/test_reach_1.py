# tests/regressions/7ea91938/test_reach_1.py
"""Claim 2 (every published value is met): the predicate enumerates the registry through a dict keyed by id, so a
published value whose id is repeated is silently dropped from the parametrization and never checked."""
import copy
import importlib.util
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]


def test_a_published_value_with_a_repeated_id_is_checked(monkeypatch):
    path = ROOT / "data_sources" / "references.yaml"
    registry = yaml.safe_load(path.read_text(encoding="utf-8"))
    bad = copy.deepcopy(next(r for r in registry["references"] if r["id"] == "zl-h1"))
    bad["value"] = 9.999  # a published value VCAT does not meet
    registry["references"].insert(0, bad)
    mutated = yaml.safe_dump(registry, allow_unicode=True)
    real_read_text = Path.read_text

    def read_text(self, *args, **kwargs):
        if Path(self).resolve() == path.resolve():
            return mutated
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_text)
    spec = importlib.util.spec_from_file_location(
        "reach_fresh_reference_checks", ROOT / "tests" / "test_reference_checks.py"
    )
    checks = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, checks)
    spec.loader.exec_module(checks)
    monkeypatch.setattr(Path, "read_text", real_read_text)

    # the predicate's module read the mutated registry: the unmet value is in it
    assert [r["value"] for r in checks.REGISTRY["references"] if r["id"] == "zl-h1"] == [9.999, 3.862]

    # the node ids the predicate runs: one per key of its REFERENCES
    rejected = []
    for reference_id in sorted(checks.REFERENCES):
        try:
            checks.test_each_published_value_is_met(reference_id)
        except AssertionError:
            rejected.append(reference_id)
    # the registry holds a published value (9.999) that is not met: the predicate must reject the state
    assert rejected, "every node passed: the repeated-id value 9.999 was never checked"
