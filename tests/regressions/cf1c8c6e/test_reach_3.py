# tests/regressions/cf1c8c6e/test_reach_3.py
import pytest

from tests import test_data_model_doc as checks


@pytest.mark.parametrize("locus", ["f1v:1", "f85r2:2", "fRos:39"])
def test_reference_rows_with_all_page_forms_are_checked(monkeypatch, locus):
    checks.test_reference_lines_through_the_text_clean_profile()
    body = checks.section("Normalization profiles")
    header = "| locus | `text_raw` | `text_clean` |\n|---|---|---|\n"
    assert header in body
    false_row = f"| `{locus}` | `not-the-source` | `not-the-profile` |\n"
    changed = body.replace(header, header + false_row, 1)
    monkeypatch.setattr(checks, "DOC", checks.DOC.replace(body, changed, 1))

    with pytest.raises(AssertionError):
        checks.test_reference_lines_through_the_text_clean_profile()
