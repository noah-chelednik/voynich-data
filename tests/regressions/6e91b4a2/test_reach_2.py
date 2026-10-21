# tests/regressions/6e91b4a2/test_reach_2.py
import json
import shutil

import pytest

from tests import test_structured_layer as checks


def test_metadata_freshness_predicate_checks_report(tmp_path, monkeypatch):
    committed = tmp_path / "committed"
    shutil.copytree(
        checks.OUTPUT / "metadata",
        committed / "metadata",
    )
    report_path = committed / "metadata" / "metadata_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["total_bifolia"] += 1
    report_path.write_text(json.dumps(report), encoding="utf-8")
    monkeypatch.setattr(checks, "OUTPUT", committed)

    with pytest.raises(AssertionError):
        checks.test_committed_metadata_is_a_fresh_build(tmp_path / "fresh")
