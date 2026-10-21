# tests/regressions/7454c2f9/test_finding_4.py
import json
from pathlib import Path

import pytest

from validators.validate_phase1_outputs import check_metadata


@pytest.mark.parametrize(
    "field",
    ["total_lines", "total_labels", "complete_quires", "pages_by_hand"],
)
def test_metadata_report_reconciles_each_summary(monkeypatch, field):
    root = Path(__file__).resolve().parents[3]
    output = root / "output"
    report_path = output / "metadata" / "metadata_report.json"
    assert check_metadata(output) == []

    report = json.loads(report_path.read_text())
    if isinstance(report[field], dict):
        assert report[field]
        report[field] = {}
    else:
        report[field] += 1

    original_read = Path.read_text

    def read(path, *args, **kwargs):
        if path.resolve() == report_path.resolve():
            return json.dumps(report)
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read)
    problems = check_metadata(output)
    assert any(field in problem for problem in problems), problems
