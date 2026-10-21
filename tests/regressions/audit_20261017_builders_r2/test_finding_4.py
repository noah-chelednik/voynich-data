# tests/regressions/audit_20261017_builders_r2/test_finding_4.py
import json
from pathlib import Path

from builders import build_metadata_datasets, export_metadata
from vcat.sources import repo_relative


def test_direct_metadata_export_records_its_destination(tmp_path):
    root = Path(__file__).resolve().parents[3]
    result = build_metadata_datasets(root / "data_sources/cache/ZL3b-n.txt")
    export_metadata(result, tmp_path)
    report = json.loads((tmp_path / "metadata_report.json").read_text())

    assert report["output_dir"] == repo_relative(tmp_path)
    for field, filename in (
        ("pages_file", "pages.jsonl"),
        ("folios_file", "folios.jsonl"),
        ("quires_file", "quires.jsonl"),
    ):
        assert (tmp_path / filename).is_file()
        assert report[field] == repo_relative(tmp_path / filename)
