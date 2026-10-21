# tests/regressions/4fe7e6d6/test_reach_2.py
"""Clause 3: instructions hidden in an HTML comment satisfy neither issue-form check. test_transcription_errors_go_upstream
also requires the field that asks where the error was reported upstream to say "upstream", but it reads that field's
label and description as raw source: GitHub renders an issue-form field's `description` as Markdown, so a description
"<!-- upstream -->" shows nothing, and a label that never says upstream still satisfies the check."""
from pathlib import Path

import pytest
import yaml

from tests import test_stability as checks


def test_upstream_hidden_in_the_field_description_comment_is_refused(monkeypatch):
    target = checks.TEMPLATES / "transcription_error.yml"
    original_read = Path.read_text
    checks.test_transcription_errors_go_upstream()  # passes as committed
    form = yaml.safe_load(original_read(target, encoding="utf-8"))
    field = next(i for i in form["body"] if i.get("id") == "upstream")
    field["attributes"]["label"] = "Where you reported it"
    field["attributes"]["description"] = "<!-- upstream -->"
    # what the reader sees of the field says nothing of upstream
    shown = field["attributes"]["label"] + " " + "".join(checks.as_shown(field["attributes"]["description"]).text)
    assert "upstream" not in shown.lower()
    replacement = yaml.safe_dump(form, sort_keys=False)

    def read_text(path, *args, **kwargs):
        if Path(path).resolve() == target.resolve():
            return replacement
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_text)
    with pytest.raises(AssertionError):
        checks.test_transcription_errors_go_upstream()
