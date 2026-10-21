# tests/regressions/f6661c36/test_finding_1.py
import contextlib
import io
import json
import shutil
from pathlib import Path

import pytest

from validators import validate_phase1_outputs as phase
from validators import verify_invariants as invariants
from validators.schema import validate_mismatch_index

ROOT = next(
    p for p in Path(__file__).resolve().parents
    if (p / "pyproject.toml").is_file()
)


@pytest.mark.parametrize("checker", ["phase", "invariants"])
def test_output_validation_rejects_schema_invalid_mismatch(tmp_path, checker):
    output = tmp_path / "output"
    shutil.copytree(ROOT / "output", output)

    def accepted():
        with contextlib.redirect_stdout(io.StringIO()):
            if checker == "phase":
                return phase.validate_outputs(output)[0]
            return invariants.verify_all_invariants(output).passed

    assert accepted(), "Positive control: committed output must validate"

    path = output / "mismatch_index.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert rows
    assert validate_mismatch_index(rows) == (True, [])

    rows[0]["status"] = "INVALID"
    valid, errors = validate_mismatch_index(rows)
    assert not valid and errors, "The standalone schema must detect the damage"

    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )
    assert not accepted(), "Production validation ignored invalid mismatch data"
