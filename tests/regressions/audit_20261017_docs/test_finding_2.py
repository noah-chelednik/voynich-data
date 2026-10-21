import pytest
from tests import test_data_model_doc as checks


def test_document_check_rejects_an_incorrect_duplicate(monkeypatch):
    checks.test_metadata_field_lists_are_the_outputs("pages")
    prefix = "| `pages.jsonl` |"
    changed = checks.DOC.replace(
        prefix,
        "| `pages.jsonl` | `phantom_field` |\n" + prefix,
        1,
    )
    assert changed != checks.DOC
    monkeypatch.setattr(checks, "DOC", changed)
    with pytest.raises(AssertionError):
        checks.test_metadata_field_lists_are_the_outputs("pages")
