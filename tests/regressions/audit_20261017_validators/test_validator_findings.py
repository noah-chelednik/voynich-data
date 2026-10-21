import contextlib
import copy
import io
import json
from collections import Counter
from pathlib import Path
from unittest.mock import patch

import pytest

from validators import validate_phase1_outputs as phase
from validators import verify_invariants as inv
from validators.schema import load_schema, validate_mismatch_index


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "output"


def accepted(rows, report):
    with (
        patch.object(phase, "load_jsonl", return_value=rows),
        patch.object(phase, "load_build_report", return_value=report),
        patch.object(inv, "stream_records", side_effect=lambda path: iter(rows)),
        contextlib.redirect_stdout(io.StringIO()),
    ):
        phase_ok, _ = phase.validate_outputs(OUT)
        invariant_ok = inv.verify_all_invariants(OUT).passed
    return phase_ok, invariant_ok


@pytest.fixture
def consistent_data():
    rows = [
        json.loads(line)
        for line in (OUT / "eva_lines.jsonl").read_text().splitlines()
    ]
    report = json.loads((OUT / "eva_lines_build_report.json").read_text())
    assert all(accepted(rows, report))
    return copy.deepcopy(rows), copy.deepcopy(report)


@pytest.mark.parametrize("field", ["position", "line_type"])
def test_f2_rejects_structure_inconsistent_with_source(consistent_data, field):
    rows, report = consistent_data
    row = rows[0]
    if field == "position":
        row[field] = "+" if row[field] != "+" else "@"
    else:
        row[field] = "label" if row[field] != "label" else "paragraph"
        report["lines_by_type"] = dict(Counter(r["line_type"] for r in rows))
    result = accepted(rows, report)
    assert not any(result), result


@pytest.mark.parametrize("field", ["has_uncertain", "has_illegible"])
def test_f3_phase_rejects_wrong_flags(consistent_data, field):
    rows, report = consistent_data
    rows[0][field] = not rows[0][field]
    phase_ok, invariant_ok = accepted(rows, report)
    assert not invariant_ok
    assert not phase_ok


def test_f3_phase_rejects_wrong_order(consistent_data):
    rows, report = consistent_data
    rows.reverse()
    phase_ok, invariant_ok = accepted(rows, report)
    assert not invariant_ok
    assert not phase_ok


@pytest.mark.parametrize("field", ["source_version", "text_clean_policy"])
def test_f4_rejects_invented_provenance(consistent_data, field):
    rows, report = consistent_data
    if field == "source_version":
        original = rows[0][field]
        replacement = "0" * len(original)
        assert replacement != original
        rows[0][field] = replacement
    else:
        report[field] = "invented-policy"
    result = accepted(rows, report)
    assert not any(result), result


def test_f1_committed_mismatch_rows_conform_to_schema():
    rows = [
        json.loads(line)
        for line in (OUT / "mismatch_index.jsonl").read_text().splitlines()
    ]
    assert rows
    valid, errors = validate_mismatch_index(rows)
    assert valid, errors[:5]


@pytest.mark.parametrize("name", ["transcription_lines", "mismatch_index"])
def test_f5_documented_short_schema_names_work(name):
    assert load_schema(name) == load_schema(name + ".schema.json")
