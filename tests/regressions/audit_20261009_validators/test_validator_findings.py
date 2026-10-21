import contextlib
import io
import json
from pathlib import Path

import pytest

from builders.build_eva_lines import build_eva_lines, export_to_jsonl
from validators.schema import load_schema, validate_mismatch_index
from validators.validate_phase1_outputs import validate_outputs
from validators.verify_invariants import verify_all_invariants


ROOT = Path(__file__).resolve().parents[3]
SOURCE = """#=IVTFF Eva- 2.0 M 5
<f1r> <! $I=H $Q=A $P=A $L=A $H=1>
<f1r.1,@P0> qokedy.[a:o].@192;
<f1r.2,+P0> daiin.?ol.*
"""


def accepted(out):
    with contextlib.redirect_stdout(io.StringIO()):
        phase, _ = validate_outputs(out)
    return {
        "phase": phase,
        "invariants": verify_all_invariants(out).passed,
    }


@pytest.fixture
def consistent_build(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text(SOURCE, encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    records, report = build_eva_lines(source, out)
    export_to_jsonl(records, out / "eva_lines.jsonl")
    (out / "eva_lines_build_report.json").write_text(
        json.dumps(report.to_dict()), encoding="utf-8"
    )
    assert all(accepted(out).values())
    return out


def read_rows(out):
    return [
        json.loads(line)
        for line in (out / "eva_lines.jsonl").read_text().splitlines()
    ]


def write_rows(out, rows):
    (out / "eva_lines.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


@pytest.mark.parametrize("field", ["lines_with_high_ascii", "total_words"])
def test_f2_rejects_invalid_report_statistics(consistent_build, field):
    out = consistent_build
    path = out / "eva_lines_build_report.json"
    report = json.loads(path.read_text())
    report[field] = -1
    path.write_text(json.dumps(report), encoding="utf-8")
    results = accepted(out)
    assert not any(results.values()), results


def test_f3_rejects_hidden_alternatives(consistent_build):
    out = consistent_build
    rows = read_rows(out)
    row = next(row for row in rows if row["has_alternatives"])
    assert "[a:o]" in row["text"]
    row["has_alternatives"] = False
    write_rows(out, rows)
    results = accepted(out)
    assert not any(results.values()), results


def test_f3_invariants_reject_hidden_high_ascii(consistent_build):
    out = consistent_build
    rows = read_rows(out)
    row = next(row for row in rows if row["has_high_ascii"])
    assert "@192;" in row["text"]
    row["has_high_ascii"] = False
    write_rows(out, rows)
    result = verify_all_invariants(out)
    assert not result.passed, result.failures


def test_f1_committed_mismatch_rows_conform():
    rows = [
        json.loads(line)
        for line in (ROOT / "output/mismatch_index.jsonl")
        .read_text()
        .splitlines()
    ]
    assert rows
    valid, errors = validate_mismatch_index(rows)
    assert valid, errors[:5]


@pytest.mark.parametrize("name", ["transcription_lines", "mismatch_index"])
def test_f4_documented_schema_names_resolve(name):
    assert load_schema(name) == load_schema(name + ".schema.json")
