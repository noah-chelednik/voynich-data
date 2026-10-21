# tests/regressions/1c53841b/test_reach_5.py
import pytest

from tests import test_data_model_doc as checks


@pytest.mark.parametrize(
    "title",
    [
        "Fields of `eva_lines.jsonl`",
        "The build report (`output/eva_lines_build_report.json`)",
    ],
)
def test_document_predicate_requires_each_claimed_table(monkeypatch, title):
    checks.test_profile_table_is_the_code()
    body = checks.section(title)
    assert "|" in body
    changed = checks.DOC.replace(
        body,
        "\nThe claimed table has been removed.\n\n",
        1,
    )
    assert changed != checks.DOC
    monkeypatch.setattr(checks, "DOC", changed)

    with pytest.raises(AssertionError):
        checks.test_profile_table_is_the_code()
