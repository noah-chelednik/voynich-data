# tests/regressions/cf1c8c6e/test_reach_4.py
import pytest

from tests import test_data_model_doc as checks


@pytest.mark.parametrize(
    "field",
    ["page_id", "line_number", "line_id", "position", "source_line"],
)
def test_mapping_requires_each_source_structure_field(monkeypatch, field):
    checks.test_mapping_table_reaches_every_markup_field()
    body = checks.section("From IVTFF to the dataset")
    token = f"`{field}`"
    assert token in body
    changed = body.replace(token, "(mapping omitted)")
    monkeypatch.setattr(checks, "DOC", checks.DOC.replace(body, changed, 1))

    with pytest.raises(AssertionError):
        checks.test_mapping_table_reaches_every_markup_field()
