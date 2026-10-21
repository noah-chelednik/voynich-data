# tests/regressions/5d6306ba/test_reach_1.py
import contextlib
import io
import json
import shutil
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from validators import validate_phase1_outputs as phase
from validators import verify_invariants as inv


ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "pyproject.toml").is_file()
)


def accepted(output_dir, checker):
    with contextlib.redirect_stdout(io.StringIO()):
        if checker == "phase":
            return phase.validate_outputs(output_dir)[0]
        return inv.verify_all_invariants(output_dir).passed


@pytest.mark.parametrize("checker", ["phase", "invariants"])
@pytest.mark.parametrize("status", ["zl_only", "it_only"])
def test_single_source_similarity_score_is_rejected(tmp_path, checker, status):
    output_dir = tmp_path / "output"
    shutil.copytree(ROOT / "output", output_dir)
    assert accepted(output_dir, checker)

    path = output_dir / "mismatch_index.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    row = next(row for row in rows if row["status"] == status)
    assert row["similarity_score"] is None
    row["similarity_score"] = 0.5

    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    pq.write_table(
        pa.Table.from_pylist(rows),
        output_dir / "mismatch_index.parquet",
    )

    assert not accepted(output_dir, checker)
