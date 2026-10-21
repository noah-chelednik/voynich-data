# tests/regressions/020f7450/test_finding_2.py
import shutil

import pyarrow as pa
import pyarrow.parquet as pq

from validators.validate_phase1_outputs import check_metadata
from vcat.sources import ROOT


def test_metadata_parquet_parity_distinguishes_booleans_from_integers(
    tmp_path,
):
    out = tmp_path / "candidate"
    meta = out / "metadata"
    shutil.copytree(ROOT / "output" / "metadata", meta)

    assert not check_metadata(out)

    path = meta / "pages.parquet"
    original = pq.read_table(path)
    assert pa.types.is_boolean(original.schema.field("has_text").type)

    control = original.to_pylist()
    control[0]["hand"] = "invalid-parquet-hand"
    pq.write_table(pa.Table.from_pylist(control), path)
    assert check_metadata(out)

    changed = original.to_pylist()
    for row in changed:
        row["has_text"] = int(row["has_text"])

    replacement = pa.Table.from_pylist(changed)
    assert pa.types.is_integer(
        replacement.schema.field("has_text").type
    )
    pq.write_table(replacement, path)

    assert check_metadata(out), (
        "Parquet integer values passed as JSONL Boolean values"
    )
