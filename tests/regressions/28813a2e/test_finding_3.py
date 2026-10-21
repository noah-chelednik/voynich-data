# tests/regressions/28813a2e/test_finding_3.py
import contextlib
import hashlib
import io
import json
import shutil
from pathlib import Path

import pytest

from validators import validate_phase1_outputs as phase
from validators import verify_invariants as inv


@pytest.mark.parametrize("checker", ["phase", "invariants"])
def test_charset_warning_occurs_once_per_flagged_row(tmp_path, checker):
    root = Path(phase.__file__).resolve().parents[1]
    out = tmp_path / "artifacts"
    shutil.copytree(root / "output", out)

    def result():
        with contextlib.redirect_stdout(io.StringIO()):
            if checker == "phase":
                return phase.validate_outputs(out)
            checked = inv.verify_all_invariants(out)
            return checked.passed, checked.failures

    accepted, errors = result()
    assert accepted, errors

    report_path = out / "eva_lines_build_report.json"
    report = json.loads(report_path.read_text())
    charset = [
        warning
        for warning in report["warnings"]
        if warning.startswith("Invalid chars in ")
    ]
    assert charset
    report["warnings"].append(charset[0])
    report_path.write_text(json.dumps(report), encoding="utf-8")

    manifest_path = out / "release_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    entry = next(
        entry
        for entry in manifest["files"]
        if entry["name"] == report_path.name
    )
    entry["sha256"] = hashlib.sha256(report_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    accepted, errors = result()
    assert not accepted, (checker, errors)
