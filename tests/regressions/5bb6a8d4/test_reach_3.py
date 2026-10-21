# tests/regressions/5bb6a8d4/test_reach_3.py
import contextlib
import io
import json

import pytest

from builders.build_eva_lines import build_eva_lines, export_to_jsonl
from validators.validate_phase1_outputs import validate_outputs
from validators.verify_invariants import verify_all_invariants


def write_build(base, data):
    base.mkdir()
    source = base / "source.txt"
    source.write_bytes(data)
    out = base / "out"
    out.mkdir()

    records, report = build_eva_lines(source, out)
    export_to_jsonl(records, out / "eva_lines.jsonl")
    (out / "eva_lines_build_report.json").write_text(
        json.dumps(report.to_dict()), encoding="utf-8"
    )
    return out, report


def accepted(out, validator):
    with contextlib.redirect_stdout(io.StringIO()):
        if validator == "phase":
            return validate_outputs(out)
        report = verify_all_invariants(out)
        return report.passed, report.failures


@pytest.mark.parametrize("validator", ["phase", "invariants"])
def test_reported_undecodable_locus_does_not_reject_accepted_rows(
    tmp_path, validator
):
    valid = (
        b"#=IVTFF Eva- 2.0 M\n"
        b"<f1r> <! $Q=A $L=A $H=1 $I=H>\n"
        b"<f1r.1,@P0> qokedy\n"
    )
    control, _ = write_build(tmp_path / "control", valid)
    ok, errors = accepted(control, validator)
    assert ok, errors

    out, report = write_build(
        tmp_path / "reported",
        valid + b"<f1r.2,+P0> a\xffb\n",
    )
    assert report.reported_loci == ["f1r:2"]
    assert report.warnings
    assert not report.loss_problems()

    ok, errors = accepted(out, validator)
    assert ok, errors
