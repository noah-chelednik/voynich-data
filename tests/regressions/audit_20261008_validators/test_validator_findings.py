import json
import re
from pathlib import Path

from validators import validate_phase1_outputs as phase
from validators import verify_invariants as inv
from validators.schema import validate_mismatch_index

ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "pyproject.toml").is_file()
)
OUTPUT = ROOT / "output"


def eva_rows():
    return [
        json.loads(line)
        for line in (OUTPUT / "eva_lines.jsonl").read_text().splitlines()
    ]


def test_phase_validator_rejects_schema_invalid_row(monkeypatch):
    row = dict(eva_rows()[0], line_type="INVALID", line_number=-1)
    monkeypatch.setattr(phase, "load_jsonl", lambda path: [row])
    valid, errors = phase.validate_outputs(OUTPUT)
    assert not valid, "Schema-invalid output was accepted"


def test_source_derived_population_passes_count_checks():
    source = ROOT / "data_sources/cache/ZL3b-n.txt"
    records = []
    for line in source.read_text().splitlines():
        match = re.match(r"^<([^>.]+)\.([0-9]+),", line)
        if match:
            records.append({"page_id": match.group(1)})
    assert records
    report = inv.InvariantReport()
    inv.check_record_count(records, report)
    inv.check_page_count(records, report)
    assert report.passed, report.failures


def test_phase_validator_rejects_empty_output(monkeypatch):
    report = json.loads(
        (OUTPUT / "eva_lines_build_report.json").read_text()
    )
    assert report["total_lines"]
    monkeypatch.setattr(phase, "load_jsonl", lambda path: [])
    valid, errors = phase.validate_outputs(OUTPUT)
    assert not valid, "Empty output was accepted against a nonempty build report"


def test_build_report_rejects_reported_failure(monkeypatch):
    path = OUTPUT / "eva_lines_build_report.json"
    report = json.loads(path.read_text())
    report.update(
        source_hash="unrelated",
        source_verified=False,
        total_lines=-1,
        errors=["failed build"],
    )
    monkeypatch.setattr(phase.json, "load", lambda stream: report)
    errors = phase.check_build_report(path)
    assert errors, "A failed and inconsistent build report was accepted"


def test_output_checkers_reject_replaced_clean_text(monkeypatch):
    original = eva_rows()
    corrupt = [dict(row, text_clean="a") for row in original]
    assert any(row["text_clean"] != "a" for row in original)
    monkeypatch.setattr(inv, "stream_records", lambda path: iter(corrupt))
    monkeypatch.setattr(phase, "load_jsonl", lambda path: corrupt)
    invariant_report = inv.verify_all_invariants(OUTPUT)
    phase_valid, phase_errors = phase.validate_outputs(OUTPUT)
    assert not invariant_report.passed, "Invariant checker accepted replaced text"
    assert not phase_valid, "Phase validator accepted replaced text"


def test_committed_mismatch_rows_conform_to_schema():
    rows = [
        json.loads(line)
        for line in (OUTPUT / "mismatch_index.jsonl").read_text().splitlines()
    ]
    assert rows
    valid, errors = validate_mismatch_index(rows)
    assert valid, errors
