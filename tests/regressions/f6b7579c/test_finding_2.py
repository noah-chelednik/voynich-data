# tests/regressions/f6b7579c/test_finding_2.py
import copy
import json
import shutil

import pyarrow as pa
import pyarrow.parquet as pq

from validators.validate_phase1_outputs import check_metadata
from vcat.sources import ROOT


def test_metadata_validator_rejects_float_canvas_indices(tmp_path):
    output = tmp_path / "candidate"
    metadata = output / "metadata"
    shutil.copytree(ROOT / "output" / "metadata", metadata)
    assert not check_metadata(output)

    path = metadata / "page_canvases.jsonl"
    original = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
    ]
    assert original

    def write(rows):
        path.write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
            encoding="utf-8",
        )
        pq.write_table(
            pa.Table.from_pylist(rows),
            metadata / "page_canvases.parquet",
        )

    wrong_id = copy.deepcopy(original)
    wrong_id[0]["canvas_id"] += "#wrong"
    write(wrong_id)
    assert check_metadata(output)

    wrong_type = copy.deepcopy(original)
    for row in wrong_type:
        row["canvas_index"] = float(row["canvas_index"])
    write(wrong_type)

    assert (
        pq.read_table(metadata / "page_canvases.parquet")
        .schema.field("canvas_index")
        .type
        == pa.float64()
    )
    assert check_metadata(output), (
        "Floating-point canvas indices passed the integer field contract"
    )
