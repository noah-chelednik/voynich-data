# tests/regressions/caac4571/test_finding_2.py
import json
import shutil

import pytest

from tests import test_structured_layer as checks


def test_metadata_freshness_compares_source_file(tmp_path, monkeypatch):
    committed = tmp_path / "committed"
    shutil.copytree(
        checks.OUTPUT / "metadata",
        committed / "metadata",
    )
    monkeypatch.setattr(checks, "OUTPUT", committed)

    checks.test_committed_metadata_is_a_fresh_build(tmp_path / "baseline")

    report_path = committed / "metadata" / "metadata_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["source_file"] = "different-upstream-source.txt"
    report_path.write_text(json.dumps(report), encoding="utf-8")

    with pytest.raises(AssertionError):
        checks.test_committed_metadata_is_a_fresh_build(tmp_path / "fresh")
