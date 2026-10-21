# tests/regressions/audit_20261017_builders/test_finding_2.py
import importlib
import json
import sys
from pathlib import Path

import pytest


def test_requested_parquet_export_failure_fails_build(tmp_path, monkeypatch):
    module = importlib.import_module("builders.build_eva_lines")
    root = Path(__file__).resolve().parents[3]

    def fail_export(*args, **kwargs):
        raise RuntimeError("Parquet export unavailable")

    monkeypatch.setattr(module, "export_to_parquet", fail_export)
    monkeypatch.setattr(sys, "argv", [
        "builder",
        "--source", str(root / "data_sources/cache/ZL3b-n.txt"),
        "--output-dir", str(tmp_path),
        "--format", "both",
    ])

    with pytest.raises((SystemExit, RuntimeError)) as failure:
        module.main()
    if isinstance(failure.value, SystemExit):
        assert failure.value.code != 0


def test_jsonl_only_manifest_lists_existing_outputs(tmp_path, monkeypatch):
    module = importlib.import_module("builders.build_eva_lines")
    root = Path(__file__).resolve().parents[3]
    monkeypatch.setattr(sys, "argv", [
        "builder",
        "--source", str(root / "data_sources/cache/ZL3b-n.txt"),
        "--output-dir", str(tmp_path),
        "--format", "jsonl",
    ])
    module.main()
    manifest = json.loads((tmp_path / "release_manifest.json").read_text())
    missing = [
        entry["name"] for entry in manifest["files"]
        if not (tmp_path / entry["name"]).is_file()
    ]
    assert not missing, missing
