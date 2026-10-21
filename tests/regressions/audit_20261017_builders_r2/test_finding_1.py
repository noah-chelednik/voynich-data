# tests/regressions/audit_20261017_builders_r2/test_finding_1.py
import contextlib
import io
from pathlib import Path
from unittest.mock import patch

import pyarrow.parquet as pq

from validators import validate_phase1_outputs as phase
from validators import verify_invariants as inv


def test_mismatch_parquet_content_is_verified():
    out = Path(__file__).resolve().parents[3] / "output"

    def accepted():
        with contextlib.redirect_stdout(io.StringIO()):
            return (
                phase.validate_outputs(out)[0],
                inv.verify_all_invariants(out).passed,
            )

    assert accepted() == (True, True)
    real = pq.read_table
    target = out / "mismatch_index.parquet"
    original = real(target)
    damaged = original.slice(0, original.num_rows - 1)
    assert damaged.num_rows < original.num_rows

    def replacement(path, *args, **kwargs):
        if Path(path).resolve() == target.resolve():
            return damaged
        return real(path, *args, **kwargs)

    with patch.object(pq, "read_table", side_effect=replacement):
        assert accepted() == (False, False)
