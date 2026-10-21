# tests/regressions/6e91b4a2/test_reach_1.py
import json
import shutil

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from validators import validate_phase1_outputs as phase
from validators import verify_invariants as invariants
from vcat.sources import ROOT


@pytest.mark.parametrize("validator", ["phase", "invariants"])
def test_both_validators_reject_a_duplicated_sheet(tmp_path, validator):
    out = tmp_path / "candidate"
    out.mkdir()
    for name in ("eva_lines.jsonl", "eva_lines_build_report.json"):
        shutil.copy2(ROOT / "output" / name, out / name)
    shutil.copytree(ROOT / "output" / "metadata", out / "metadata")

    def problems():
        if validator == "phase":
            return phase.validate_outputs(out)[1]
        return invariants.verify_all_invariants(out).failures

    assert not problems()

    jsonl = out / "metadata" / "bifolia.jsonl"
    rows = [
        json.loads(line)
        for line in jsonl.read_text(encoding="utf-8").splitlines()
    ]
    rows.append(dict(rows[0]))
    jsonl.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    pq.write_table(
        pa.Table.from_pylist(rows),
        out / "metadata" / "bifolia.parquet",
    )

    assert problems(), "Duplicating a sheet must fail metadata validation"
