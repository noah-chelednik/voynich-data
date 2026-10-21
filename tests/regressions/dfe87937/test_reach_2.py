# tests/regressions/dfe87937/test_reach_2.py
import json
from dataclasses import replace

import pytest

from builders.build_eva_lines import build_eva_lines, export_to_jsonl
from validators.verify_invariants import verify_all_invariants


SOURCE = """#=IVTFF Eva- 2.0 M 5
<f1r>      <! $I=H $Q=A $P=A $L=A $H=1>
<f1r.1,@P0>       fachys.ykal
<f1r.2,+P0>       sory.ckhar
"""


@pytest.mark.parametrize(
    "case",
    ["replacement_locus", "unrelated_reported_locus"],
)
def test_invariants_require_source_locus_membership(tmp_path, case):
    source = tmp_path / "source.txt"
    source.write_text(SOURCE, encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()

    records, report = build_eva_lines(source, out)
    jsonl = out / "eva_lines.jsonl"
    report_path = out / "eva_lines_build_report.json"
    export_to_jsonl(records, jsonl)
    payload = report.to_dict()
    report_path.write_text(json.dumps(payload), encoding="utf-8")

    control = verify_all_invariants(out)
    assert control.passed, control.failures

    if case == "replacement_locus":
        new_number = max(record.line_number for record in records) + 1
        replacement = replace(
            records[-1],
            line_number=new_number,
            line_id=f"{records[-1].page_id}:{new_number}",
        )
        changed = records[:-1] + [replacement]
        assert replacement.line_id not in {
            record.line_id for record in records
        }
    else:
        changed = records[:-1]
        payload["reported_loci"] = ["f9r:1"]
        assert set(payload["reported_loci"]).isdisjoint(
            record.line_id for record in records
        )
        report_path.write_text(json.dumps(payload), encoding="utf-8")

    assert records[-1].line_id not in {
        record.line_id for record in changed
    }
    export_to_jsonl(changed, jsonl)

    result = verify_all_invariants(out)
    assert not result.passed, (
        f"Accepted unaccounted source-locus loss through {case}: "
        f"{result.failures}"
    )
