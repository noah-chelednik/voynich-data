# tests/regressions/88bdfa1e/test_finding_1.py
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from validators import validate_phase1_outputs as phase
from validators import verify_invariants as invariants


ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("validator", ["phase", "invariants"])
def test_line_ending_change_revalidates_word_provenance(tmp_path, validator):
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

    target = tmp_path / "eva_lines.jsonl"
    original_bytes = target.read_bytes()
    original_text = target.read_text(encoding="utf-8")
    changed = original_bytes.replace(b"\n", b"\r\n")
    assert changed != original_bytes
    target.write_bytes(changed)

    assert target.read_text(encoding="utf-8") == original_text
    report = json.loads(
        (tmp_path / "eva_words_report.json").read_text(encoding="utf-8")
    )
    assert hashlib.sha256(changed).hexdigest() != report["lines_sha256"]

    assert not accepted(), "Cached success bypassed the byte-exact input hash"
