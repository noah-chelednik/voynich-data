# tests/regressions/ce645765/test_finding_2.py
import json
from dataclasses import replace

from builders.build_eva_lines import build_eva_lines, export_to_jsonl
from validators.validate_phase1_outputs import validate_outputs


SOURCE = """#=IVTFF Eva- 2.0 M 5
<f1r>      <! $I=H $Q=A $P=A $L=A $H=1>
<f1r.1,@P0>       fachys.ykal
<f1r.2,+P0>       sory.ckhar
"""


def test_phase_validator_rejects_duplicate_source_rows(tmp_path):
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

    valid, errors = validate_outputs(out)
    assert valid, errors

    duplicate = replace(records[-1], line_index=records[-1].line_index + 1)
    changed = records + [duplicate]
    assert len({row.line_id for row in changed}) < len(changed)
    export_to_jsonl(changed, jsonl)
    payload["total_lines"] = len(changed)
    report_path.write_text(json.dumps(payload), encoding="utf-8")

    valid, errors = validate_outputs(out)
    assert not valid, f"Accepted duplicate source rows: {errors}"
