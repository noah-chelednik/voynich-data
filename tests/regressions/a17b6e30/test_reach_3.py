# tests/regressions/a17b6e30/test_reach_3.py
import contextlib
import io
import json

import pytest

from builders.build_eva_lines import build_eva_lines, export_to_jsonl
from validators import validate_phase1_outputs as phase
from validators import verify_invariants as inv


@pytest.mark.parametrize(
    "text_raw, expected",
    [
        ("da{Ic}y", "daIcy"),
        ("da[I:o]y", "daIy"),
        ("da[{Ic}:o]y", "daIcy"),
    ],
)
def test_source_uppercase_glyph_is_accepted_inside_markup(tmp_path, text_raw, expected):
    source = tmp_path / "source.txt"
    source.write_text(
        "#=IVTFF Eva- 2.0 M 5\n"
        "<f1r> <! $Q=A $L=A $H=1 $I=H>\n"
        f"<f1r.1,@P0> {text_raw}\n",
        encoding="utf-8",
    )
    out = tmp_path / "out"
    out.mkdir()
    records, report = build_eva_lines(source, out)
    assert records[0].text_clean == expected
    export_to_jsonl(records, out / "eva_lines.jsonl")
    (out / "eva_lines_build_report.json").write_text(
        json.dumps(report.to_dict()), encoding="utf-8"
    )

    with contextlib.redirect_stdout(io.StringIO()):
        phase_ok, errors = phase.validate_outputs(out)
        invariants = inv.verify_all_invariants(out)

    assert phase_ok, errors
    assert invariants.passed, invariants.failures
