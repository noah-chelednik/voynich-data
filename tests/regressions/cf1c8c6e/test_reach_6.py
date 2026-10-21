# tests/regressions/cf1c8c6e/test_reach_6.py
import json

import pytest

from tests import test_data_model_doc as checks


@pytest.mark.parametrize("field", ["text_clean", "phantom2"])
def test_build_report_table_rejects_extra_fields(monkeypatch, field):
    checks.test_build_report_fields_are_the_report()
    report = json.loads(
        (checks.OUTPUT / "eva_lines_build_report.json").read_text(encoding="utf-8")
    )
    assert field not in report

    body = checks.section("The build report (`output/eva_lines_build_report.json`)")
    separator = "|---|---|\n"
    assert separator in body
    changed = body.replace(
        separator,
        separator + f"| `{field}` | Claimed report field absent from the report. |\n",
        1,
    )
    monkeypatch.setattr(checks, "DOC", checks.DOC.replace(body, changed, 1))

    with pytest.raises(AssertionError):
        checks.test_build_report_fields_are_the_report()
