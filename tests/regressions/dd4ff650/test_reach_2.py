# tests/regressions/dd4ff650/test_reach_2.py
import pytest

from tests import test_stability as checks


def test_erratum_requires_all_declared_columns(monkeypatch):
    checks.test_every_roadmap_defect_has_an_erratum()
    row = next(
        line for line in checks.ERRATA.splitlines()
        if line.startswith("| E-")
    )
    identifier_only = "|" + row.split("|")[1] + "|"
    changed = checks.ERRATA.replace(row, identifier_only, 1)
    monkeypatch.setattr(checks, "ERRATA", changed)

    with pytest.raises(AssertionError):
        checks.test_every_roadmap_defect_has_an_erratum()
