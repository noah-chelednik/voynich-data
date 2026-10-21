import contextlib
import io
import json
import shutil
from pathlib import Path

import pytest

from validators import validate_phase1_outputs as phase
from validators import verify_invariants as inv
from validators.schema import load_schema

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def copied_output(tmp_path):
    out = tmp_path / "output"
    out.mkdir()
    for path in (ROOT / "output").iterdir():
        if path.is_file():
            shutil.copy2(path, out / path.name)
    return out


def accepted(out, checker):
    with contextlib.redirect_stdout(io.StringIO()):
        if checker == "phase":
            return phase.validate_outputs(out)[0]
        return inv.verify_all_invariants(out).passed


@pytest.mark.parametrize("checker", ["phase", "invariants"])
def test_f3_rejects_false_manifest_source_pin(copied_output, checker):
    assert accepted(copied_output, checker)
    path = copied_output / "release_manifest.json"
    manifest = json.loads(path.read_text())
    report = json.loads(
        (copied_output / "eva_lines_build_report.json").read_text()
    )
    wrong = "0" * len(report["source_hash"])
    assert wrong != report["source_hash"]
    manifest["source"]["expected_sha256"] = wrong
    manifest["source"]["verified"] = True
    path.write_text(json.dumps(manifest))
    assert not accepted(copied_output, checker)


@pytest.mark.parametrize("name", ["transcription_lines", "mismatch_index"])
def test_f4_documented_short_schema_names(name):
    expected = load_schema(name + ".schema.json")
    assert load_schema(name) == expected


@pytest.mark.parametrize("checker", ["phase", "invariants"])
@pytest.mark.parametrize("damage", ["empty", "false_status"])
def test_f1_rejects_invalid_mismatch_content(copied_output, checker, damage):
    assert accepted(copied_output, checker)
    path = copied_output / "mismatch_index.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert rows
    if damage == "empty":
        path.write_text("")
    else:
        row = next(row for row in rows if row["status"] == "different")
        assert row["zl_text_raw"] != row["it_text_raw"]
        row["status"] = "identical"
        path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    assert not accepted(copied_output, checker)


@pytest.mark.parametrize("checker", ["phase", "invariants"])
@pytest.mark.parametrize("damage", ["missing", "unreadable"])
def test_f2_rejects_bad_mismatch_parquet(copied_output, checker, damage):
    assert accepted(copied_output, checker)
    path = copied_output / "mismatch_index.parquet"
    assert path.is_file()
    if damage == "missing":
        path.unlink()
    else:
        path.write_bytes(b"not a parquet file\n")
    assert not accepted(copied_output, checker)
