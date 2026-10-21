# tests/regressions/dd4ff650/test_reach_3.py
from copy import deepcopy

import pytest

from tests import test_stability as checks


@pytest.mark.parametrize(
    "name", ("data_bug.yml", "transcription_error.yml")
)
def test_required_field_check_cannot_hide_duplicate_ids(monkeypatch, name):
    checks.test_issue_templates_are_forms_with_required_fields(name)
    forms = deepcopy(checks.templates())
    body = forms[name]["body"]
    original = next(item for item in body if item.get("id") == "line_id")
    unchecked = deepcopy(original)
    unchecked["validations"]["required"] = False
    body.insert(body.index(original), unchecked)
    monkeypatch.setattr(checks, "templates", lambda: forms)

    with pytest.raises(AssertionError):
        checks.test_issue_templates_are_forms_with_required_fields(name)
