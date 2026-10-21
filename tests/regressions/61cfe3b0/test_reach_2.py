# tests/regressions/61cfe3b0/test_reach_2.py
import contextlib
import io
import json

import pytest

from builders.build_eva_lines import build_eva_lines, export_to_jsonl
from validators.validate_phase1_outputs import validate_outputs
from validators.verify_invariants import verify_all_invariants


@pytest.mark.parametrize("validator", ["phase", "invariants"])
def test_invalid_page_language_is_kept_and_accepted_by_both_validators(
    tmp_path, validator
):
    source = tmp_path / "source.txt"
    source.write_bytes(
        b"#=IVTFF Eva- 2.0 M 5\n"
        b"<f1r> <! $L=AB $B=1>\n"
        b"<f1r.1,@P0> daiin\n"
    )
    out = tmp_path / "out"
    out.mkdir()

    records, report = build_eva_lines(source, out)
    assert [record.line_id for record in records] == ["f1r:1"]
    assert any("page variable" in warning for warning in report.warnings)
    assert report.reported_loci == []
    assert report.reported_pages == []
    assert report.loss_problems() == []

    export_to_jsonl(records, out / "eva_lines.jsonl")
    (out / "eva_lines_build_report.json").write_text(
        json.dumps(report.to_dict()), encoding="utf-8"
    )

    with contextlib.redirect_stdout(io.StringIO()):
        if validator == "phase":
            accepted, errors = validate_outputs(out)
            assert accepted, errors
        else:
            result = verify_all_invariants(out)
            assert result.passed, result.failures
