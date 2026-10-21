import contextlib
import io
import json
import shutil
from pathlib import Path

import pytest

from validators import validate_phase1_outputs as phase
from validators import verify_invariants as inv
from validators.schema import load_schema, validate_mismatch_index


ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "pyproject.toml").is_file()
)


@pytest.fixture
def copied_output(tmp_path):
    out = tmp_path / "output"
    shutil.copytree(ROOT / "output", out)
    return out


def verdict(out, checker):
    with contextlib.redirect_stdout(io.StringIO()):
        if checker == "phase":
            return phase.validate_outputs(out)
        report = inv.verify_all_invariants(out)
        return report.passed, report.failures


def test_f1_committed_mismatch_conforms():
    rows = [
        json.loads(line)
        for line in (ROOT / "output" / "mismatch_index.jsonl")
        .read_text()
        .splitlines()
    ]
    assert rows
    valid, errors = validate_mismatch_index(rows)
    assert valid, errors


@pytest.mark.parametrize("checker", ["phase", "invariants"])
def test_f2_reordered_and_renumbered_loci_rejected(copied_output, checker):
    valid, errors = verdict(copied_output, checker)
    assert valid, errors

    path = copied_output / "eva_lines.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    first, second = rows[:2]
    assert first["page_id"] == second["page_id"]
    assert first["source_line"] < second["source_line"]

    first_index = first["line_index"]
    second_index = second["line_index"]
    rows[0], rows[1] = second, first
    rows[0]["line_index"] = first_index
    rows[1]["line_index"] = second_index
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))

    valid, errors = verdict(copied_output, checker)
    assert not valid, errors


@pytest.mark.parametrize("checker", ["phase", "invariants"])
@pytest.mark.parametrize("damage", ["missing", "unreadable", "different"])
def test_f3_bad_parquet_rejected(copied_output, checker, damage):
    valid, errors = verdict(copied_output, checker)
    assert valid, errors

    manifest = json.loads(
        (copied_output / "release_manifest.json").read_text()
    )
    path = copied_output / "eva_lines.parquet"
    assert path.name in {entry["name"] for entry in manifest["files"]}

    if damage == "missing":
        path.unlink()
    elif damage == "unreadable":
        path.write_bytes(b"not a parquet file\n")
    else:
        import pyarrow as pa
        import pyarrow.parquet as pq

        table = pq.read_table(path)
        rows = table.to_pylist()
        rows[0]["text_clean"] += "a"
        pq.write_table(pa.Table.from_pylist(rows, schema=table.schema), path)

    valid, errors = verdict(copied_output, checker)
    assert not valid, errors


def test_f4_documented_short_schema_name():
    expected = load_schema("transcription_lines.schema.json")
    assert load_schema("transcription_lines") == expected
