# tests/regressions/ce645765/test_finding_3.py
import json

import pytest

from builders.build_eva_lines import build_eva_lines, export_to_jsonl
from validators.validate_phase1_outputs import validate_outputs


SOURCE = """#=IVTFF Eva- 2.0 M 5
<f1r>      <! $I=H $Q=A $P=A $L=A $H=1>
<f1r.1,@P0>       fachys.ykal
<f1r.2,+P0>       sory.ckhar
<f1v>      <! $I=H $Q=A $P=B $L=A $H=1>
"""


@pytest.mark.parametrize("extra_page", ["f9r", "f1v"])
def test_page_totals_reconcile_with_source_identity(tmp_path, extra_page):
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
    assert "f1v" in payload["page_ids_without_lines"]

    payload["page_ids_without_lines"].append(extra_page)
    for field in (
        "pages_without_lines",
        "total_pages",
        "total_pages_in_source",
    ):
        payload[field] += 1
    report_path.write_text(json.dumps(payload), encoding="utf-8")

    valid, errors = validate_outputs(out)
    assert not valid, f"Accepted invented or repeated page {extra_page}: {errors}"
