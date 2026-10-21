# tests/regressions/f6e6801f/test_finding_2.py
import contextlib
import io
import json

import pytest

from builders.build_eva_lines import build_eva_lines, export_to_jsonl
from validators import validate_phase1_outputs as phase
from validators import verify_invariants as inv


@pytest.mark.parametrize(
    "field", ["pages_by_language", "pages_by_section"]
)
@pytest.mark.parametrize(
    "conversion", [bool, float], ids=["boolean", "float"]
)
def test_page_summary_values_must_be_integer_counts(
    tmp_path, field, conversion
):
    source = tmp_path / "source.txt"
    source.write_text(
        "#=IVTFF Eva- 2.0\n"
        "<f1r> <! $I=H $L=A>\n"
        "<f1r.1,@P0> daiin\n",
        encoding="utf-8",
    )
    out = tmp_path / "out"
    out.mkdir()
    records, report = build_eva_lines(source, out)
    export_to_jsonl(records, out / "eva_lines.jsonl")
    report_path = out / "eva_lines_build_report.json"
    report_data = report.to_dict()
    report_path.write_text(json.dumps(report_data), encoding="utf-8")

    def results():
        with contextlib.redirect_stdout(io.StringIO()):
            accepted, errors = phase.validate_outputs(out)
            checked = inv.verify_all_invariants(out)
        return {
            "phase": accepted,
            "invariants": checked.passed,
        }, (errors, checked.failures)

    accepted, errors = results()
    assert all(accepted.values()), errors
    original = report_data[field]
    assert original
    assert all(type(value) is int for value in original.values())

    report_data[field] = {
        key: conversion(value) for key, value in original.items()
    }
    assert report_data[field] == original
    assert all(
        type(value) is not int for value in report_data[field].values()
    )
    report_path.write_text(json.dumps(report_data), encoding="utf-8")

    accepted, errors = results()
    assert not any(accepted.values()), (accepted, errors)
