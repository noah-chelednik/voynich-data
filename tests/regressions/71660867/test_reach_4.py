# tests/regressions/71660867/test_reach_4.py
import json
import shutil
from pathlib import Path

import pytest

from validators import validate_phase1_outputs as phase
from validators import verify_invariants as invariants


ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("validator", ["phase", "invariants"])
def test_validators_reject_word_companions_without_jsonl(tmp_path, validator):
    source = ROOT / "output"
    for name in (
        "eva_lines.jsonl",
        "eva_lines_build_report.json",
        "eva_words.jsonl",
        "eva_words.parquet",
        "eva_words_report.json",
    ):
        shutil.copy2(source / name, tmp_path / name)

    def accepted():
        if validator == "phase":
            return phase.validate_outputs(tmp_path)[0]
        return invariants.verify_all_invariants(tmp_path).passed

    assert accepted()

    (tmp_path / "eva_words.jsonl").unlink()
    report_path = tmp_path / "eva_words_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["lines_sha256"] = "0" * 64
    report_path.write_text(json.dumps(report), encoding="utf-8")

    assert not accepted(), "Word companions were accepted without their JSONL"
