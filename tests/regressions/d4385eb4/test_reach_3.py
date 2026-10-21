# tests/regressions/d4385eb4/test_reach_3.py
import pytest

from builders import stage_release as sr
from tests import test_staging as gate


def test_staged_byte_predicate_checks_unselected_twins(tmp_path):
    staging = tmp_path / "staged"
    sr.stage(staging)

    twin = staging / "voynich-eva" / "eva_lines.jsonl"
    twin.write_bytes(twin.read_bytes() + b"\n")

    with pytest.raises(AssertionError):
        gate.test_every_staged_file_is_its_build_file(staging)
