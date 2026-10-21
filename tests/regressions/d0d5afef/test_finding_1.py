# tests/regressions/d0d5afef/test_finding_1.py
import contextlib
import io
import json

from builders.build_eva_lines import build_eva_lines, export_to_jsonl
from validators import validate_phase1_outputs as phase
from validators import verify_invariants as inv


def _build(base, text):
    base.mkdir()
    source = base / "source.txt"
    source.write_text(text, encoding="utf-8", newline="")
    out = base / "out"
    out.mkdir()
    records, report = build_eva_lines(source, out)
    export_to_jsonl(records, out / "eva_lines.jsonl")
    (out / "eva_lines_build_report.json").write_text(
        json.dumps(report.to_dict()), encoding="utf-8"
    )
    return out


def _results(out):
    with contextlib.redirect_stdout(io.StringIO()):
        accepted, errors = phase.validate_outputs(out)
        checked = inv.verify_all_invariants(out)
    return {
        "phase": accepted,
        "invariants": checked.passed,
    }, (errors, checked.failures)


def test_page_summaries_use_physical_source_line_boundaries(tmp_path):
    text = (
        "#=IVTFF Eva- 2.0\n"
        "<f1r> <! $I=H $L=A>\n"
        "<f1r.1,@P0> daiin\n"
        "# note continued\n"
        "<f2r> <! $I=A $L=B>\n"
    )
    control, errors = _results(_build(tmp_path / "control", text))
    assert all(control.values()), errors

    changed = text.replace(
        "# note continued\n", "# note\fcontinued\n"
    )
    out = _build(tmp_path / "case", changed)
    correct, correct_errors = _results(out)

    report_path = out / "eva_lines_build_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert "f2r" in report["page_ids_without_lines"]

    languages = report["pages_by_language"]
    languages["unknown"] = languages.pop("B")
    sections = report["pages_by_section"]
    sections["herbal"] += sections.pop("astronomical")
    report_path.write_text(json.dumps(report), encoding="utf-8")

    incorrect, incorrect_errors = _results(out)
    assert {"correct": correct, "incorrect": incorrect} == {
        "correct": {"phase": True, "invariants": True},
        "incorrect": {"phase": False, "invariants": False},
    }, (correct_errors, incorrect_errors)
