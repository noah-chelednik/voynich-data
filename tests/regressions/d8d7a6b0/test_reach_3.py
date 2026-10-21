# tests/regressions/d8d7a6b0/test_reach_3.py
import pytest

from tests import test_data_model_doc as checks


def test_data_model_predicate_reaches_metadata_outputs(monkeypatch):
    checks.test_profile_table_is_the_code()
    checks.test_metadata_field_lists_are_the_outputs("pages")

    original = "| `pages.jsonl` | `page_id`,"
    replacement = "| `pages.jsonl` | `phantom_field`,"
    assert original in checks.DOC
    monkeypatch.setattr(
        checks,
        "DOC",
        checks.DOC.replace(original, replacement, 1),
    )

    # The existing output comparison recognizes the false documentation.
    with pytest.raises(AssertionError):
        checks.test_metadata_field_lists_are_the_outputs("pages")

    # The predicate named by claim 16 must reach that comparison.
    with pytest.raises(AssertionError):
        checks.test_profile_table_is_the_code()
