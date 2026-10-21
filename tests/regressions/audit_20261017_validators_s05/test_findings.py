import contextlib
import copy
import io
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from validators import validate_phase1_outputs as phase
from validators import verify_invariants as inv
from validators.schema import load_schema, validate_mismatch_index

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "output"


@pytest.fixture
def data():
    rows = phase.load_jsonl(OUTPUT / "eva_lines.jsonl")
    report = phase.load_build_report(OUTPUT / "eva_lines_build_report.json")
    return rows, report


def accepts(checker, rows, report):
    with (
        patch.object(phase, "load_jsonl", return_value=rows),
        patch.object(inv, "stream_records", side_effect=lambda _: iter(rows)),
        patch.object(phase, "load_build_report", return_value=report),
        contextlib.redirect_stdout(io.StringIO()),
    ):
        if checker == "phase":
            return phase.validate_outputs(OUTPUT)[0]
        return inv.verify_all_invariants(OUTPUT).passed


@pytest.mark.parametrize("fault", ["has_uncertain", "has_illegible", "order"])
def test_f2_release_rejects_flags_and_order(data, fault):
    rows, report = data
    assert accepts("phase", rows, report)
    changed = copy.deepcopy(rows)
    if fault == "order":
        changed.reverse()
    else:
        changed[0][fault] = not changed[0][fault]
    assert not accepts("phase", changed, report)


@pytest.mark.parametrize("checker", ["phase", "invariant"])
@pytest.mark.parametrize(
    "field,value",
    [
        ("quire", "Z"),
        ("hand", "99"),
        ("illustration_type", "Z"),
        ("currier_language", "B"),
    ],
)
def test_f3_rejects_false_page_metadata(data, checker, field, value):
    rows, report = data
    assert accepts(checker, rows, report)
    assert rows[0]["page_id"] == "f1r"
    assert rows[0][field] != value
    changed = copy.deepcopy(rows)
    changed[0][field] = value
    assert not accepts(checker, changed, report)


@pytest.mark.parametrize("checker", ["phase", "invariant"])
@pytest.mark.parametrize(
    "field,value",
    [
        ("source_version", "not-the-source-hash"),
        ("text_clean_policy", "invented-policy"),
        ("alphabet", "invented-alphabet"),
        ("format_version", "999.0"),
        ("format_options", "invented-options"),
    ],
)
def test_f4_rejects_false_provenance(data, checker, field, value):
    rows, report = data
    assert accepts(checker, rows, report)
    changed = copy.deepcopy(rows)
    build = copy.deepcopy(report)
    if field == "source_version":
        changed[0][field] = value
    else:
        build[field] = value
    assert not accepts(checker, changed, build)


@pytest.mark.parametrize("name", ["transcription_lines", "mismatch_index"])
def test_f5_documented_short_names(name):
    expected = load_schema(f"{name}.schema.json")
    assert load_schema(name) == expected
