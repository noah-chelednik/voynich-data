# tests/regressions/99d8710e/test_finding_2.py
import pytest

from tests import test_data_model_doc as checks


@pytest.mark.parametrize("name", ["pages", "folios", "quires"])
def test_metadata_table_rejects_an_incorrect_duplicate(monkeypatch, name):
    checks.test_metadata_field_lists_are_the_outputs(name)
    body = checks.section("Metadata datasets (`output/metadata/`)")
    prefix = f"| `{name}.jsonl` |"
    assert body.count(prefix) == 1
    changed = body.replace(
        prefix,
        f"| `{name}.jsonl` | `phantom_field` |\n" + prefix,
        1,
    )
    assert changed != body
    monkeypatch.setattr(checks, "DOC", checks.DOC.replace(body, changed, 1))

    with pytest.raises(AssertionError):
        checks.test_metadata_field_lists_are_the_outputs(name)
