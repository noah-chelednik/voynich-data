# tests/regressions/07b7ddfc/test_finding_1.py
import contextlib
import io
import json
import shutil
from pathlib import Path

import pytest

from validators import validate_phase1_outputs as phase
from validators import verify_invariants as inv


@pytest.mark.parametrize("checker", ["phase", "invariants"])
@pytest.mark.parametrize("manifest_value", ["omitted", "null"])
def test_manifest_page_statistics_cannot_be_erased(
    tmp_path, checker, manifest_value
):
    root = Path(__file__).resolve().parents[3]
    output = tmp_path / "output"
    shutil.copytree(root / "output", output)

    def accepted():
        with contextlib.redirect_stdout(io.StringIO()):
            if checker == "phase":
                return phase.validate_outputs(output)[0]
            return inv.verify_all_invariants(output).passed

    assert accepted(), "The unchanged output must pass the positive control"

    report_path = output / "eva_lines_build_report.json"
    manifest_path = output / "release_manifest.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    for manifest_key, report_key in (
        ("pages_in_source", "total_pages_in_source"),
        ("pages_without_lines", "pages_without_lines"),
    ):
        report.pop(report_key)
        manifest["statistics"].pop(manifest_key)
        if manifest_value == "null":
            manifest["statistics"][manifest_key] = None

    report_path.write_text(json.dumps(report), encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    assert not accepted(), (
        checker,
        manifest_value,
        "Missing build-report counters must not authorize missing or null "
        "release-manifest page statistics",
    )
