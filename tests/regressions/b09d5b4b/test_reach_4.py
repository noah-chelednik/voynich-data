# tests/regressions/b09d5b4b/test_reach_4.py
import pytest

from tests import test_sources as checks


def test_used_by_predicate_checks_both_directions(monkeypatch):
    checks.test_used_by_lists_name_only_datasets()
    dataset = checks.SOURCES["datasets"][0]
    source = dataset["sources"][0]
    name = dataset["name"]
    changed = {
        key: list(values)
        for key, values in checks.SOURCES_USED_BY.items()
    }
    assert name in changed[source]
    changed[source].remove(name)
    monkeypatch.setattr(checks, "SOURCES_USED_BY", changed)

    with pytest.raises(AssertionError):
        checks.test_used_by_lists_name_only_datasets()
