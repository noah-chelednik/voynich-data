# tests/regressions/audit_20261017_builders/test_finding_6.py
import json
from pathlib import Path

from builders.build_metadata import build_metadata_datasets


def test_persisted_metadata_report_matches_returned_report(tmp_path):
    root = Path(__file__).resolve().parents[3]
    result = build_metadata_datasets(
        root / "data_sources/cache/ZL3b-n.txt",
        tmp_path,
    )
    written = json.loads((tmp_path / "metadata_report.json").read_text())
    assert written == result.report.to_dict()
