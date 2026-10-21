# tests/regressions/cad4bcad/test_finding_2.py
import pytest

from tests import test_data_model_doc as checks


def test_field_table_rejects_a_row_without_outer_pipes(monkeypatch):
    checks.test_field_table_is_the_schema()
    body = checks.section("Fields of `eva_lines.jsonl`")
    lines = body.splitlines(keepends=True)
    last = max(i for i, line in enumerate(lines) if line.startswith("|"))
    changed = "".join(
        lines[: last + 1]
        + ["phantom_field | string | Not a schema field.\n"]
        + lines[last + 1 :]
    )
    assert changed != body
    monkeypatch.setattr(checks, "DOC", checks.DOC.replace(body, changed, 1))

    with pytest.raises(AssertionError):
        checks.test_field_table_is_the_schema()
