# tests/regressions/dfe87937/test_reach_1.py
import json

import pytest

from builders.build_eva_lines import build_eva_lines, export_to_jsonl
from validators.validate_phase1_outputs import validate_outputs


SOURCE = """#=IVTFF Eva- 2.0 M 5
<f1r>      <! $I=H $Q=A $P=A $L=A $H=1>
<f1r.1,@P0>       fachys.ykal
<f1r.2,+P0>       sory.ckhar
"""


@pytest.mark.parametrize(
    "field",
    ["total_pages", "loci_emitted", "loci_reported"],
)
def test_phase_validator_reconciles_report_totals(tmp_path, field):
    source = tmp_path / "source.txt"
    source.write_text(SOURCE, encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()

    records, report = build_eva_lines(source, out)
    export_to_jsonl(records, out / "eva_lines.jsonl")
    report_path = out / "eva_lines_build_report.json"
    payload = report.to_dict()
    report_path.write_text(json.dumps(payload), encoding="utf-8")

    valid, errors = validate_outputs(out)
    assert valid, errors

    payload[field] += 1
    report_path.write_text(json.dumps(payload), encoding="utf-8")

    valid, errors = validate_outputs(out)
    assert not valid, f"Accepted inconsistent report total {field}: {errors}"
