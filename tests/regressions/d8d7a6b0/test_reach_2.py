# tests/regressions/d8d7a6b0/test_reach_2.py
import pytest

from tests import test_data_model_doc as checks


def test_data_model_predicate_rejects_a_false_field_type(monkeypatch):
    checks.test_profile_table_is_the_code()
    assert checks.SCHEMA["properties"]["page_id"]["type"] == "string"

    original = "| `page_id` | string |"
    replacement = "| `page_id` | integer |"
    assert original in checks.DOC
    monkeypatch.setattr(
        checks,
        "DOC",
        checks.DOC.replace(original, replacement, 1),
    )

    with pytest.raises(AssertionError):
        checks.test_profile_table_is_the_code()
