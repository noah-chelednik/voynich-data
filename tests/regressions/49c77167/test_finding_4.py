# tests/regressions/49c77167/test_finding_4.py
import json

from builders.build_eva_lines import build_eva_lines
from validators.validate_phase1_outputs import check_loss_accounting


def test_reported_page_survives_report_serialization(tmp_path):
    source = tmp_path / "reported-page.txt"
    source.write_text(
        "#=IVTFF Eva- 2.0 M\n"
        "<f1r>\n"
        "<f1r.1,@P0> daiin\n"
        "<fXr>\n",
        encoding="utf-8",
    )
    records, report = build_eva_lines(source, tmp_path)
    assert report.loss_problems() == []
    assert any("fXr" in warning for warning in report.warnings)

    serialized = json.loads(json.dumps(report.to_dict()))
    errors = check_loss_accounting(
        [record.to_dict() for record in records], serialized
    )
    assert errors == [], errors
