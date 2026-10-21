# tests/regressions/0c2638a4/test_finding_2.py
import json

import pytest

from builders.build_eva_lines import build_eva_lines, export_to_jsonl
from validators.validate_phase1_outputs import validate_outputs
from validators.verify_invariants import verify_all_invariants


SOURCE = """#=IVTFF Eva- 2.0 M 5
<f1r>      <! $I=H $Q=A $P=A $L=A $H=1>
<f1r.1,@P0>       fachys.ykal
<f1r.2,+P0>       sory.ckhar
"""


@pytest.mark.parametrize(
    "malformed",
    [None, "f9r:1", {"f9r:1": "reported"}],
)
def test_phase_rejects_malformed_reported_loci(tmp_path, malformed):
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
    control = verify_all_invariants(out)
    assert control.passed, control.failures

    payload["reported_loci"] = malformed
    report_path.write_text(json.dumps(payload), encoding="utf-8")

    invariant_result = verify_all_invariants(out)
    assert not invariant_result.passed, invariant_result.failures

    valid, errors = validate_outputs(out)
    assert not valid, f"Silently accepted malformed reported_loci: {errors}"
