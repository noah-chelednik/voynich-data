# tests/regressions/cc2c2127/test_finding_3.py
from pathlib import Path

from builders.build_eva_lines import build_eva_lines
from vcat.loss_accounting import CACHE_DIR, resolve_source
from vcat.sources import repo_relative


def test_external_relative_source_survives_report_serialization(
    tmp_path, monkeypatch
):
    source = tmp_path / "external-source.ivtff"
    source.write_bytes((CACHE_DIR / "ZL3b-n.txt").read_bytes())
    monkeypatch.chdir(tmp_path)

    # Positive control: the same external file resolves when absolute.
    assert resolve_source(repo_relative(source)) == source

    records, report = build_eva_lines(
        Path(source.name), tmp_path / "build"
    )
    assert records and not report.loss_problems()
    assert resolve_source(report.source_file) == source
