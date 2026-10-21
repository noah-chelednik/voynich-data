# tests/regressions/ce645765/test_finding_1.py
import json

import pytest

from builders.build_eva_lines import build_eva_lines, export_to_jsonl
from validators.verify_invariants import verify_all_invariants


SOURCE = """#=IVTFF Eva- 2.0 M 5
<f1r>      <! $I=H $Q=A $P=A $L=A $H=1>
<f1r.1,@P0>       fachys.ykal
<f1r.2,+P0>       sory.ckhar
"""


@pytest.mark.parametrize(
    "defect",
    ["row_schema", "errors", "source_verified", "source_hash", "total_lines"],
)
def test_invariants_enforce_promised_schema_and_report_checks(tmp_path, defect):
    source = tmp_path / "source.txt"
    source.write_text(SOURCE, encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    records, report = build_eva_lines(source, out)
    jsonl = out / "eva_lines.jsonl"
    export_to_jsonl(records, jsonl)
    report_path = out / "eva_lines_build_report.json"
    payload = report.to_dict()
    report_path.write_text(json.dumps(payload), encoding="utf-8")

    control = verify_all_invariants(out)
    assert control.passed, control.failures

    if defect == "row_schema":
        rows = [record.to_dict() for record in records]
        rows[0]["line_type"] = "INVALID"
        jsonl.write_text(
            "".join(json.dumps(row) + "\n" for row in rows),
            encoding="utf-8",
        )
    else:
        changes = {
            "errors": ["failed build"],
            "source_verified": False,
            "source_hash": "unrelated",
            "total_lines": len(records) + 1,
        }
        payload[defect] = changes[defect]
        report_path.write_text(json.dumps(payload), encoding="utf-8")

    result = verify_all_invariants(out)
    assert not result.passed, (
        f"Invariant validator accepted {defect}: {result.failures}"
    )
