# tests/regressions/6e91b4a2/test_reach_4.py
import pytest

from tests import test_data_model_doc as checks


def test_metadata_field_check_reaches_later_tables(monkeypatch):
    checks.test_metadata_field_lists_are_the_outputs("bifolia")
    body = checks.section("Metadata datasets (`output/metadata/`)")
    extra = (
        "\n| file | fields |\n"
        "|---|---|\n"
        "| `bifolia.jsonl` | `invented_field` |\n\n"
    )
    monkeypatch.setattr(
        checks,
        "DOC",
        checks.DOC.replace(body, body + extra, 1),
    )

    with pytest.raises(AssertionError):
        checks.test_metadata_field_lists_are_the_outputs("bifolia")
