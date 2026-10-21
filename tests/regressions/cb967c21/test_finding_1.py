# tests/regressions/cb967c21/test_finding_1.py
import json

import pytest

from builders.build_eva_lines import build_eva_lines, export_to_jsonl
from validators.validate_phase1_outputs import validate_outputs
from validators.verify_invariants import verify_all_invariants


SOURCE = """#=IVTFF Eva- 2.0 M 5
<f1r>      <! $I=H $Q=A $P=A $L=A $H=1>
<f1r.1,@P0>       fachys.ykal
<f1r.2,+P0>       sory.ckhar
<f1v>      <! $I=H $Q=A $P=B $L=A $H=1>
"""


@pytest.mark.parametrize(
    "defect",
    [
        "missing_empty_page",
        "invented_empty_page",
        "missing_accounting",
        "source_loci",
        "source_page_headers",
        "loci_emitted",
        "loci_reported",
    ],
)
def test_invariants_enforce_complete_loss_accounting(tmp_path, defect):
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
    assert payload["page_ids_without_lines"] == ["f1v"]

    if defect == "missing_empty_page":
        payload["page_ids_without_lines"] = []
        payload["pages_without_lines"] = len(
            payload["page_ids_without_lines"]
        )
        parsed_pages = len({record.page_id for record in records})
        payload["total_pages"] = parsed_pages
        payload["total_pages_in_source"] = parsed_pages
    elif defect == "invented_empty_page":
        payload["page_ids_without_lines"] = ["f9r"]
    elif defect == "missing_accounting":
        del payload["unaccounted_loci"]
    else:
        payload[defect] += 1

    report_path.write_text(json.dumps(payload), encoding="utf-8")

    valid, errors = validate_outputs(out)
    assert not valid, f"Phase control accepted {defect}: {errors}"

    result = verify_all_invariants(out)
    assert not result.passed, (
        f"Invariant validator accepted {defect}: {result.failures}"
    )
