# tests/regressions/caac4571/test_finding_1.py
import json
import shutil

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from validators import validate_phase1_outputs as phase
from validators import verify_invariants as invariants
from vcat.sources import ROOT


@pytest.mark.parametrize("validator", ["phase", "invariants"])
@pytest.mark.parametrize("tamper", ["renamed_sheet", "repeated_members"])
def test_validators_reject_repeated_physical_structure(
    tmp_path, validator, tamper
):
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
    if tamper == "renamed_sheet":
        duplicate = dict(rows[0])
        duplicate["bifolio_id"] += "-duplicate"
        rows.append(duplicate)
    else:
        rows[0]["folio_ids"].append(rows[0]["folio_ids"][0])
        rows[0]["page_ids"].append(rows[0]["page_ids"][0])

    jsonl.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    pq.write_table(
        pa.Table.from_pylist(rows),
        jsonl.with_suffix(".parquet"),
    )

    assert problems(), "Repeated physical structure must fail validation"
