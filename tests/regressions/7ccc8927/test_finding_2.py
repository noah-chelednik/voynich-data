# tests/regressions/7ccc8927/test_finding_2.py
import pytest

from tests import test_data_model_doc as checks


def test_field_table_rejects_a_row_with_only_its_first_cell(monkeypatch):
    checks.test_field_table_is_the_schema()
    body = checks.section("Fields of `eva_lines.jsonl`")
    lines = body.splitlines(keepends=True)
    last = max(i for i, line in enumerate(lines) if line.startswith("|"))
    changed = "".join(
        lines[: last + 1]
        + ["phantom_field\n"]
        + lines[last + 1 :]
    )
    assert changed != body
    monkeypatch.setattr(checks, "DOC", checks.DOC.replace(body, changed, 1))

    with pytest.raises(AssertionError):
        checks.test_field_table_is_the_schema()
