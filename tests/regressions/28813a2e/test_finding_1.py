# tests/regressions/28813a2e/test_finding_1.py
import contextlib
import io
import json

from builders.build_eva_lines import build_eva_lines, export_to_jsonl
from validators import validate_phase1_outputs as phase
from validators import verify_invariants as inv


def _build(base, text):
    base.mkdir()
    source = base / "source.txt"
    source.write_text(text, encoding="utf-8")
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
        invariant = inv.verify_all_invariants(out)
    return {
        "phase": accepted,
        "invariants": invariant.passed,
    }, (errors, invariant.failures)


def test_rejected_header_does_not_erase_an_accepted_page(tmp_path):
    text = (
        "#=IVTFF Eva- 2.0\n"
        "<f1r> <! $I=H $L=A>\n"
        "<f1r.1,@P0> daiin\n"
    )
    control, errors = _results(_build(tmp_path / "control", text))
    assert all(control.values()), errors

    out = _build(tmp_path / "case", text + "<f1r\n")
    path = out / "eva_lines_build_report.json"
    report = json.loads(path.read_text())
    assert report["reported_pages"] == ["f1r"]
    assert report["pages_by_language"] and report["pages_by_section"]

    correct, correct_errors = _results(out)
    report["pages_by_language"] = {}
    report["pages_by_section"] = {}
    path.write_text(json.dumps(report), encoding="utf-8")
    erased, erased_errors = _results(out)

    assert {"correct": correct, "erased": erased} == {
        "correct": {"phase": True, "invariants": True},
        "erased": {"phase": False, "invariants": False},
    }, (correct_errors, erased_errors)
