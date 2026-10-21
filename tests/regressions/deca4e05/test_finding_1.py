# tests/regressions/deca4e05/test_finding_1.py
import json
import shutil

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from validators import validate_phase1_outputs as phase
from validators import verify_invariants as invariants
from vcat.sources import ROOT


@pytest.mark.parametrize("validator", ["phase", "invariants"])
@pytest.mark.parametrize(
    "tamper",
    ["quire_prefix", "shared_leaf", "leaf_order"],
)
def test_validators_enforce_canonical_sheet_structure(
    tmp_path, validator, tamper
):
    out = tmp_path / "candidate"
    out.mkdir()
    for name in ("eva_lines.jsonl", "eva_lines_build_report.json"):
        shutil.copy2(ROOT / "output" / name, out / name)
    shutil.copytree(ROOT / "output" / "metadata", out / "metadata")
    meta = out / "metadata"

    def problems():
        if validator == "phase":
            return phase.validate_outputs(out)[1]
        return invariants.verify_all_invariants(out).failures

    def read(stem):
        return [
            json.loads(line)
            for line in (meta / f"{stem}.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]

    def write(stem, rows):
        (meta / f"{stem}.jsonl").write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
            encoding="utf-8",
        )
        pq.write_table(
            pa.Table.from_pylist(rows),
            meta / f"{stem}.parquet",
        )

    assert not problems()

    sheets = read("bifolia")
    first = next(sheet for sheet in sheets if len(sheet["folio_ids"]) > 1)

    if tamper == "quire_prefix":
        first["quire_id"] = "x" + first["quire_id"][1:]
        first["bifolio_id"] = (
            f"{first['quire_id']}.b{first['bifolio_number']}"
        )
    elif tamper == "shared_leaf":
        second = next(
            sheet
            for sheet in sheets
            if sheet["bifolio_id"] != first["bifolio_id"]
            and len(sheet["folio_ids"]) > 1
        )
        old_leaf = second["folio_ids"][0]
        new_leaf = first["folio_ids"][0]
        second["folio_ids"][0] = new_leaf
        pages = read("pages")
        for page in pages:
            if page["folio_id"] == old_leaf:
                page["folio_id"] = new_leaf
        write("pages", pages)
    else:
        first["folio_ids"].reverse()

    write("bifolia", sheets)
    assert problems(), f"Invalid sheet structure accepted: {tamper}"
