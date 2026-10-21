# tests/regressions/audit_20261018_tests_r3/test_finding_2.py
from pathlib import Path

import pytest
import yaml

from tests import test_stability as checks


@pytest.mark.parametrize(
    ("filename", "predicate"),
    [
        ("transcription_error.yml", "test_transcription_errors_go_upstream"),
        ("data_bug.yml", "test_the_documents_are_linked"),
    ],
)
def test_hidden_form_instructions_do_not_satisfy_checks(
    monkeypatch, filename, predicate
):
    target = checks.TEMPLATES / filename
    original_read = Path.read_text
    form = yaml.safe_load(original_read(target, encoding="utf-8"))
    for item in form["body"]:
        if item.get("type") == "markdown":
            value = item["attributes"]["value"]
            item["attributes"]["value"] = "<!--\n" + value + "\n-->"
    replacement = yaml.safe_dump(form)

    def read_text(path, *args, **kwargs):
        if path.resolve() == target.resolve():
            return replacement
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_text)
    with pytest.raises(AssertionError):
        getattr(checks, predicate)()
