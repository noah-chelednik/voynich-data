# tests/regressions/28813a2e/test_finding_2.py
import contextlib
import io
import json

import pytest

from builders.build_eva_lines import build_eva_lines, export_to_jsonl
from validators import validate_phase1_outputs as phase
from validators import verify_invariants as inv


@pytest.mark.parametrize("checker", ["phase", "invariants"])
def test_empty_page_without_illustration_keeps_builder_summary(tmp_path, checker):
    text = (
        "#=IVTFF Eva- 2.0\n"
        "<f1r> <! $I=H $L=A>\n"
        "<f1r.1,@P0> daiin\n"
    )

    def build_and_check(name, source_text):
        base = tmp_path / name
        base.mkdir()
        source = base / "source.txt"
        source.write_text(source_text, encoding="utf-8")
        out = base / "out"
        out.mkdir()
        records, report = build_eva_lines(source, out)
        export_to_jsonl(records, out / "eva_lines.jsonl")
        (out / "eva_lines_build_report.json").write_text(
            json.dumps(report.to_dict()), encoding="utf-8"
        )
        with contextlib.redirect_stdout(io.StringIO()):
            if checker == "phase":
                result = phase.validate_outputs(out)
            else:
                checked = inv.verify_all_invariants(out)
                result = checked.passed, checked.failures
        return report, result

    _, (accepted, errors) = build_and_check("control", text)
    assert accepted, errors

    report, (accepted, errors) = build_and_check(
        "empty_page", text + "<f2r>\n"
    )
    assert "f2r" in report.page_ids_without_lines
    assert accepted, errors
