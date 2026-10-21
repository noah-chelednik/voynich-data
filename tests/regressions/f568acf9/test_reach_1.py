# tests/regressions/f568acf9/test_reach_1.py
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
def test_reported_pages_cannot_erase_accepted_page_summaries(tmp_path, checker):
    root = Path(phase.__file__).resolve().parents[1]
    out = tmp_path / "artifacts"
    shutil.copytree(root / "output", out)

    def result():
        with contextlib.redirect_stdout(io.StringIO()):
            if checker == "phase":
                return phase.validate_outputs(out)
            checked = inv.verify_all_invariants(out)
            return checked.passed, checked.failures

    success, errors = result()
    assert success, errors

    rows = [
        json.loads(line)
        for line in (out / "eva_lines.jsonl").read_text().splitlines()
    ]
    report_path = out / "eva_lines_build_report.json"
    report = json.loads(report_path.read_text())
    accepted = {row["page_id"] for row in rows}
    accepted.update(report["page_ids_without_lines"])
    assert accepted
    assert report["pages_by_language"] and report["pages_by_section"]

    report["reported_pages"] = sorted(accepted)
    report["pages_by_language"] = {}
    report["pages_by_section"] = {}
    report_path.write_text(json.dumps(report), encoding="utf-8")

    manifest_path = out / "release_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    for entry in manifest["files"]:
        if entry["name"] == report_path.name:
            entry["sha256"] = hashlib.sha256(report_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    success, errors = result()
    assert not success, (
        checker,
        "Accepted pages disappeared from both summaries via reported_pages",
        errors,
    )
