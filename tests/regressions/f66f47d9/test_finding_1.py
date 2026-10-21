# tests/regressions/f66f47d9/test_finding_1.py
import json
import os
import shutil
from pathlib import Path

import pytest

from validators import validate_phase1_outputs as phase
from validators import verify_invariants as invariants


ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("validator", ["phase", "invariants"])
def test_changed_words_with_preserved_mtime_are_revalidated(tmp_path, validator):
    for name in (
        "eva_lines.jsonl",
        "eva_lines_build_report.json",
        "eva_words.jsonl",
        "eva_words.parquet",
        "eva_words_report.json",
    ):
        shutil.copy2(ROOT / "output" / name, tmp_path / name)

    def accepted():
        if validator == "phase":
            return phase.validate_outputs(tmp_path)[0]
        return invariants.verify_all_invariants(tmp_path).passed

    assert accepted()

    target = tmp_path / "eva_words.jsonl"
    saved = target.stat()
    original = target.read_bytes()
    first, separator, remainder = original.partition(b"\n")
    row = json.loads(first)
    word = row["word"]
    row["word"] = ("x" if word[0] != "x" else "y") + word[1:]
    replacement = json.dumps(
        row, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    changed = replacement + separator + remainder

    assert changed != original
    assert len(changed) == len(original)
    target.write_bytes(changed)
    os.utime(target, ns=(saved.st_atime_ns, saved.st_mtime_ns))
    assert target.stat().st_size == saved.st_size
    assert target.stat().st_mtime_ns == saved.st_mtime_ns

    assert not accepted(), "Validation reused success for different word bytes"
