# tests/regressions/cf1c8c6e/test_reach_1.py
import pytest

from tests import test_data_model_doc as checks


def test_field_table_rejects_an_extra_undecorated_field(monkeypatch):
    checks.test_field_table_is_the_schema()
    body = checks.section("Fields of `eva_lines.jsonl`")
    separator = "|---|---|---|\n"
    assert separator in body
    changed = body.replace(
        separator,
        separator + "| phantom_field | string | Absent from the row schema. |\n",
        1,
    )
    monkeypatch.setattr(checks, "DOC", checks.DOC.replace(body, changed, 1))

    with pytest.raises(AssertionError):
        checks.test_field_table_is_the_schema()
