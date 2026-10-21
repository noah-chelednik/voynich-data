# tests/regressions/09e1ca3c/test_finding_1.py
import contextlib
import io
import json

from builders.build_eva_lines import build_eva_lines, export_to_jsonl
from validators.validate_phase1_outputs import validate_outputs
from validators.verify_invariants import verify_all_invariants


def test_interrupted_wrap_is_reported_instead_of_emitted(tmp_path):
    source = tmp_path / "source.txt"
    out = tmp_path / "out"
    out.mkdir()
    prefix = (
        "#=IVTFF Eva- 2.0 M 5\n"
        "<f1r> <! $I=H $Q=A $P=A $L=A $H=1>\n"
        "<f1r.1,@P0> qokedy\n"
    )

    def build(tail):
        source.write_text(prefix + tail, encoding="utf-8", newline="")
        records, report = build_eva_lines(source, out)
        export_to_jsonl(records, out / "eva_lines.jsonl")
        (out / "eva_lines_build_report.json").write_text(
            json.dumps(report.to_dict()), encoding="utf-8"
        )
        return records, report

    def require_valid():
        with contextlib.redirect_stdout(io.StringIO()):
            valid, errors = validate_outputs(out)
            invariants = verify_all_invariants(out)
        assert valid, errors
        assert invariants.passed, invariants.failures

    records, report = build("<f1r.2,+P0> daiin /\n/ shedy\n")
    assert not report.warnings
    assert next(r for r in records if r.line_id == "f1r:2").text_raw == (
        "daiin /\n/ shedy"
    )
    require_valid()

    records, report = build("<f1r.2,+P0> daiin /\n# note\n/ shedy\n")
    assert "f1r:2" in report.reported_loci
    assert all(r.line_id != "f1r:2" for r in records)
    assert not report.unaccounted_loci
    require_valid()
