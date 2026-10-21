# tests/regressions/f6e6801f/test_finding_1.py
import contextlib
import io
import json

from builders.build_eva_lines import build_eva_lines, export_to_jsonl
from parsers import IVTFFParser
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
    encoded_report = report.to_dict()
    (out / "eva_lines_build_report.json").write_text(
        json.dumps(encoded_report), encoding="utf-8"
    )
    return source, out, encoded_report


def _results(out):
    with contextlib.redirect_stdout(io.StringIO()):
        accepted, errors = phase.validate_outputs(out)
        checked = inv.verify_all_invariants(out)
    return {
        "phase": accepted,
        "invariants": checked.passed,
    }, (errors, checked.failures)


def test_empty_page_summaries_are_checked_against_source_headers(
    tmp_path, monkeypatch
):
    text = (
        "#=IVTFF Eva- 2.0\n"
        "<f1r> <! $I=H $L=A>\n"
        "<f1r.1,@P0> daiin\n"
        "<f2r> <! $I=A $L=B>\n"
    )
    _, control_out, correct_report = _build(tmp_path / "control", text)
    accepted, errors = _results(control_out)
    assert all(accepted.values()), errors

    original_parse = IVTFFParser.parse_file

    def wrong_empty_page_metadata(self, path):
        for page in original_parse(self, path):
            if page.page_id == "f2r" and not page.loci:
                page.variables.language = "A"
                page.variables.illustration = "H"
            yield page

    monkeypatch.setattr(
        IVTFFParser, "parse_file", wrong_empty_page_metadata
    )
    source, out, wrong_report = _build(tmp_path / "case", text)
    assert source.read_text(encoding="utf-8") == text
    assert "f2r" in wrong_report["page_ids_without_lines"]
    for field in ("pages_by_language", "pages_by_section"):
        assert wrong_report[field] != correct_report[field]

    accepted, errors = _results(out)
    assert not any(accepted.values()), (accepted, errors)
