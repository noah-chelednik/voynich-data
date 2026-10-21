# tests/regressions/92b55594/test_reach_3.py
import pytest

from tests import test_variants as checks


def test_eva_predicate_rejects_a_non_eva_alignment_reader(monkeypatch):
    other = next(
        source
        for source in checks.ORDER
        if checks.SOURCES[source]
        and checks.SOURCES[source][0]["alphabet"] != "EVA"
    )
    changed = [dict(row) for row in checks.ALIGNMENTS]
    changed[0]["reader"] = other
    monkeypatch.setattr(checks, "ALIGNMENTS", changed)

    with pytest.raises(AssertionError):
        checks.test_only_eva_is_compared()
